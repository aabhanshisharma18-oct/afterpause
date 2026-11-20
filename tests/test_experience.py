from sqlalchemy import func, select

from app.models import Exhibit, Flower, GuestEntry, Media, Proposal, User, db
from app.showcase import seed_gallery
from conftest import csrf, post, publish, register


def demo(app):
    client = app.test_client()
    response = post(client, "/auth/demo", csrf_token=csrf(client, "/auth/login"))
    assert response.status_code == 303
    assert response.location.endswith("/dashboard")
    assert b"Demo workspace" in client.get(response.location).data
    return client


def test_demo_opens_populated_dashboard_and_can_publish(app):
    client = demo(app)
    page = client.get("/dashboard")
    assert b"BorrowBox" in page.data and b"Campus Guide" in page.data
    with client.session_transaction() as session:
        owner = session["user_id"]
    with app.app_context():
        draft = db.session.scalar(select(Exhibit).where(Exhibit.owner_id == owner, Exhibit.title == "BorrowBox"))
        draft_id = draft.id
    response = post(client, f"/exhibits/{draft_id}/publish")
    assert response.status_code == 303
    assert b"BorrowBox" in client.get(response.location).data
    assert client.get("/admin/reports").status_code == 403


def test_demo_isolation_media_and_role_switching(app):
    first, second = demo(app), demo(app)
    with first.session_transaction() as session:
        sandbox, owner = session["demo_sandbox"], session["user_id"]
    with app.app_context():
        item = db.session.scalar(select(Exhibit).where(Exhibit.owner_id == owner, Exhibit.title == "Campus Guide"))
        slug, key, item_id = item.slug, item.media[0].storage_key, item.id
        assert db.session.get(User, owner).role == "member"
    assert first.get(f"/exhibits/{slug}").status_code == 200
    assert second.get(f"/exhibits/{slug}").status_code == 404
    assert second.get(f"/media/{key}").status_code == 404
    assert app.test_client().get(f"/media/{key}").status_code == 404
    assert post(second, f"/exhibits/{item_id}/flowers").status_code == 404
    assert slug.encode() not in second.get("/explore").data
    assert post(first, "/auth/demo", {"role": "contributor"}).status_code == 303
    with first.session_transaction() as session:
        assert session["demo_sandbox"] == sandbox and session["user_id"] != owner
    assert b"My requests" in first.get("/dashboard?tab=my-requests").data
    assert b"Demo Contributor" in first.get("/dashboard").data


def test_flowers_guestbook_and_delete_permissions(app):
    creator = register(app, "Maker")
    item_id, url = publish(creator)
    guest = register(app, "Visitor")
    assert post(guest, f"/exhibits/{item_id}/flowers").status_code == 303
    assert post(guest, f"/exhibits/{item_id}/flowers").status_code == 303
    assert post(guest, f"/exhibits/{item_id}/guest-book", {"body": "<script>alert(1)</script>"}).status_code == 303
    page = guest.get(url)
    assert b"&lt;script&gt;" in page.data and b"Flower placed" in page.data
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Flower)) == 1
        note_id = db.session.scalar(select(GuestEntry.id))
    stranger = register(app, "Stranger")
    assert post(stranger, f"/guest-book/{note_id}/delete").status_code == 403
    assert post(creator, f"/guest-book/{note_id}/delete").status_code == 303
    assert b"&lt;script&gt;" not in creator.get(url).data


def test_bundled_collection_is_idempotent_and_navigation_works(app):
    with app.app_context():
        from werkzeug.security import generate_password_hash
        db.session.add(User(email="collection@afterpause.invalid", display_name="Existing member",
                            password_hash=generate_password_hash("test-account-only")))
        db.session.commit()
        seed_gallery()
        seed_gallery()
        owner = db.session.scalar(select(User).where(User.role == "collection"))
        assert owner.email != "collection@afterpause.invalid"
        assert db.session.scalar(select(func.count()).select_from(Exhibit)) == 6
        assert db.session.scalar(select(func.count()).select_from(Media)) == 6
    client = app.test_client()
    for path in ("/", "/explore", "/collection", "/statistics", "/gift-shop", "/auth/login"):
        response = client.get(path)
        assert response.status_code == 200, path
    page = client.get("/explore?cause=burnout")
    assert b"One More Level" in page.data and b"Campus Guide" not in page.data
    assert b"fictional examples" in client.get("/statistics").data
    with app.app_context():
        key = db.session.scalar(select(Media.storage_key).limit(1))
    assert client.get(f"/media/{key}").status_code == 200


