from unittest.mock import Mock, patch

import pytest
from werkzeug.exceptions import ServiceUnavailable

from app import storage
from app.models import Exhibit, db
from conftest import draft, post, register, screenshot


def cloud(app):
    app.config.update(MEDIA_STORAGE="supabase", SUPABASE_URL="https://example.supabase.co",
                      SUPABASE_SERVICE_KEY="server-secret", SUPABASE_BUCKET="afterpause-media")


def test_private_media_is_authorised_before_storage_read(app):
    owner = register(app, "Creator")
    item_id, edit = draft(owner)
    cloud(app)
    with patch("app.storage.remote", return_value=b"image-bytes") as remote:
        assert post(owner, f"{edit}?step=2", dict(current_work="Map", image=screenshot(),
                                                alt_text="Campus map")).status_code == 303
        with app.app_context():
            key = db.session.get(Exhibit, item_id).media[0].storage_key
        remote.reset_mock()
        assert app.test_client().get(f"/media/{key}").status_code == 404
        remote.assert_not_called()
        response = owner.get(f"/media/{key}")
        assert response.status_code == 200
        assert response.data == b"image-bytes"
        assert response.headers["Cache-Control"] == "private, no-store"
        assert remote.call_args.args[1].startswith("object/authenticated/afterpause-media/")


def test_cloud_upload_is_removed_when_database_commit_fails(app):
    cloud(app)
    key = "a" * 32 + ".webp"
    from app.services import commit
    media = Mock(storage_key=key)
    with app.app_context(), patch("app.storage.remote") as remote:
        with patch.object(db.session, "commit", side_effect=RuntimeError("database failed")):
            with pytest.raises(RuntimeError, match="database failed"):
                commit((media, b"webp"))
        assert [call.args[0] for call in remote.call_args_list] == ["POST", "DELETE"]


def test_remote_failure_returns_no_credentials(app):
    from urllib.error import URLError
    cloud(app)
    with app.app_context(), patch("app.storage.build_opener") as opener:
        opener.return_value.open.side_effect = URLError("network failed")
        with pytest.raises(ServiceUnavailable) as caught:
            storage.read("b" * 32 + ".webp")
        assert "server-secret" not in str(caught.value)


def test_local_collision_keeps_existing_file(app, tmp_path):
    app.config["UPLOAD_DIR"] = tmp_path
    key = "c" * 32 + ".webp"
    (tmp_path / key).write_bytes(b"existing")
    with app.app_context(), pytest.raises(FileExistsError):
        storage.store(key, b"replacement")
    assert (tmp_path / key).read_bytes() == b"existing"


def test_postgres_application_tables_have_rls(app):
    from sqlalchemy import text
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("PostgreSQL only")
        assert db.session.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'users'::regclass"))
