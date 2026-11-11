import io
import os
import re
from pathlib import Path
from uuid import uuid4

import pytest
from flask_migrate import upgrade
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.engine import make_url

from app import create_app
from app.models import Room, db


@pytest.fixture
def app(tmp_path):
    url = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.sqlite3'}"
    if not url.startswith("sqlite:") and not re.fullmatch(r"\w+_test", make_url(url).database or ""):
        pytest.fail("TEST_DATABASE_URL must refer to a disposable database ending in _test.")
    config = {
        "APP_ENV": "test", "TESTING": True, "SECRET_KEY": "test-session-only",
        "RATELIMIT_STORAGE_URI": "memory://",
        "SQLALCHEMY_DATABASE_URI": url, "UPLOAD_DIR": tmp_path / "uploads",
    }
    app = create_app(config)
    with app.app_context():
        upgrade(directory=str(Path(__file__).resolve().parents[1] / "migrations"))
        for table in reversed(db.metadata.sorted_tables):
            if table != Room.__table__:
                db.session.execute(delete(table))
        db.session.commit()
    yield app
    with app.app_context():
        db.engine.dispose()


def csrf(client, page="/dashboard"):
    html = client.get(page).get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, f"No CSRF token on {page}"
    return match.group(1)


def post(client, path, data=None, *, token=None, csrf_token=None):
    return client.post(path, data={"csrf_token": csrf_token or csrf(client),
                                   "action_token": token or uuid4().hex, **(data or {})})


def register(app, name):
    client = app.test_client()
    response = post(client, "/auth/register", dict(
        email=f"{name.lower()}@example.test", display_name=name, password="museum-testing-123",
        confirm_password="museum-testing-123",
    ), csrf_token=csrf(client, "/auth/register"))
    assert response.status_code == 303
    return client


def log_in(app, name):
    client = app.test_client()
    response = post(client, "/auth/login", dict(
        email=f"{name.lower()}@example.test", password="museum-testing-123",
    ), csrf_token=csrf(client, "/auth/login"))
    assert response.status_code == 303
    return client


def screenshot():
    payload = io.BytesIO()
    Image.new("RGB", (25, 16), "#b18b5e").save(payload, "PNG")
    payload.seek(0)
    return payload, "preview.png"


def draft(client, title="Campus Navigation"):
    response = post(client, "/exhibits")
    assert response.status_code == 303
    edit = response.location
    item_id = int(edit.split("/")[2])
    result = post(client, edit, dict(title=title, intention="Find the shortest walk to class.",
                                   story="A map based on familiar campus routes.", room_id="unfinished-interfaces",
                                   category="design", destination="dashboard"))
    assert result.status_code == 303
    return item_id, edit


def publish(client, title="Campus Navigation"):
    item_id, edit = draft(client, title)
    assert title.encode() in client.get(edit).data
    assert post(client, f"{edit}?step=2", dict(current_work="Desktop map", image=screenshot(),
                                                alt_text="Illustrative desktop map")).status_code == 303
    response = post(client, f"{edit}?step=3", dict(next_step="Build keyboard accessible mobile navigation",
                                                   skills="HTML, CSS", tags="maps, navigation", attribution="Map by creator",
                                                   permissions="ask", share_confirmed="yes"))
    assert response.status_code == 303
    assert b"Owner preview" in client.get(response.location).data
    response = post(client, f"/exhibits/{item_id}/publish")
    assert response.status_code == 303
    return item_id, response.location


def propose(client, exhibit_id, text="Private menu proposal"):
    assert post(client, f"/exhibits/{exhibit_id}/requests", dict(
        proposal=text, milestone="Add an accessible menu", materials="Original map with permission",
    )).status_code == 303


def submit_update(client, continuation_id, title="Mobile navigation is working"):
    response = post(client, f"/continuations/{continuation_id}/updates", dict(
        title=title, body="Added a keyboard friendly menu.", next_step="Test on smaller devices.",
        link="https://example.test/commit/abc", image=screenshot(), alt_text="Menu on a phone",
    ))
    assert response.status_code == 303
