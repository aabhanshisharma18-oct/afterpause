from concurrent.futures import ThreadPoolExecutor
import re
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select

from app import create_app
from app.models import Continuation, Exhibit, Media, ModerationDecision, Proposal, Report, TimelineEvent, Update, User, db
from conftest import csrf, draft, log_in, post, propose, publish, register, screenshot, submit_update


def review_version(owner, proposal_id):
    html = owner.get("/dashboard?tab=requests").get_data(as_text=True)
    form = re.search(rf'action="/requests/{proposal_id}/accept"[^>]*>(.*?)</form>', html, re.S)
    assert form
    match = re.search(r'name="proposal_version" value="([a-f0-9]{64})"', form.group(1))
    assert match
    return match.group(1)


def test_full_journey_moderation_and_restart(app):
    creator = register(app, "Creator")
    contributor = register(app, "Contributor")
    admin = register(app, "Moderator")
    visitor = app.test_client()
    with app.app_context():
        user = db.session.scalar(select(User).where(User.email == "moderator@example.test"))
        user.role = "admin"
        db.session.commit()
        assert user.password_hash != "museum-testing-123"
    item_id, public = publish(creator)

    assert b"Campus Navigation" in visitor.get("/explore?room=unfinished-interfaces&skill=CSS&state=open&q=maps").data
    assert b"No exhibits match" in visitor.get("/explore?q=%25").data
    assert post(creator, f"/exhibits/{item_id}/requests").status_code == 403
    assert post(contributor, f"/exhibits/{item_id}/edit").status_code == 403
    propose(contributor, item_id)
    with app.app_context():
        proposal_id = db.session.scalar(select(Proposal.id))
    assert post(contributor, f"/requests/{proposal_id}/accept").status_code == 403
    assert post(contributor, f"/exhibits/{item_id}/requests").status_code == 409
    assert b"Private menu proposal" in contributor.get("/dashboard?tab=my-requests").data
    assert post(creator, f"/requests/{proposal_id}/accept", {"note": "Private acceptance note", "proposal_version": review_version(creator, proposal_id)}).status_code == 303
    with app.app_context():
        continuation_id = db.session.scalar(select(Continuation.id))

    submit_update(contributor, continuation_id)
    with app.app_context():
        update_id = db.session.scalar(select(Update.id))
        image = db.session.scalar(select(Media).where(Media.update_id == update_id))
        private_media = f"/media/{image.storage_key}"
    assert visitor.get(private_media).status_code == 404
    assert creator.get(private_media).status_code == 200
    assert b"Mobile navigation is working" not in visitor.get(public).data
    assert post(contributor, f"/updates/{update_id}/approve").status_code == 403
    assert post(creator, f"/updates/{update_id}/approve", {"note": "Private review note"}).status_code == 303
    assert post(creator, f"/updates/{update_id}/approve").status_code == 409
    assert post(creator, f"/continuations/{continuation_id}/complete").status_code == 303
    assert post(contributor, f"/continuations/{continuation_id}/updates").status_code == 409

    restarted = create_app({key: app.config[key] for key in (
        "APP_ENV", "TESTING", "SECRET_KEY", "SQLALCHEMY_DATABASE_URI", "UPLOAD_DIR",
    )})
    guest = restarted.test_client()
    html = guest.get(public).data
    for text in (b"Original work by Creator", b"Mobile navigation is working", b"Contributor", b"Milestone reached"):
        assert text in html
    for text in (b"Private menu proposal", b"Private acceptance note", b"Private review note"):
        assert text not in html
    assert guest.get(private_media).content_type == "image/webp"

    assert post(contributor, f"/exhibits/{item_id}/report", {"reason": "Check attribution privately"}).status_code == 303
    assert contributor.get("/admin/reports").status_code == 403
    assert b"Check attribution privately" in admin.get("/admin/reports").data
    assert b"Private menu proposal" in admin.get(f"/admin/exhibits/{item_id}").data
    assert post(contributor, f"/admin/exhibits/{item_id}/hide").status_code == 403
    with app.app_context():
        report_id = db.session.scalar(select(Report.id))
    assert post(admin, f"/admin/exhibits/{item_id}/hide", {"note": "Temporary audit", "report_id": report_id}).status_code == 303
    assert guest.get(public).status_code == 404
    assert guest.get(private_media).status_code == 404
    assert b"Campus Navigation" not in guest.get("/explore?q=Campus").data
    assert post(creator, f"/exhibits/{item_id}/report", {"reason": "I am appealing the attribution decision."}).status_code == 303
    assert post(admin, f"/admin/exhibits/{item_id}/unhide", {"note": "Credit verified"}).status_code == 303
    assert b"Mobile navigation is working" in guest.get(public).data
    with app.app_context():
        assert set(db.session.scalars(select(ModerationDecision.action))) == {"hide", "unhide"}
    propose(contributor, item_id, "A second chapter is possible")


