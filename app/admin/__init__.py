from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from sqlalchemy import select

from ..models import Exhibit, ModerationDecision, Proposal, Report, db
from ..services import FormError, admin_only, exhibit_for_write, once, pagination_number, signed_in, value

bp = Blueprint("admin", __name__)


@bp.route("/exhibits/<int:exhibit_id>/report", methods=("GET", "POST"))
@signed_in
def report(exhibit_id):
    exhibit = exhibit_for_write(exhibit_id) if request.method == "POST" else db.get_or_404(Exhibit, exhibit_id)
    if not exhibit.is_public and not (exhibit.moderation_hidden and exhibit.owner_id == g.user.id):
        abort(404)
    if request.method == "POST":
        if db.session.scalar(select(Report.id).where(
                Report.exhibit_id == exhibit.id, Report.reporter_id == g.user.id, Report.status == "open")):
            abort(409, "You already have an open report for this exhibit.")
        try:
            reason = value("reason", "Report or appeal details", 600)
        except FormError as error:
            return render_template("report.html", exhibit=exhibit, error=error), 400
        once()
        exhibit.review_state = "flagged"
        db.session.add(Report(exhibit=exhibit, reporter_id=g.user.id, reason=reason))
        db.session.commit()
        flash("Report sent privately to the museum administrators.", "success")
        return redirect(url_for("museum.exhibit", slug=exhibit.slug) if exhibit.is_public else
                        url_for("exhibits.dashboard"), code=303)
    return render_template("report.html", exhibit=exhibit)


@bp.get("/admin/reports")
@admin_only
def reports():
    reports = db.paginate(select(Report).order_by((Report.status == "open").desc(), Report.id.desc()),
                          page=pagination_number(), per_page=20)
    history = db.session.scalars(select(ModerationDecision).order_by(ModerationDecision.id.desc()).limit(20))
    return render_template("admin.html", reports=reports, history=list(history),
                           report_page=lambda number: url_for(".reports", page=number))


@bp.get("/admin/exhibits/<int:exhibit_id>")
@admin_only
def inspect(exhibit_id):
    exhibit = db.get_or_404(Exhibit, exhibit_id)
    proposals = db.session.scalars(select(Proposal).where(Proposal.exhibit_id == exhibit.id).order_by(Proposal.id))
    return render_template("inspect.html", exhibit=exhibit, proposals=list(proposals))


@bp.post("/admin/exhibits/<int:exhibit_id>/<action>")
@admin_only
def decide(exhibit_id, action):
    if action not in {"hide", "unhide", "resolve"}:
        abort(404)
    exhibit = exhibit_for_write(exhibit_id)
    try:
        note = value("note", "Moderation note", 600)
    except FormError as error:
        abort(400, str(error))
    report_id = request.form.get("report_id", type=int)
    item = db.session.get(Report, report_id) if report_id else None
    if report_id and (not item or item.exhibit_id != exhibit.id):
        abort(404)
    if (action == "hide" and exhibit.moderation_hidden) or (action == "unhide" and not exhibit.moderation_hidden):
        abort(409, "This visibility decision has already been applied.")
    if action == "resolve" and (not item or item.status != "open"):
        abort(409, "Choose an open report.")
    once()
    if action in {"hide", "unhide"}:
        exhibit.moderation_hidden = action == "hide"
    if item:
        item.status = "resolved"
    unresolved = db.session.scalar(select(Report.id).where(Report.exhibit_id == exhibit.id, Report.status == "open").limit(1))
    exhibit.review_state = "flagged" if unresolved or exhibit.moderation_hidden else "clear"
    db.session.add(ModerationDecision(exhibit=exhibit, moderator_id=g.user.id, report_id=report_id, action=action, note=note))
    db.session.commit()
    flash("Moderation decision recorded.", "success")
    return redirect(url_for(".reports"), code=303)
