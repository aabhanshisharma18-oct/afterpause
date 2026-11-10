from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .models import ROOMS, Room, User, db


def room_seed():
    for slug, (name, description) in ROOMS.items():
        if not db.session.get(Room, slug):
            db.session.add(Room(slug=slug, name=name, description=description))
    db.session.commit()


@click.command("make-admin")
@click.argument("email")
@with_appcontext
def make_admin(email):
    """Grant the admin role to an existing account."""
    user = db.session.scalar(select(User).where(User.email == email.lower()))
    if not user:
        raise click.ClickException("Create this account before granting administrator access.")
    user.role = "admin"
    db.session.commit()
    click.echo("Administrator role granted.")


@click.command("seed-demo")
@click.option("--password", envvar="DEMO_ACCOUNT_PASSWORD", prompt=True, hide_input=True,
              confirmation_prompt=True, help="Set a password for the three local demo accounts.")
@with_appcontext
def seed_demo(password):
    """Load the labelled exhibits into a separate demo database."""
    if current_app.config["APP_ENV"] != "demo":
        raise click.ClickException("Use APP_ENV=demo with a separate demo database.")
    if not 8 <= len(password) <= 128:
        raise click.ClickException("Use a demo password between 8 and 128 characters.")
    from .demo import populate
    room_seed()
    populate(password)
    click.echo("Demo ready. Sign in as creator@example.test, contributor@example.test or admin@example.test.")


def register_commands(app):
    app.cli.add_command(make_admin)
    app.cli.add_command(seed_demo)
