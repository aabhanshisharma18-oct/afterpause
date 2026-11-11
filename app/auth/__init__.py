import re
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from limits import parse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..models import User, db
from ..services import FormError, signed_in, value

bp = Blueprint("auth", __name__, url_prefix="/auth")
EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}")
DUMMY_HASH = generate_password_hash("afterpause-rate-limit-placeholder")
LOGIN_LIMITS = (parse("5 per minute"), parse("30 per hour"))
REGISTRATION_LIMITS = (parse("5 per hour"),)


def throttle():
    if current_app.testing and not current_app.config.get("TEST_RATE_LIMIT"):
        return
    limiter = current_app.extensions["auth_limiter"]
    rules = REGISTRATION_LIMITS if request.endpoint == "auth.register" else LOGIN_LIMITS
    for rule in rules:
        if not limiter.hit(rule, "afterpause-auth", request.endpoint, request.remote_addr or "unknown"):
            abort(429, "Too many attempts from your connection. Wait before trying again.")


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


def find_user(email):
    # Also accept the email casing of records created before normalization.
    return db.session.scalar(select(User).where(func.lower(User.email) == email))


def authenticate(register):
    mode = "register" if register else "login"
    if g.user:
        return redirect(next_page())
    if request.method == "POST":
        throttle()
        try:
            email = email_value()
            password = request.form.get("password", "")
            minimum = 12 if register else 1
            if not (minimum <= len(password) <= 128):
                raise FormError("password", f"Use a password between {minimum} and 128 characters.")
            user = find_user(email)
            if register:
                name = value("display_name", "Display name", 70)
                if len(name) < 2:
                    raise FormError("display_name", "Use at least 2 characters for your display name.")
                if request.form.get("confirm_password") != password:
                    raise FormError("confirm_password", "Passwords must match.")
                if user:
                    raise FormError("email", "An account already uses this email address.")
                user = User(email=email, display_name=name, password_hash=generate_password_hash(password))
                db.session.add(user)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    if find_user(email) is None:
                        raise
                    raise FormError("email", "An account already uses this email address.")
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
@signed_in
def logout():
    session.clear()
    flash("You’re signed out.", "success")
    return redirect(url_for("museum.entrance"), code=303)


@bp.get("/account")
@signed_in
def account():
    return render_template("account.html")


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
