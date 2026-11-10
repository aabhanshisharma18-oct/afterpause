import os
from pathlib import Path
import secrets

from flask import Flask, g, render_template, request, session
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError

from .models import CATEGORIES, PAUSE_REASONS, PERMISSIONS, ROOMS, STATES, User, db

csrf = CSRFProtect()
migrate = Migrate()


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    mode = os.getenv("APP_ENV", "development")
    database = os.getenv("DEMO_DATABASE_URL" if mode == "demo" else "DATABASE_URL")
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY"), APP_ENV=mode,
        SQLALCHEMY_DATABASE_URI=database or ("sqlite:///demo.sqlite3" if mode == "demo" else "sqlite:///museum.sqlite3"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_DIR=os.getenv("DEMO_UPLOAD_DIR" if mode == "demo" else "UPLOAD_DIR") or
        Path(app.instance_path) / ("demo-uploads" if mode == "demo" else "uploads"),
        MAX_CONTENT_LENGTH=13 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=mode == "production",
        PERMANENT_SESSION_LIFETIME=86400,
    )
    if config:
        app.config.update(config)
    mode = app.config["APP_ENV"]
    if mode == "production" and (
        len(app.config["SECRET_KEY"] or "") < 32 or not app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql+")
    ):
        raise RuntimeError("Production requires a strong SECRET_KEY and a MySQL DATABASE_URL.")
    app.config["SECRET_KEY"] = app.config["SECRET_KEY"] or secrets.token_hex(32)
    app.config["UPLOAD_DIR"] = Path(app.config["UPLOAD_DIR"]).resolve()
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("mysql"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True, "pool_recycle": 1800, "isolation_level": "READ COMMITTED",
        }
    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            @event.listens_for(db.engine, "connect")
            def sqlite_foreign_keys(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
    csrf.init_app(app)
    migrate.init_app(app, db)

    from .admin import bp as admin
    from .auth import bp as auth
    from .continuations import bp as continuations
    from .exhibits import bp as exhibits
    from .museum import bp as museum
    from .cli import register_commands

    for bp in (museum, auth, exhibits, continuations, admin):
        app.register_blueprint(bp)
    register_commands(app)

    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        g.user = db.session.get(User, user_id) if user_id is not None else None

    app.jinja_env.filters["room_names"] = lambda rooms: {key: room[0] for key, room in rooms.items()}

    @app.context_processor
    def shared():
        return dict(rooms=ROOMS, categories=CATEGORIES, states=STATES, permissions=PERMISSIONS,
                    pause_reasons=PAUSE_REASONS, action_token=lambda: secrets.token_hex(16))

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' blob:; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "private, no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(CSRFError)
    def expired(_):
        return render_template("error.html", code=400, title="This form expired",
                               detail="Reload the form and try again."), 400

    @app.errorhandler(IntegrityError)
    def conflict(error):
        db.session.rollback()
        app.logger.info("Write conflicted with an existing record: %s", type(error.orig).__name__)
        return render_template("error.html", code=409, title="This action was already recorded",
                               detail="Reload the page to see the current state."), 409

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def http_error(error):
        titles = {400: "Check this submission", 403: "Access denied", 404: "This page is unavailable",
                  409: "This action is no longer available", 413: "The upload is too large",
                  429: "Too many attempts"}
        return render_template("error.html", code=error.code, title=titles[error.code],
                               detail=error.description), error.code

    return app
