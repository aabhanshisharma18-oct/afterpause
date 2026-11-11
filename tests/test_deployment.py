from unittest.mock import patch

import pytest
from flask import request
from sqlalchemy.exc import OperationalError

from app import create_app
from app.models import db


def test_health_and_readiness(app):
    client = app.test_client()
    assert client.get("/healthz").json == {"status": "ok"}
    assert client.get("/readyz").status_code == 200
    with patch("limits.storage.MemoryStorage.check", return_value=False):
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json == {"status": "unavailable"}


def test_database_failure_does_not_break_liveness(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
    with patch.object(db.session, "execute", side_effect=OperationalError("unavailable", {}, None)):
        assert client.get("/healthz").status_code == 200
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json == {"status": "unavailable"}


@pytest.mark.parametrize("hops, expected", [(0, "http:127.0.0.1"), (1, "https:203.0.113.10")])
def test_proxy_headers_are_opt_in(tmp_path, hops, expected):
    app = create_app({
        "APP_ENV": "test", "TESTING": True, "SECRET_KEY": "proxy-test",
        "SQLALCHEMY_DATABASE_URI": "sqlite://", "UPLOAD_DIR": tmp_path,
        "RATELIMIT_STORAGE_URI": "memory://", "PROXY_HOPS": hops,
    })

    @app.get("/proxy-test")
    def proxy_test():
        return f"{request.scheme}:{request.remote_addr}"

    response = app.test_client().get("/proxy-test", headers={
        "X-Forwarded-For": "203.0.113.10", "X-Forwarded-Proto": "https",
    })
    assert response.get_data(as_text=True) == expected
