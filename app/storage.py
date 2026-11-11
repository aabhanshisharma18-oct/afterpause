"""Private media storage. Every read is authorised by the Flask media route."""
import io
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from flask import abort, current_app


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward server credentials to another destination.


def validate_storage(config):
    if config["MEDIA_STORAGE"] not in {"local", "supabase"}:
        raise RuntimeError("MEDIA_STORAGE must be local or supabase")
    if config["MEDIA_STORAGE"] == "supabase":
        url = urlsplit(config["SUPABASE_URL"])
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment or url.path not in {"", "/"}
                or not config["SUPABASE_SERVICE_KEY"]
                or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", config["SUPABASE_BUCKET"])):
            raise RuntimeError("Set an HTTPS SUPABASE_URL, server-only SUPABASE_SERVICE_KEY and valid bucket")


def checked_key(key):
    if not re.fullmatch(r"[a-f0-9]{32}\.webp", key):
        abort(404)
    return key


def remote(method, path, data=None, content_type=None):
    config = current_app.config
    key = config["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    if content_type:
        headers["Content-Type"] = content_type
    req = Request(config["SUPABASE_URL"].rstrip("/") + "/storage/v1/" + path,
                  data=data, headers=headers, method=method)
    try:
        with build_opener(NoRedirect).open(req, timeout=15) as response:
            return response.read(8 * 1024 * 1024 + 1)
    except HTTPError as error:
        status = error.code
        error.close()
        if method == "GET" and status == 404:
            abort(404)
        current_app.logger.error("Media storage HTTP failure: %s", status)
        abort(503, "Image storage is temporarily unavailable. Try again.")
    except (URLError, OSError):
        current_app.logger.error("Media storage connection failed")
        abort(503, "Image storage is temporarily unavailable. Try again.")


def store(key, content):
    checked_key(key)
    if current_app.config["MEDIA_STORAGE"] == "supabase":
        bucket = quote(current_app.config["SUPABASE_BUCKET"], safe="")
        remote("POST", f"object/{bucket}/{key}", content, "image/webp")
    else:
        path = Path(current_app.config["UPLOAD_DIR"]) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            try:
                handle.write(content)
            except BaseException:
                path.unlink(missing_ok=True)
                raise


def remove(key):
    checked_key(key)
    if current_app.config["MEDIA_STORAGE"] == "supabase":
        bucket = quote(current_app.config["SUPABASE_BUCKET"], safe="")
        remote("DELETE", f"object/{bucket}", json.dumps({"prefixes": [key]}).encode(), "application/json")
    else:
        (Path(current_app.config["UPLOAD_DIR"]) / key).unlink(missing_ok=True)


def read(key):
    checked_key(key)
    if current_app.config["MEDIA_STORAGE"] == "supabase":
        bucket = quote(current_app.config["SUPABASE_BUCKET"], safe="")
        content = remote("GET", f"object/authenticated/{bucket}/{key}")
        if len(content) > 8 * 1024 * 1024:
            abort(503, "Stored image exceeds the serving limit.")
        return io.BytesIO(content)
    path = Path(current_app.config["UPLOAD_DIR"]) / key
    if not path.is_file():
        abort(404)
    return path