def test_draft_validation_deduplication_and_archive(app):
    owner = register(app, "Owner")
    other = register(app, "Other")
    guest = app.test_client()
    item_id, edit = draft(owner, "Private draft record")
    with app.app_context():
        slug = db.session.get(Exhibit, item_id).slug
    assert guest.get(f"/exhibits/{slug}").status_code == 404
    assert b"Private draft record" not in guest.get("/explore?q=Private").data
    assert other.get(f"/exhibits/{item_id}/preview").status_code == 403
    assert owner.post(edit, data={"title": "No CSRF"}).status_code == 400
    response = post(owner, f"{edit}?step=2", dict(current_work="Entered text is kept",
                                                   image=(__import__("io").BytesIO(b"<svg/>"), "fake.png"),
                                                   alt_text="An image"))
    assert response.status_code == 400
    assert b"Entered text is kept" in response.data and b"Use a static PNG" in response.data
    assert post(owner, f"{edit}?step=2", dict(current_work="Finished a map", image=screenshot(),
                                               alt_text="A map")).status_code == 303
    with app.app_context():
        image = db.session.scalar(select(Media))
        media_url = f"/media/{image.storage_key}"
    assert guest.get(media_url).status_code == 404
    assert other.get(media_url).status_code == 404
    assert owner.get(media_url).status_code == 200
    token = uuid4().hex
    assert post(owner, "/exhibits", token=token).status_code == 303
    assert post(owner, "/exhibits", token=token).status_code == 409
    new_id, public = publish(owner, "Visible Map")
    assert post(other, f"/exhibits/{new_id}/bookmark", {"save": "yes"}).status_code == 303
    assert b"Visible Map" in other.get("/dashboard?tab=saved").data
    assert post(owner, f"/exhibits/{new_id}/archive").status_code == 303
    assert guest.get(public).status_code == 404
    assert b"Visible Map" not in other.get("/dashboard?tab=saved").data
    assert post(owner, f"/exhibits/{new_id}/publish").status_code == 303
    with app.app_context():
        assert len(list(db.session.scalars(select(TimelineEvent).where(TimelineEvent.exhibit_id == new_id)))) == 1


def test_simultaneous_acceptance_and_transaction_rollback(app, monkeypatch):
    from app import continuations

    owner = register(app, "Owner")
    first = register(app, "First")
    second = register(app, "Second")
    exhibit_id, _ = publish(owner)
    propose(first, exhibit_id)
    propose(second, exhibit_id)
    with app.app_context():
        ids = list(db.session.scalars(select(Proposal.id).order_by(Proposal.id)))

    versions = [review_version(owner, proposal_id) for proposal_id in ids]
    original = continuations.add_event
    def fail_after_flush(*_args, **_kwargs):
        db.session.flush()
        raise RuntimeError("Simulated failure before event creation")
    monkeypatch.setattr(continuations, "add_event", fail_after_flush)
    with pytest.raises(RuntimeError, match="Simulated failure"):
        post(owner, f"/requests/{ids[0]}/accept", {"proposal_version": versions[0]})
    with app.app_context():
        assert list(db.session.scalars(select(Proposal.status))) == ["pending", "pending"]
        assert db.session.scalar(select(Continuation.id)) is None
        assert db.session.get(Exhibit, exhibit_id).continuation_state == "open"
        assert list(db.session.scalars(select(TimelineEvent.event_type))) == ["original"]
    monkeypatch.setattr(continuations, "add_event", original)

    clients = [log_in(app, "Owner"), log_in(app, "Owner")]
    csrf_tokens = [csrf(client) for client in clients]
    barrier = Barrier(2)
    def accept(index):
        barrier.wait(timeout=5)
        return post(clients[index], f"/requests/{ids[index]}/accept",
                    {"proposal_version": versions[index]}, csrf_token=csrf_tokens[index]).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(accept, range(2)))
    assert sorted(outcomes) == [303, 409]
    with app.app_context():
        assert set(db.session.scalars(select(Proposal.status))) == {"accepted", "closed"}
        assert list(db.session.scalars(select(Continuation.active_slot))) == [1]
        assert list(db.session.scalars(select(TimelineEvent.event_type).order_by(TimelineEvent.id))) == ["original", "accepted"]