def test_demo_disabled_and_csrf_required(app):
    client = app.test_client()
    assert client.post("/auth/demo").status_code == 400
    app.config["DEMO_LOGIN_ENABLED"] = False
    assert b"Demo sign-in" not in client.get("/auth/login").data
    assert post(client, "/auth/demo", csrf_token=csrf(client, "/auth/login")).status_code == 404


def test_invalid_dates_are_not_saved(app):
    creator = register(app, "Maker")
    item_id, _ = publish(creator)
    response = post(creator, f"/exhibits/{item_id}/edit?step=2", {
        "current_work": "Map", "born_on": "2024-08-01", "paused_on": "2024-03-01",
    })
    assert response.status_code == 400
    assert b"on or after" in response.data


def test_link_checker_rejects_private_and_pins_public_ip(monkeypatch):
    from app.museum import integrations
    import pytest
    monkeypatch.setattr(integrations.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(ValueError):
        integrations.check_demo_url("https://example.test")
    with pytest.raises(ValueError):
        integrations.check_demo_url("https://example.test:8080")
    monkeypatch.setattr(integrations.socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, '', ('93.184.216.34', 443))])
    calls = []
    class Connection:
        def __init__(self, *a, **kw):
            pass
        def request(self, method, path, headers):
            self._create_connection(("example.test", 443))
        def getresponse(self):
            return type("Response", (), {"status": 302})()
        def close(self):
            pass
    monkeypatch.setattr(integrations.http.client, "HTTPSConnection", Connection)
    monkeypatch.setattr(integrations.socket, "create_connection", lambda target, *a: calls.append(target))
    result = integrations.check_demo_url("https://example.test")
    assert result["status"] == 302
    assert calls == [("93.184.216.34", 443)]


def test_github_metadata_visible_scope_errors_and_success(app, monkeypatch):
    from app.museum import integrations
    client = demo(app)
    with client.session_transaction() as session:
        sandbox = session["demo_sandbox"]
    with app.app_context():
        item = db.session.scalar(select(Exhibit).where(Exhibit.sandbox_id == sandbox).limit(1))
        slug = item.slug
        item.repository_url = "https://github.com/example/project"
        db.session.commit()
    monkeypatch.setattr(integrations, "github_metadata", lambda *a: {"stars": 3, "archived": True, "final_words": "done"})
    assert client.get(f"/exhibits/{slug}/metadata/github").json["stars"] == 3
    assert app.test_client().get(f"/exhibits/{slug}/metadata/github").status_code == 404


def test_reading_room_starts_pending_and_restart_keeps_owner_role(app):
    from app.models import Continuation, TimelineEvent
    client = demo(app)
    assert post(client, "/auth/demo", {"role": "contributor"}).status_code == 303
    with client.session_transaction() as session:
        old_sandbox = session["demo_sandbox"]
    with app.app_context():
        proposal = db.session.scalar(select(Proposal).join(Exhibit).where(
            Exhibit.sandbox_id == old_sandbox, Exhibit.title == "Reading Room"))
        assert proposal.status == "pending" and proposal.continuation is None
        assert proposal.exhibit.continuation_state == "open"
        assert db.session.scalar(select(func.count()).select_from(TimelineEvent).where(
            TimelineEvent.exhibit_id == proposal.exhibit_id)) == 1
        proposal_id, version = proposal.id, proposal.review_key
    page = client.get("/dashboard?tab=requests")
    assert b"Accept proposal" in page.data and b"Decline proposal" in page.data
    assert post(client, f"/requests/{proposal_id}/accept", {"proposal_version": version}).status_code == 303
    assert b"Restart demo with pending proposals" in client.get("/dashboard?tab=requests").data
    assert post(client, "/auth/demo", {"role": "contributor", "restart": "yes"}).status_code == 303
    with client.session_transaction() as session:
        assert session["demo_sandbox"] != old_sandbox
        new_sandbox, user_id = session["demo_sandbox"], session["user_id"]
    with app.app_context():
        assert db.session.get(User, user_id).email.endswith("-contributor@afterpause.invalid")
        old_proposal = db.session.get(Proposal, proposal_id)
        assert old_proposal.status == "accepted" and old_proposal.continuation.status == "active"
        fresh = db.session.scalar(select(Proposal).join(Exhibit).where(
            Exhibit.sandbox_id == new_sandbox, Exhibit.title == "Reading Room"))
        assert fresh.status == "pending" and fresh.continuation is None
    assert b"Accept proposal" in client.get("/dashboard?tab=requests").data
    assert client.post("/auth/demo", data={"restart": "yes"}).status_code == 400
