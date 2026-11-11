import io
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app import create_app
from app.models import Exhibit, Media, TimelineEvent, db
from conftest import log_in, post, publish, register


def empty_draft(owner):
    response = post(owner, "/exhibits")
    assert response.status_code == 303
    return int(response.location.split("/")[2]), response.location


@pytest.mark.parametrize("step, fields, column, expected", [
    (1, {"title": "An unfinished idea"}, "title", "An unfinished idea"),
    (2, {"pause_note": "Returning after exams"}, "pause_note", "Returning after exams"),
    (3, {"next_step": "Build the first screen"}, "next_step", "Build the first screen"),
])
def test_partial_sections_can_be_saved_and_reopened(app, step, fields, column, expected):
    owner = register(app, "Owner")
    item_id, edit = empty_draft(owner)
    response = post(owner, f"{edit}?step={step}", {**fields, "destination": "dashboard"})
    assert response.location == "/dashboard"
    assert expected.encode() in owner.get(f"{edit}?step={step}").data
    with app.app_context():
        exhibit = db.session.get(Exhibit, item_id)
        assert getattr(exhibit, column) == expected
        assert exhibit.room_id is None
        assert exhibit.publication_state == "draft"
        assert exhibit.submission_progress == {
            "completed_steps": [], "resume_step": 1, "ready": False,
        }


def test_partial_draft_survives_restart_and_stays_private(app):
    owner = register(app, "Owner")
    stranger = register(app, "Stranger")
    item_id, edit = empty_draft(owner)
    assert post(owner, edit, {"title": "A private unfinished idea", "destination": "dashboard"}).status_code == 303
    with app.app_context():
        slug = db.session.get(Exhibit, item_id).slug
    assert stranger.get(edit).status_code == 403
    assert post(stranger, edit, {"title": "Changed by another user", "destination": "dashboard"}).status_code == 403
    guest = app.test_client()
    assert guest.get(f"/exhibits/{slug}").status_code == 404
    assert b"A private unfinished idea" not in guest.get("/explore?q=unfinished").data
    assert post(owner, f"/exhibits/{item_id}/publish").location.endswith("/preview")
    with app.app_context():
        assert db.session.get(Exhibit, item_id).publication_state == "draft"
        assert db.session.scalar(select(func.count()).select_from(TimelineEvent)) == 0
    restarted = create_app({key: app.config[key] for key in (
        "APP_ENV", "TESTING", "SECRET_KEY", "SQLALCHEMY_DATABASE_URI", "UPLOAD_DIR",
        "RATELIMIT_STORAGE_URI",
    )})
    try:
        client = log_in(restarted, "Owner")
        assert b"A private unfinished idea" in client.get(edit).data
    finally:
        with restarted.app_context():
            db.session.remove()
            db.engine.dispose()


def test_partial_save_keeps_validation_and_duplicate_action_protection(app):
    owner = register(app, "Owner")
    item_id, edit = empty_draft(owner)
    token = uuid4().hex
    assert post(owner, edit, {"title": "Saved once", "destination": "dashboard"}, token=token).status_code == 303
    assert post(owner, edit, {"title": "Duplicate change", "destination": "dashboard"}, token=token).status_code == 409
    assert post(owner, edit, {"title": "Not saved without other fields"}).status_code == 400
    assert post(owner, edit, {"title": "Invalid room", "room_id": "missing", "destination": "dashboard"}).status_code == 400
    assert post(owner, edit, {"title": "x" * 101, "destination": "dashboard"}).status_code == 400
    response = post(owner, f"{edit}?step=2", {
        "current_work": "Keep this entered text", "destination": "dashboard",
        "image": (io.BytesIO(b"<svg/>"), "fake.png"), "alt_text": "An unsafe image",
    })
    assert response.status_code == 400
    assert b"Keep this entered text" in response.data
    with app.app_context():
        exhibit = db.session.get(Exhibit, item_id)
        assert exhibit.title == "Saved once"
        assert exhibit.current_work == ""
        assert db.session.scalar(select(func.count()).select_from(Media)) == 0


def test_partial_save_cannot_clear_required_fields_of_published_exhibits(app):
    owner = register(app, "Owner")
    item_id, public = publish(owner)
    response = post(owner, f"/exhibits/{item_id}/edit", {
        "title": "An incomplete replacement", "destination": "dashboard",
    })
    assert response.status_code == 400
    with app.app_context():
        exhibit = db.session.get(Exhibit, item_id)
        assert exhibit.title == "Campus Navigation"
        assert exhibit.publication_state == "published"
        assert exhibit.submission_progress["ready"] is True
    assert b"Campus Navigation" in app.test_client().get(public).data