def test_private_withdrawal_and_rejection(app):
    owner = register(app, "Owner")
    contributor = register(app, "Contributor")
    stranger = register(app, "Stranger")
    item, public = publish(owner)
    propose(contributor, item)
    with app.app_context():
        request_id = db.session.scalar(select(Proposal.id))
    assert post(stranger, f"/requests/{request_id}/withdraw").status_code == 403
    assert post(owner, f"/requests/{request_id}/decline", {"note": "Private decline note", "proposal_version": review_version(owner, request_id)}).status_code == 303
    assert b"Private decline note" in contributor.get("/dashboard?tab=my-requests").data
    assert b"Private decline note" not in stranger.get(public).data
    propose(contributor, item)
    with app.app_context():
        request_id = db.session.scalar(select(Proposal.id).where(Proposal.status == "pending"))
    assert post(contributor, f"/requests/{request_id}/withdraw").status_code == 303
    propose(contributor, item)
    with app.app_context():
        request_id = db.session.scalar(select(Proposal.id).where(Proposal.status == "pending"))
    assert post(owner, f"/requests/{request_id}/accept", {"proposal_version": review_version(owner, request_id)}).status_code == 303
    with app.app_context():
        continuation_id = db.session.scalar(select(Continuation.id))
    submit_update(contributor, continuation_id, "Private unfinished update")
    assert post(contributor, f"/continuations/{continuation_id}/withdraw").status_code == 303
    with app.app_context():
        update_id = db.session.scalar(select(Update.id))
    assert post(owner, f"/updates/{update_id}/approve").status_code == 409
    assert b"Private unfinished update" not in stranger.get(public).data
    assert b"The contributor stepped back" in stranger.get(public).data


def test_registration_profile_and_rate_limit(app):
    member = register(app, "Visitor")
    assert b"Visitor" in member.get("/auth/profile").data
    assert post(member, "/auth/profile", {"display_name": "<strong>New credit</strong>"}).status_code == 303
    assert b"&lt;strong&gt;New credit&lt;/strong&gt;" in member.get("/auth/profile").data
    assert post(member, "/auth/logout").status_code == 303
    assert member.get("/dashboard").status_code == 303
    login = member.get("/auth/login?next=//elsewhere.example")
    assert login.status_code == 200
    login_response = post(member, "/auth/login?next=//elsewhere.example",
                          {"email": "visitor@example.test", "password": "museum-testing-123"},
                          csrf_token=csrf(member, "/auth/login"))
    assert login_response.location == "/dashboard"
    app.config["TEST_RATE_LIMIT"] = True
    guest = app.test_client()
    token = csrf(guest, "/auth/login")
    for _ in range(10):
        assert post(guest, "/auth/login", {"email": "wrong@example.test", "password": "incorrect123"},
                    csrf_token=token).status_code == 400
    assert post(guest, "/auth/login", {"email": "wrong@example.test", "password": "incorrect123"},
                csrf_token=token).status_code == 429


def test_pending_proposal_can_be_revised_and_stale_review_is_rejected(app):
    owner = register(app, "Owner")
    contributor = register(app, "Contributor")
    stranger = register(app, "Stranger")
    exhibit_id, public = publish(owner)
    propose(contributor, exhibit_id)
    with app.app_context():
        proposal_id = db.session.scalar(select(Proposal.id))

    edit = f"/requests/{proposal_id}/edit"
    old_version = review_version(owner, proposal_id)
    form = contributor.get(edit)
    assert form.status_code == 200 and b"Private menu proposal" in form.data
    assert edit.encode() in contributor.get(public).data
    assert edit.encode() not in stranger.get(public).data
    assert stranger.get(edit).status_code == 403
    revised = {
        "proposal_version": old_version,
        "proposal": "Private revised plan for keyboard navigation",
        "milestone": "Test the menu with a keyboard",
        "materials": "Original map with permission",
    }
    assert post(owner, edit, revised).status_code == 403
    assert post(contributor, edit, {**revised, "milestone": ""}).status_code == 400
    assert post(contributor, edit, revised).location == public + "#invitation"
    assert post(contributor, edit, revised).status_code == 409
    assert revised["proposal"].encode() not in app.test_client().get(public).data
    assert revised["proposal"].encode() in owner.get("/dashboard?tab=requests").data

    accept = f"/requests/{proposal_id}/accept"
    assert post(owner, accept, {"proposal_version": old_version}).status_code == 409
    assert post(owner, accept, {"proposal_version": review_version(owner, proposal_id)}).status_code == 303
    assert b"Submit progress" in contributor.get(public).data
    assert edit.encode() not in contributor.get(public).data
    assert post(contributor, edit, revised).status_code == 409
