"""Bounded, cached public metadata; never fetch arbitrary internal addresses."""
from functools import lru_cache
import http.client
import ipaddress
import json
import re
import socket
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flask import abort, current_app, jsonify, request
from limits import parse

from . import bp
from ..models import Exhibit
from ..services import visible_exhibits
from ..models import db


def metadata_limit():
    if not current_app.testing and not current_app.extensions["auth_limiter"].hit(
        parse("12 per minute"), "public-metadata", request.remote_addr or "unknown"
    ):
        abort(429, "Wait a moment before checking another link.")


@lru_cache(maxsize=128)
def github_metadata(repository, bucket):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Enter a GitHub repository URL.")
    def fetch(suffix):
        req = Request(f"https://api.github.com/repos/{repository}{suffix}", headers={
            "Accept": "application/vnd.github+json", "User-Agent": "Afterpause-Museum",
        })
        with urlopen(req, timeout=4) as response:
            payload = response.read(150_001)
            if len(payload) > 150_000:
                raise ValueError("The response was too large.")
            return json.loads(payload)
    repo = fetch("")
    commits = fetch("/commits?per_page=1")
    latest = commits[0].get("commit", {}) if commits else {}
    return dict(stars=repo.get("stargazers_count", 0), archived=bool(repo.get("archived")),
                last_commit=latest.get("committer", {}).get("date"),
                final_words=latest.get("message", "No commits found.")[:1000],
                label="Latest commit (the repository may still be active)")


def check_demo_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTP or HTTPS demo links can be checked.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in (80, 443):
        raise ValueError("Use a public demo on port 80 or 443.")
    records = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    addresses = {record[4][0] for record in records}
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("Local and private network links cannot be checked.")
    address = sorted(addresses)[0]
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection = connection_type(parsed.hostname, port=port, timeout=4)
    # Pin the validated IP while retaining the original Host and HTTPS SNI.
    # Redirects are reported rather than followed to avoid internal redirects.
    connection._create_connection = lambda target, timeout=4, source_address=None, **kwargs: socket.create_connection(
        (address, port), timeout, source_address)
    try:
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        connection.request("HEAD", path, headers={"User-Agent": "Afterpause-Link-Check"})
        response = connection.getresponse()
        status = response.status
        return dict(status=status, result=("Reachable" if 200 <= status < 300 else
                    "Responded with a redirect" if 300 <= status < 400 else "Responded with an error"),
                    detail="A single HTTP check; this does not determine whether a project is maintained.")
    finally:
        connection.close()


@lru_cache(maxsize=128)
def cached_link_check(url, bucket):
    return check_demo_url(url)


@bp.get("/exhibits/<slug>/metadata/<kind>")
def external_metadata(slug, kind):
    item = db.session.scalar(visible_exhibits().where(Exhibit.slug == slug))
    if not item:
        abort(404)
    metadata_limit()
    try:
        if kind == "github":
            url = urlsplit(item.repository_url)
            if url.scheme != "https" or url.hostname != "github.com" or url.username or url.port:
                raise ValueError("Add a valid HTTPS GitHub repository link to this exhibit first.")
            repository = url.path.strip("/").removesuffix(".git")
            result = github_metadata(repository, int(time.time() // 900))
        elif kind == "demo":
            result = cached_link_check(item.demo_url, int(time.time() // 900))
        else:
            abort(404)
        return jsonify(result)
    except (OSError, ValueError, http.client.HTTPException):
        return jsonify(error="This link could not be checked. It may be unavailable, rate-limited, or restricted. You can still open the original link."), 502
