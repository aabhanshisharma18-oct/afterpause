from uuid import uuid4

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..models import (Bookmark, CATEGORIES, Continuation, Exhibit, Media, PAUSE_REASONS, PERMISSIONS,
                      Proposal, ROOMS, Tag, Update, db, utcnow)
from ..services import (FormError, add_event, attach_image, can_preview, commit, exhibit_for_write, external_link,
                        once, option, read_image, signed_in, upload_path, value, visible_exhibits)

bp = Blueprint("exhibits", __name__)


def owned(exhibit_id):
    exhibit = db.get_or_404(Exhibit, exhibit_id)
    if exhibit.owner_id != g.user.id:
        abort(403)
    return exhibit


@bp.post("/exhibits")
@signed_in
def create():
    once()
    exhibit = Exhibit(slug=f"exhibit-{uuid4().hex[:12]}", owner_id=g.user.id)
    db.session.add(exhibit)
    db.session.commit()
    return redirect(url_for(".edit", exhibit_id=exhibit.id), code=303)


def read_step(exhibit, step, *, partial=False):
    if step == 1:
        return dict(
            title=value("title", "Title", 100, required=not partial),
            intention=value("intention", "One-sentence intention", 180, required=not partial),
            story=value("story", "Project story", 2400, required=not partial),
            room_id=option("room_id", "Room", ROOMS, required=not partial) or None,
            category=option("category", "Category", CATEGORIES, required=not partial),
        ), []
    if step == 2:
        details = dict(
            current_work=value("current_work", "What exists", 1600, required=not partial),
            pause_reason=option("pause_reason", "Pause reason", PAUSE_REASONS, required=False),
            pause_note=value("pause_note", "Pause note", 600, required=False),
            repository_url=external_link("repository_url", "Repository link"),
            demo_url=external_link("demo_url", "Demo link"),
        )
        images = [read_image(), read_image("second_image", "second_alt_text")]
        if len(exhibit.media) + sum(bool(image) for image in images) > 4:
            raise FormError("image", "An exhibit can contain up to four images.")
        return details, images
    details = dict(
        next_step=value("next_step", "Next step", 240, required=not partial),
        skills=value("skills", "Skills", 160, required=False),
        task_size=value("task_size", "Task size", 40, required=False),
        attribution=value("attribution", "Creator credit", 240, required=not partial),
        permissions=option("permissions", "Material permissions", PERMISSIONS, required=not partial),
        share_confirmed=request.form.get("share_confirmed") == "yes",
    )
    if not details["share_confirmed"] and not partial:
        raise FormError("share_confirmed", "Confirm that you can share the work and images.")
    raw = value("tags", "Tags", 160, required=False).casefold()
    names = sorted({name.strip() for name in raw.split(",") if name.strip()})
    if len(names) > 6 or any(len(name) > 30 for name in names):
        raise FormError("tags", "Use at most six tags of 30 characters each.")
    # Tag lookup and creation are inside the exhibit's edit transaction.
    tags = []
    for name in names:
        tag = db.session.scalar(select(Tag).where(Tag.name == name))
        tags.append(tag or Tag(name=name))
    details["tags"] = tags
    return details, []


@bp.route("/exhibits/<int:exhibit_id>/edit", methods=("GET", "POST"))
@signed_in
def edit(exhibit_id):
    step = request.args.get("step", 1, type=int)
    if step not in (1, 2, 3):
        abort(404)
    exhibit = owned(exhibit_id) if request.method == "GET" else exhibit_for_write(exhibit_id, owner=True)
    if request.method == "POST":
        try:
            partial = exhibit.publication_state == "draft" and request.form.get("destination") == "dashboard"
            fields, images = read_step(exhibit, step, partial=partial)
        except FormError as error:
            return render_template("wizard.html", exhibit=exhibit, step=step, error=error), 400
        once()
        for key, data in fields.items():
            setattr(exhibit, key, data)
        if step == 1 and exhibit.published_at is None:
            # The URL is immutable after the first publication.
            import re
            slug = re.sub(r"[^a-z0-9]+", "-", exhibit.title.lower()).strip("-")[:80] or "exhibit"
            exhibit.slug = f"{slug}-{exhibit.id}"
        commit(*(attach_image(image, exhibit=exhibit) for image in images))
        flash("Exhibit changes saved." if exhibit.is_public else "Private draft saved.", "success")
        if request.form.get("destination") == "dashboard":
            return redirect(url_for(".dashboard"), code=303)
        if step == 3:
            return redirect(url_for(".preview", exhibit_id=exhibit.id), code=303)
        return redirect(url_for(".edit", exhibit_id=exhibit.id, step=step + 1), code=303)
    return render_template("wizard.html", exhibit=exhibit, step=step)


