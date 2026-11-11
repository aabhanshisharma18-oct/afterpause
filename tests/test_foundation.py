import pytest

from afterpause import create_app as original_entry_point
from app import create_app


def test_original_entry_point_uses_the_integrated_app():
    assert original_entry_point is create_app


@pytest.mark.parametrize("secret", [None, "", "replace_with_a_random_secret"])
def test_startup_rejects_missing_or_placeholder_session_secrets(tmp_path, secret):
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({
            "APP_ENV": "development",
            "TESTING": False,
            "SECRET_KEY": secret,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "UPLOAD_DIR": tmp_path,
        })


def test_session_lifetime_and_secure_production_configuration(tmp_path):
    app = create_app({
        "APP_ENV": "production",
        "RATELIMIT_STORAGE_URI": "redis://127.0.0.1:6379/0",
        "SECRET_KEY": "a-random-session-secret-with-at-least-32-characters",
        "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://example@127.0.0.1/afterpause_test",
        "UPLOAD_DIR": tmp_path,
    })
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.permanent_session_lifetime.total_seconds() == 12 * 60 * 60
    with app.app_context():
        from app.models import db
        db.engine.dispose()
