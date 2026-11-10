from collections import deque
import re
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from ..models import User, db
from ..services import FormError, signed_in, value

bp = Blueprint("auth", __name__, url_prefix="/auth")
EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}")
DUMMY_HASH = generate_password_hash("afterpause-rate-limit-placeholder")


def throttle():
    # Limit credential checks per source. Each app process keeps a bounded window.
    if current_app.testing and not current_app.config.get("TEST_RATE_LIMIT"):
        return
    attempts, lock = current_app.extensions.setdefault("login_attempts", ({}, Lock()))
    ip, now = request.remote_addr or "unknown", monotonic()
    with lock:
        for key in list(attempts):
            if attempts[key][-1] <= now - 60:
                del attempts[key]
        if ip not in attempts and len(attempts) >= 2048:
            abort(429, "Wait a minute and try again.")
        times = attempts.setdefault(ip, deque())
        while times and times[0] <= now - 60:
            times.popleft()
        if len(times) >= 10:
            abort(429, "Wait a minute and try again.")
        times.append(now)


def next_page():
    target = request.args.get("next", "")
    # Resolve a local route only; browsers normalize backslashes and controls.
    if re.fullmatch(r"/[A-Za-z0-9/?%=&_.+~-]*", target) and not target.startswith("//"):
        parsed = urlsplit(target)
        if not parsed.netloc and not parsed.path.lower().startswith(("/%2f", "/%5c")):
            return target
    return url_for("exhibits.dashboard")


def email_value():
    email = value("email", "Email address", 254).lower()
    if not EMAIL.fullmatch(email):
        raise FormError("email", "Enter a valid email address.")
    return email


def authenticate(register):
    mode = "register" if register else "login"
    if g.user:
        return redirect(next_page())
    if request.method == "POST":
        throttle()
        try:
            email = email_value()
            password = request.form.get("password", "")
            if not (8 <= len(password) <= 128):
                raise FormError("password", "Use a password between 8 and 128 characters.")
            user = db.session.scalar(select(User).where(User.email == email))
            if register:
                name = value("display_name", "Display name", 70)
                if user:
                    raise FormError("email", "An account already uses this email address.")
                user = User(email=email, display_name=name, password_hash=generate_password_hash(password))
                db.session.add(user)
                db.session.commit()
            elif not check_password_hash(user.password_hash if user else DUMMY_HASH, password) or not user:
                raise FormError("password", "The email address or password is incorrect.")
        except FormError as error:
            return render_template("auth.html", mode=mode, error=error), 400
        session.clear()
        session["user_id"] = user.id
        session.permanent = True
        flash("You’re signed in.", "success")
        return redirect(next_page(), code=303)
    return render_template("auth.html", mode=mode)


@bp.route("/register", methods=("GET", "POST"))
def register():
    return authenticate(True)


@bp.route("/login", methods=("GET", "POST"))
def login():
    return authenticate(False)


@bp.post("/logout")
def logout():
    session.clear()
    flash("You’re signed out.", "success")
    return redirect(url_for("museum.entrance"), code=303)


@bp.route("/profile", methods=("GET", "POST"))
@signed_in
def profile():
    if request.method == "POST":
        try:
            g.user.display_name = value("display_name", "Display name", 70)
            db.session.commit()
        except FormError as error:
            return render_template("profile.html", error=error), 400
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"), code=303)
    return render_template("profile.html")