@bp.get("/exhibits/<int:exhibit_id>/preview")
@signed_in
def preview(exhibit_id):
    from ..museum import detail
    return detail(owned(exhibit_id), preview=True)


@bp.post("/exhibits/<int:exhibit_id>/publish")
@signed_in
def publish(exhibit_id):
    exhibit = exhibit_for_write(exhibit_id, owner=True)
    if exhibit.moderation_hidden:
        abort(409, "An administrator must clear the visibility restriction before this exhibit can be published.")
    if exhibit.publication_state == "published":
        abort(409, "This exhibit is already published.")
    if not exhibit.submission_progress["ready"]:
        flash("Complete all three steps and add a cover image before publishing.", "error")
        return redirect(url_for(".preview", exhibit_id=exhibit.id), code=303)
    once()
    exhibit.publication_state = "published"
    if not exhibit.published_at:
        exhibit.published_at = utcnow()
        add_event(exhibit, g.user, "original", "The original idea",
                  body=exhibit.intention, next_step=exhibit.next_step, media=exhibit.media[0])
    db.session.commit()
    flash("Your exhibit is open to visitors.", "success")
    return redirect(url_for("museum.exhibit", slug=exhibit.slug), code=303)


@bp.post("/exhibits/<int:exhibit_id>/archive")
@signed_in
def archive(exhibit_id):
    exhibit = exhibit_for_write(exhibit_id, owner=True)
    if exhibit.publication_state == "hidden":
        abort(409, "This exhibit is already archived.")
    once()
    exhibit.publication_state = "hidden"
    db.session.commit()
    flash("Exhibit archived. Its approved history is retained.", "success")
    return redirect(url_for(".dashboard"), code=303)


@bp.get("/media/<storage_key>")
def media(storage_key):
    item = db.session.scalar(select(Media).where(Media.storage_key == storage_key))
    if not item:
        abort(404)
    exhibit = item.exhibit if item.exhibit_id else item.update.continuation.exhibit
    if item.update_id and item.update.review_status != "approved":
        if not can_preview(exhibit) and not (g.user and item.update.author_id == g.user.id):
            abort(404)
    elif not exhibit.is_public and not can_preview(exhibit):
        abort(404)
    path = upload_path(storage_key)
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="image/webp", download_name="exhibit-image.webp")


@bp.get("/dashboard")
@signed_in
def dashboard():
    owner = g.user.id
    tab = request.args.get("tab", "exhibits")
    entries = []
    if tab == "exhibits":
        entries = db.session.scalars(select(Exhibit).where(Exhibit.owner_id == owner)
                                     .options(selectinload(Exhibit.media)).order_by(Exhibit.id.desc()))
    elif tab in {"requests", "my-requests"}:
        where = Exhibit.owner_id == owner if tab == "requests" else Proposal.applicant_id == owner
        entries = db.session.scalars(select(Proposal).join(Exhibit).where(where).order_by(Proposal.id.desc()))
    elif tab == "review":
        entries = db.session.scalars(select(Update).join(Continuation).join(Exhibit).where(
            Exhibit.owner_id == owner, Update.review_status == "pending").order_by(Update.id.desc()))
    elif tab == "continuations":
        entries = db.session.scalars(select(Continuation).where(
            Continuation.contributor_id == owner).order_by(Continuation.id.desc()))
    elif tab == "saved":
        entries = db.session.scalars(visible_exhibits().join(Bookmark).where(
            Bookmark.user_id == owner).order_by(Exhibit.id.desc()))
    else:
        abort(404)
    return render_template("dashboard.html", tab=tab, entries=list(entries))


@bp.post("/exhibits/<int:exhibit_id>/bookmark")
@signed_in
def bookmark(exhibit_id):
    exhibit = exhibit_for_write(exhibit_id, public=True)
    once()
    pair = db.session.get(Bookmark, (g.user.id, exhibit.id))
    if request.form.get("save") == "yes" and not pair:
        db.session.add(Bookmark(user_id=g.user.id, exhibit_id=exhibit.id))
    elif request.form.get("save") == "no" and pair:
        db.session.delete(pair)
    db.session.commit()
    return redirect(url_for("museum.exhibit", slug=exhibit.slug), code=303)
