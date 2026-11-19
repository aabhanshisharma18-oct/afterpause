"""Visitor interactions and collection views, using the same visibility rules."""
from collections import Counter
from statistics import mean

from flask import abort, current_app, flash, g, redirect, render_template, request, url_for
from limits import parse
from sqlalchemy import select

from . import bp
from ..models import Exhibit, Flower, GuestEntry, PAUSE_REASONS, db
from ..services import FormError, exhibit_for_write, once, signed_in, value, visible_exhibits


def collection_stats():
    items = db.session.scalars(visible_exhibits()).all()
    reasons = Counter(PAUSE_REASONS.get(item.pause_reason, "Not recorded") for item in items)
    lifespans = [(item.paused_on - item.born_on).days for item in items if item.born_on and item.paused_on]
    return dict(total=len(items), reviving=sum(item.continuation_state == "in-progress" for item in items),
                milestones=sum(item.continuation_state == "milestone" for item in items),
                average=round(mean(lifespans)) if lifespans else None,
                reasons=reasons.most_common(), dated=sorted(
                    [item for item in items if item.paused_on], key=lambda item: item.paused_on, reverse=True),
                demo_count=sum(item.is_demo for item in items))


@bp.get("/collection")
def collection():
    items = db.session.scalars(visible_exhibits().order_by(Exhibit.curator_pick.desc(), Exhibit.id.asc())).all()
    return render_template("collection.html", items=items, stats=collection_stats())


@bp.get("/statistics")
def statistics():
    return render_template("statistics.html", stats=collection_stats())


@bp.get("/gift-shop")
def gift_shop():
    return render_template("gift_shop.html")


@bp.post("/exhibits/<int:exhibit_id>/flowers")
@signed_in
def flowers(exhibit_id):
    exhibit = exhibit_for_write(exhibit_id, public=True)
    once()
    if not db.session.get(Flower, (g.user.id, exhibit.id)):
        db.session.add(Flower(user_id=g.user.id, exhibit_id=exhibit.id))
    db.session.commit()
    flash("A flower for an idea worth remembering.", "success")
    return redirect(url_for("museum.exhibit", slug=exhibit.slug, _anchor="guest-book"), code=303)


@bp.post("/exhibits/<int:exhibit_id>/guest-book")
@signed_in
def guest_book(exhibit_id):
    exhibit = exhibit_for_write(exhibit_id, public=True)
    limiter = current_app.extensions["auth_limiter"]
    if not limiter.hit(parse("10 per minute"), "guest-book", str(g.user.id)):
        abort(429, "Give other visitors a moment before leaving another note.")
    try:
        body = value("body", "Guest book note", 600)
    except FormError as error:
        abort(400, str(error))
    once()
    db.session.add(GuestEntry(exhibit_id=exhibit.id, author_id=g.user.id, body=body))
    db.session.commit()
    flash("Your note is in the guest book.", "success")
    return redirect(url_for("museum.exhibit", slug=exhibit.slug, _anchor="guest-book"), code=303)


@bp.post("/guest-book/<int:entry_id>/delete")
@signed_in
def delete_guest_entry(entry_id):
    entry = db.get_or_404(GuestEntry, entry_id)
    exhibit = exhibit_for_write(entry.exhibit_id, public=True)
    if g.user.id not in {entry.author_id, exhibit.owner_id} and g.user.role != "admin":
        abort(403)
    once()
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("museum.exhibit", slug=exhibit.slug, _anchor="guest-book"), code=303)
