from flask import Blueprint, abort, g, render_template, request, url_for
from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload, selectinload

from ..models import Bookmark, CATEGORIES, Exhibit, ROOMS, STATES, Tag, TimelineEvent, db
from ..services import pagination_number, visible_exhibits

bp = Blueprint("museum", __name__)


@bp.get("/")
def entrance():
    featured = db.session.scalar(visible_exhibits().order_by(Exhibit.is_demo.asc(), Exhibit.id.asc()).limit(1))
    return render_template("entrance.html", featured=featured)


@bp.get("/explore")
def explore():
    filters = {key: request.args.get(key, "").strip()[:limit] for key, limit in
               (("q", 100), ("room", 40), ("category", 16), ("skill", 60), ("state", 16))}
    for key, allowed in (("room", ROOMS), ("category", CATEGORIES), ("state", STATES)):
        if filters[key] and filters[key] not in allowed:
            abort(400, "Choose a valid filter.")
    query = visible_exhibits().options(joinedload(Exhibit.owner), selectinload(Exhibit.media))
    if term := filters["q"]:
        query = query.where(or_(Exhibit.title.icontains(term, autoescape=True),
                                Exhibit.story.icontains(term, autoescape=True),
                                Exhibit.intention.icontains(term, autoescape=True),
                                Exhibit.tags.any(Tag.name.icontains(term, autoescape=True))))
    if skill := filters["skill"]:
        query = query.where(Exhibit.skills.icontains(skill, autoescape=True))
    for key, column in (("room", Exhibit.room_id), ("category", Exhibit.category),
                        ("state", Exhibit.continuation_state)):
        if filters[key]:
            query = query.where(column == filters[key])
    page = db.paginate(query.order_by(Exhibit.published_at.desc(), Exhibit.id.desc()),
                       page=pagination_number(), per_page=9)
    filter_url = lambda **changes: url_for(".explore", **{
        key: data for key, data in (filters | changes).items() if data
    })
    return render_template("explore.html", filters=filters, page=page, filter_url=filter_url,
                           filter_url_page=lambda number: filter_url(page=number))


def detail(exhibit, *, preview=False):
    events = db.paginate(select(TimelineEvent).where(TimelineEvent.exhibit_id == exhibit.id)
                         .options(joinedload(TimelineEvent.media), joinedload(TimelineEvent.update))
                         .order_by(TimelineEvent.created_at, TimelineEvent.id),
                         page=pagination_number("chapter"), per_page=10)
    saved = bool(g.user and db.session.get(Bookmark, (g.user.id, exhibit.id)))
    comparison = None
    if not preview and exhibit.media:
        first = db.session.scalar(select(TimelineEvent).where(
            TimelineEvent.exhibit_id == exhibit.id, TimelineEvent.event_type == "original"))
        latest = db.session.scalar(select(TimelineEvent).where(
            TimelineEvent.exhibit_id == exhibit.id, TimelineEvent.event_type == "update",
            TimelineEvent.media_id.is_not(None)).order_by(TimelineEvent.id.desc()).limit(1))
        if first and first.media and latest:
            comparison = (first, latest)
    return render_template("exhibit.html", exhibit=exhibit, preview=preview, events=events,
                           saved=saved, comparison=comparison)


@bp.get("/exhibits/<slug>")
def exhibit(slug):
    item = db.session.scalar(visible_exhibits().where(Exhibit.slug == slug))
    if not item:
        abort(404)
    return detail(item)


@bp.get("/guidelines")
def guidelines():
    return render_template("guidelines.html")


@bp.get("/exhibits/<slug>/ticket")
def ticket(slug):
    item = db.session.scalar(visible_exhibits().where(Exhibit.slug == slug))
    if not item:
        abort(404)
    return render_template("ticket.html", exhibit=item, share_url=url_for(".exhibit", slug=slug, _external=True))
