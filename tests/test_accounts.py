import pytest
from sqlalchemy import func, select
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import User, db
from conftest import csrf, post, register


def registration_data(**changes):
    return {
        "email": "creator@example.test",
        "display_name": "Creator",
        "password": "a strong testing password",
        "confirm_password": "a strong testing password",
        **changes,
    }


def test_account_page_and_logout_are_private(app):
    guest = app.test_client()
    assert guest.get("/auth/account").status_code == 303
    member = register(app, "Creator")
    account = member.get("/auth/account")
    assert account.status_code == 200
    assert b"creator@example.test" in account.data
    assert account.headers["Cache-Control"] == "private, no-store"
    assert b"My account" in member.get("/").data
    assert member.get("/auth/logout").status_code == 405
    assert member.post("/auth/logout").status_code == 400
    assert member.get("/auth/account").status_code == 200
    assert post(member, "/auth/logout").status_code == 303
    assert member.get("/auth/account").status_code == 303


@pytest.mark.parametrize("changes, message", [
    ({"confirm_password": "another password"}, b"Passwords must match"),
    ({"confirm_password": ""}, b"Passwords must match"),
    ({"password": "short", "confirm_password": "short"}, b"12 and 128"),
    ({"display_name": "A"}, b"at least 2 characters"),
])
def test_registration_errors_preserve_text_and_hide_passwords(app, changes, message):
    guest = app.test_client()
    response = post(guest, "/auth/register", registration_data(**changes),
                    csrf_token=csrf(guest, "/auth/register"))
    assert response.status_code == 400
    assert message in response.data
    assert b'value="creator@example.test"' in response.data
    assert b'value="a strong testing password"' not in response.data
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 0


def test_registration_keeps_server_role_and_normalizes_email(app):
    guest = app.test_client()
    response = post(guest, "/auth/register", registration_data(
        email=" Creator@Example.TEST ", display_name=" Creator ", role="admin",
    ), csrf_token=csrf(guest, "/auth/register"))
    assert response.status_code == 303
    with app.app_context():
        user = db.session.scalar(select(User))
        assert user.email == "creator@example.test"
        assert user.display_name == "Creator"
        assert user.role == "member"
        assert user.password_hash != "a strong testing password"


def test_older_passwords_and_email_casing_can_still_sign_in(app):
    with app.app_context():
        db.session.add(User(email="OLDER@example.test", display_name="Older account",
                            password_hash=generate_password_hash("oldpass8")))
        db.session.commit()
    guest = app.test_client()
    response = post(guest, "/auth/login", {
        "email": "older@example.test", "password": "oldpass8",
    }, csrf_token=csrf(guest, "/auth/login"))
    assert response.status_code == 303
    assert b"Older account" in guest.get("/auth/account").data


def test_duplicate_registration_race_rolls_back_and_preserves_input(app, monkeypatch):
    from app import auth

    register(app, "Creator")
    lookup = auth.find_user
    calls = 0

    def concurrent_lookup(email):
        nonlocal calls
        calls += 1
        # Simulate another registration committing after our first lookup.
        return None if calls == 1 else lookup(email)

    monkeypatch.setattr(auth, "find_user", concurrent_lookup)
    guest = app.test_client()
    response = post(guest, "/auth/register", registration_data(),
                    csrf_token=csrf(guest, "/auth/register"))
    assert response.status_code == 400
    assert b"already uses this email" in response.data
    assert b'value="Creator"' in response.data
    assert guest.get("/auth/account").status_code == 303
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1


def test_registration_limits_are_separate_from_login_limits(app):
    app.config["TEST_RATE_LIMIT"] = True
    guest = app.test_client()
    token = csrf(guest, "/auth/register")
    for _ in range(5):
        assert post(guest, "/auth/register", registration_data(confirm_password="wrong"),
                    csrf_token=token).status_code == 400
    assert post(guest, "/auth/register", registration_data(), csrf_token=token).status_code == 429
    assert guest.get("/auth/register").status_code == 200
    assert post(guest, "/auth/login", {"email": "unknown@example.test", "password": "incorrect"},
                csrf_token=token).status_code == 400


@pytest.mark.parametrize("storage_uri", ["memory://", "memory://limits", "", None])
def test_production_requires_shared_credential_limits(tmp_path, storage_uri):
    with pytest.raises(RuntimeError, match="shared RATELIMIT_STORAGE_URI"):
        create_app({
            "APP_ENV": "production",
            "SECRET_KEY": "a-long-production-test-secret-with-at-least-32-characters",
            "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://example@127.0.0.1/afterpause_test",
            "RATELIMIT_STORAGE_URI": storage_uri,
            "UPLOAD_DIR": tmp_path,
        })
