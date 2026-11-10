from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import select

from ..models import Continuation, Exhibit, Proposal, Update, db, utcnow
from ..services import (FormError, add_event, attach_image, commit, exhibit_for_write, external_link, once,
                        option, read_image, signed_in, value)

bp = Blueprint("continuations", __name__)


def dashboard(tab):
    return redirect(url_for("exhibits.dashboard", tab=tab), code=303)


def resolve(item, status, note=""):
    item.status = status
    item.pending_slot = None
    item.decision_note = note
    item.decided_at = utcnow()


def pending(exhibit_id):
    return select(Proposal).where(Proposal.exhibit_id == exhibit_id, Proposal.status == "pending")


def active(exhibit_id):
    return db.session.scalar(select(Continuation).where(
        Continuation.exhibit_id == exhibit_id, Continuation.active_slot == 1))


@bp.route("/exhibits/<int:exhibit_id>/requests", methods=("GET", "POST"))
@signed_in
def request_continuation(exhibit_id):
    exhibit = exhibit_for_write(exhibit_id, public=True) if request.method == "POST" else db.get_or_404(Exhibit, exhibit_id)
    if not exhibit.is_public:
        abort(404)
    if exhibit.owner_id == g.user.id:
        abort(403, "You can’t propose a continuation on your own exhibit.")
    if active(exhibit.id):
        abort(409, "This exhibit already has an active contributor.")
    if db.session.scalar(pending(exhibit.id).where(Proposal.applicant_id == g.user.id)):
        abort(409, "You already have a pending request for this exhibit.")
    if request.method == "POST":
        try:
            data = dict(proposal=value("proposal", "Proposal", 1400), milestone=value("milestone", "First milestone", 240),
                        materials=value("materials", "Materials you will use", 400))
        except FormError as error:
            return render_template("proposal.html", exhibit=exhibit, error=error), 400
        once()
        db.session.add(Proposal(exhibit_id=exhibit.id, applicant_id=g.user.id, **data))
        db.session.commit()
        flash("Proposal sent. Keep exploring while the creator reviews it.", "success")
        return dashboard("my-requests")
    return render_template("proposal.html", exhibit=exhibit)


def lock_request(proposal_id, *, owner=False, public=False):
    exhibit_id = db.session.scalar(select(Proposal.exhibit_id).where(Proposal.id == proposal_id))
    if not exhibit_id:
        abort(404)
    exhibit = exhibit_for_write(exhibit_id, owner=owner, public=public)
    item = db.session.get(Proposal, proposal_id)
    if item.status != "pending":
        abort(409, "This request is no longer pending.")
    return exhibit, item


@bp.post("/requests/<int:proposal_id>/accept")
@signed_in
def accept(proposal_id):
    exhibit, item = lock_request(proposal_id, owner=True, public=True)
    if active(exhibit.id):
        abort(409, "This exhibit already has an active contributor.")
    note = decision_note()
    once()
    resolve(item, "accepted", note)
    for other in db.session.scalars(pending(exhibit.id).where(Proposal.id != item.id)):
        resolve(other, "closed", "The creator accepted another proposal.")
    db.session.add(Continuation(exhibit=exhibit, request=item, contributor=item.applicant))
    exhibit.continuation_state = "in-progress"
    add_event(exhibit, item.applicant, "accepted", "A new chapter begins")
    db.session.commit()
    flash("Request accepted. The contributor can now submit progress.", "success")
    return dashboard("requests")


def decision_note():
    try:
        return value("note", "Decision note", 400, required=False)
    except FormError as error:
        abort(400, str(error))


@bp.post("/requests/<int:proposal_id>/decline")
@signed_in
def decline(proposal_id):
    _, item = lock_request(proposal_id, owner=True)
    note = decision_note()
    once()
    resolve(item, "declined", note)
    db.session.commit()
    flash("Request declined.", "success")
    return dashboard("requests")


@bp.post("/requests/<int:proposal_id>/withdraw")
@signed_in
def withdraw_request(proposal_id):
    _, item = lock_request(proposal_id)
    if item.applicant_id != g.user.id:
        abort(403)
    once()
    resolve(item, "withdrawn")
    db.session.commit()
    flash("Request withdrawn.", "success")
    return dashboard("my-requests")


