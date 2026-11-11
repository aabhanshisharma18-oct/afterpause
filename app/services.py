"""Validation, visibility and shared write helpers."""

from functools import wraps
import io
from pathlib import Path
import re
from urllib.parse import urlsplit
from uuid import uuid4
import warnings

from flask import abort, current_app, g, redirect, request, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select, text

from .models import Action, Exhibit, Media, TimelineEvent, db

MAX_IMAGE = 4 * 1024 * 1024


class FormError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field


def value(key, label, limit, *, required=True):
    content = request.form.get(key, "").strip()
    if not content and required:
        raise FormError(key, f"Enter {label.lower()}.")
    if len(content) > limit:
        raise FormError(key, f"{label} can be at most {limit} characters.")
    return content


def option(key, label, choices, *, required=True):
    content = value(key, label, 40, required=required)
    if content and content not in choices:
        raise FormError(key, f"Choose a valid {label.lower()}.")
    return content


def external_link(key, label):
    content = value(key, label, 500, required=False)
    if content:
        try:
            url = urlsplit(content)
            valid = (url.scheme in {"http", "https"} and url.hostname and url.username is None
                     and not re.search(r"[\s\\\x00-\x1f\x7f]", content))
            url.port
        except ValueError:
            valid = False
        if not valid:
            raise FormError(key, f"{label} must be a complete http or https URL.")
    return content


def pagination_number(key="page"):
    return min(10000, max(1, request.args.get(key, 1, type=int)))


def signed_in(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            target = request.full_path.rstrip("?") if request.method == "GET" else url_for("exhibits.dashboard")
            return redirect(url_for("auth.login", next=target), code=303)
        return view(*args, **kwargs)
    return wrapped


def admin_only(view):
    @signed_in
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def exhibit_for_write(exhibit_id, *, owner=False, public=False):
    if db.engine.dialect.name == "sqlite":
        db.session.execute(text("BEGIN IMMEDIATE"))
    exhibit = db.session.scalar(select(Exhibit).where(Exhibit.id == exhibit_id).with_for_update())
    if exhibit is None or (public and not exhibit.is_public):
        abort(404)
    if owner and exhibit.owner_id != g.user.id:
        abort(403)
    return exhibit


def once():
    token = request.form.get("action_token", "")
    if not re.fullmatch(r"[a-f0-9]{32}", token):
        abort(400, "Reload the form and try again.")
    if db.session.get(Action, (g.user.id, token)):
        abort(409, "This form was already submitted. Reload the page to see the current state.")
    db.session.add(Action(user_id=g.user.id, token=token))


def visible_exhibits():
    return select(Exhibit).where(Exhibit.publication_state == "published", Exhibit.moderation_hidden.is_(False))


def can_preview(exhibit):
    return g.user and (g.user.id == exhibit.owner_id or g.user.role == "admin")


def add_event(exhibit, actor, event_type, title, *, body="", next_step="", media=None, update=None):
    db.session.add(TimelineEvent(
        exhibit=exhibit, actor_id=actor.id, actor_name=actor.display_name, event_type=event_type,
        title=title, body=body, next_step=next_step, media=media, update=update,
    ))


def read_image(field="image", alt_field="alt_text", *, required=False):
    upload = request.files.get(field)
    if not upload or not upload.filename:
        if required:
            raise FormError(field, "Choose a screenshot.")
        if request.form.get(alt_field, "").strip():
            raise FormError(field, "Choose the image for this description.")
        return None
    data = upload.stream.read(MAX_IMAGE + 1)
    if len(data) > MAX_IMAGE:
        raise FormError(field, "Use an image of 4 MB or less.")
    alt = value(alt_field, "Image description", 180)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as image:
                if image.width * image.height > 20_000_000 or getattr(image, "is_animated", False):
                    raise ValueError("Image must be static and at most 20 megapixels.")
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1600, 1600))
                clean = Image.new("RGBA" if image.has_transparency_data else "RGB", image.size)
                clean.paste(image.convert(clean.mode))
                output = io.BytesIO()
                clean.save(output, "WEBP", quality=84, method=4)
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning):
        raise FormError(field, "Use a static PNG, JPEG or WebP image up to 20 megapixels.") from None
    return output.getvalue(), alt


def attach_image(data, *, exhibit=None, update=None):
    if data:
        content, alt = data
        media = Media(exhibit=exhibit, update=update, storage_key=f"{uuid4().hex}.webp",
                      alt_text=alt, size=len(content))
        db.session.add(media)
        return media, content
    return None


def upload_path(storage_key):
    if not re.fullmatch(r"[a-f0-9]{32}\.webp", storage_key):
        abort(404)
    return Path(current_app.config["UPLOAD_DIR"]) / storage_key


def commit(*uploads):
    from . import storage
    created = []
    try:
        for upload in filter(None, uploads):
            media, content = upload
            storage.store(media.storage_key, content)
            created.append(media.storage_key)
        db.session.commit()
    except BaseException:
        db.session.rollback()
        for key in created:
            try:
                storage.remove(key)
            except Exception:
                current_app.logger.error("Media rollback cleanup failed for %s", key)
        raise