def lock_continuation(continuation_id, *, public=False):
    exhibit_id = db.session.scalar(select(Continuation.exhibit_id).where(Continuation.id == continuation_id))
    if not exhibit_id:
        abort(404)
    return exhibit_for_write(exhibit_id, public=public), db.session.get(Continuation, continuation_id)


@bp.route("/continuations/<int:continuation_id>/updates", methods=("GET", "POST"))
@signed_in
def submit_update(continuation_id):
    if request.method == "POST":
        exhibit, continuation = lock_continuation(continuation_id, public=True)
    else:
        continuation = db.get_or_404(Continuation, continuation_id)
        exhibit = continuation.exhibit
        if not exhibit.is_public:
            abort(404)
    if continuation.contributor_id != g.user.id:
        abort(403)
    if continuation.status != "active":
        abort(409, "Only an active continuation can submit new work.")
    if request.method == "POST":
        try:
            fields = dict(title=value("title", "Update title", 100), body=value("body", "Progress description", 2000),
                          next_step=value("next_step", "Next step", 240), link=external_link("link", "Update link"))
            image = read_image(required=True)
        except FormError as error:
            return render_template("update.html", continuation=continuation, error=error), 400
        once()
        update = Update(continuation=continuation, author_id=g.user.id, **fields)
        db.session.add(update)
        commit(attach_image(image, update=update))
        flash("Update submitted for review. It will appear publicly after approval.", "success")
        return dashboard("continuations")
    return render_template("update.html", continuation=continuation)


@bp.post("/updates/<int:update_id>/<decision>")
@signed_in
def review(update_id, decision):
    if decision not in {"approve", "reject"}:
        abort(404)
    exhibit_id = db.session.scalar(select(Continuation.exhibit_id).join(
        Update, Update.continuation_id == Continuation.id).where(Update.id == update_id))
    if not exhibit_id:
        abort(404)
    exhibit = exhibit_for_write(exhibit_id, owner=True, public=decision == "approve")
    update = db.session.get(Update, update_id)
    if update.review_status != "pending" or update.continuation.status != "active":
        abort(409, "This update is no longer waiting for review.")
    note = decision_note()
    once()
    update.review_status = "approved" if decision == "approve" else "rejected"
    update.reviewed_by, update.reviewed_at, update.review_note = g.user.id, utcnow(), note
    if decision == "approve":
        add_event(exhibit, update.author, "update", update.title, body=update.body, next_step=update.next_step,
                  media=update.media, update=update)
    db.session.commit()
    flash("Update published to the timeline." if decision == "approve" else "Update returned to its author.", "success")
    return dashboard("review")


@bp.post("/continuations/<int:continuation_id>/<action>")
@signed_in
def close_continuation(continuation_id, action):
    statuses = {"withdraw": "withdrawn", "end": "ended", "complete": "completed"}
    if action not in statuses:
        abort(404)
    exhibit, continuation = lock_continuation(continuation_id)
    is_contributor = continuation.contributor_id == g.user.id
    if (action == "withdraw" and not is_contributor) or (action != "withdraw" and exhibit.owner_id != g.user.id):
        abort(403)
    if continuation.status != "active":
        abort(409, "This continuation has already ended.")
    try:
        note = value("note", "Reason", 400, required=action == "end")
    except FormError as error:
        abort(400, str(error))
    if action == "complete" and not db.session.scalar(select(Update.id).where(
            Update.continuation_id == continuation.id, Update.review_status == "approved").limit(1)):
        abort(409, "Approve an update before marking the milestone complete.")
    once()
    continuation.status, continuation.active_slot, continuation.end_reason = statuses[action], None, note
    exhibit.continuation_state = "milestone" if action == "complete" else "open"
    titles = {"withdraw": "The contributor stepped back", "end": "The continuation ended", "complete": "Milestone reached"}
    add_event(exhibit, continuation.contributor, statuses[action], titles[action])
    for update in db.session.scalars(select(Update).where(
            Update.continuation_id == continuation.id, Update.review_status == "pending")):
        update.review_status, update.reviewed_by, update.reviewed_at = "rejected", g.user.id, utcnow()
        update.review_note = "The continuation closed before this update was approved."
    db.session.commit()
    flash("Continuation updated. Approved chapters and credit have been retained.", "success")
    return dashboard("continuations" if is_contributor else "requests")
