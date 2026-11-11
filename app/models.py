"""Shared data model for the three Afterpause modules."""

from datetime import datetime, timezone
from hashlib import sha256
import json

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

db = SQLAlchemy(metadata=MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}))

ROOMS = {
    "unfinished-interfaces": ("Unfinished Interfaces", "Designs waiting for the next interaction."),
    "playable-someday": ("Playable Someday", "Games and worlds with more to explore."),
    "useful-little-tools": ("Useful Little Tools", "Small projects that make everyday work easier."),
    "first-experiments": ("First Experiments", "Early ideas with room to grow."),
}
CATEGORIES = {"design": "Design", "software": "Software", "games": "Games", "other": "Other"}
STATES = {"open": "Open", "in-progress": "In progress", "milestone": "Milestone reached"}
PERMISSIONS = {"ask": "Ask the creator before reuse", "mit": "MIT", "cc-by": "CC BY 4.0", "cc0": "CC0 1.0"}
PAUSE_REASONS = {"time": "Time constraints", "learning": "Learning curve",
                 "priorities": "Changed priorities", "other": "Other"}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Record:
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class User(Record, db.Model):
    __tablename__ = "users"
    email = db.Column(db.String(254), nullable=False, unique=True)
    display_name = db.Column(db.String(70), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(12), nullable=False, default="member")


class Room(db.Model):
    __tablename__ = "rooms"
    slug = db.Column(db.String(40), primary_key=True)
    name = db.Column(db.String(70), nullable=False)
    description = db.Column(db.String(150), nullable=False)


exhibit_tags = db.Table(
    "exhibit_tags",
    db.Column("exhibit_id", db.ForeignKey("exhibits.id"), primary_key=True),
    db.Column("tag_id", db.ForeignKey("tags.id"), primary_key=True),
)


class Tag(Record, db.Model):
    __tablename__ = "tags"
    name = db.Column(db.String(30), nullable=False, unique=True)


class Exhibit(Record, db.Model):
    __tablename__ = "exhibits"
    slug = db.Column(db.String(125), nullable=False, unique=True)
    owner_id = db.Column(db.ForeignKey("users.id"), nullable=False, index=True)
    room_id = db.Column(db.ForeignKey("rooms.slug"), nullable=True, index=True)
    title = db.Column(db.String(100), default="", nullable=False)
    intention = db.Column(db.String(180), default="", nullable=False)
    story = db.Column(db.Text, default="", nullable=False)
    current_work = db.Column(db.Text, default="", nullable=False)
    next_step = db.Column(db.Text, default="", nullable=False)
    category = db.Column(db.String(16), default="", nullable=False)
    skills = db.Column(db.String(160), default="", nullable=False)
    task_size = db.Column(db.String(40), default="", nullable=False)
    pause_reason = db.Column(db.String(16), default="", nullable=False)
    pause_note = db.Column(db.Text, default="", nullable=False)
    repository_url = db.Column(db.String(500), default="", nullable=False)
    demo_url = db.Column(db.String(500), default="", nullable=False)
    attribution = db.Column(db.String(240), default="", nullable=False)
    permissions = db.Column(db.String(16), default="", nullable=False)
    share_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    publication_state = db.Column(db.String(12), default="draft", nullable=False, index=True)
    review_state = db.Column(db.String(12), default="clear", nullable=False)
    moderation_hidden = db.Column(db.Boolean, default=False, nullable=False)
    continuation_state = db.Column(db.String(16), default="open", nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    owner = db.relationship(User)
    room = db.relationship(Room)
    tags = db.relationship(Tag, secondary=exhibit_tags, order_by=Tag.name)
    media = db.relationship("Media", order_by="Media.id", back_populates="exhibit")

    @property
    def is_public(self):
        return self.publication_state == "published" and not self.moderation_hidden

    @property
    def label(self):
        return self.title or "Untitled draft"


class Proposal(Record, db.Model):
    __tablename__ = "requests"
    exhibit_id = db.Column(db.ForeignKey("exhibits.id"), nullable=False, index=True)
    applicant_id = db.Column(db.ForeignKey("users.id"), nullable=False, index=True)
    proposal = db.Column(db.Text, nullable=False)
    milestone = db.Column(db.String(240), nullable=False)
    materials = db.Column(db.String(400), nullable=False)
    status = db.Column(db.String(12), default="pending", nullable=False)
    pending_slot = db.Column(db.Integer, nullable=True, default=1)
    decision_note = db.Column(db.String(400), default="", nullable=False)
    decided_at = db.Column(db.DateTime, nullable=True)
    exhibit = db.relationship(Exhibit)
    applicant = db.relationship(User)
    continuation = db.relationship("Continuation", uselist=False, back_populates="request")
    __table_args__ = (
        db.UniqueConstraint("exhibit_id", "applicant_id", "pending_slot", name="uq_request_pending"),
        db.CheckConstraint("(status = 'pending' AND pending_slot IS NOT NULL AND pending_slot = 1) OR "
                           "(status <> 'pending' AND pending_slot IS NULL)", name="request_pending_slot"),
    )

    @property
    def review_key(self):
        """Identify the exact proposal text rendered in a decision or edit form."""
        fields = json.dumps((self.proposal, self.milestone, self.materials))
        return sha256(fields.encode("utf-8")).hexdigest()


class Continuation(Record, db.Model):
    __tablename__ = "continuations"
    exhibit_id = db.Column(db.ForeignKey("exhibits.id"), nullable=False, index=True)
    request_id = db.Column(db.ForeignKey("requests.id"), nullable=False, unique=True)
    contributor_id = db.Column(db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(12), default="active", nullable=False)
    active_slot = db.Column(db.Integer, nullable=True, default=1)
    end_reason = db.Column(db.String(400), default="", nullable=False)
    exhibit = db.relationship(Exhibit)
    request = db.relationship(Proposal, back_populates="continuation")
    updates = db.relationship("Update", order_by="Update.id.desc()", back_populates="continuation")
    contributor = db.relationship(User)
    __table_args__ = (
        db.UniqueConstraint("exhibit_id", "active_slot", name="uq_continuation_active"),
        db.CheckConstraint("(status = 'active' AND active_slot IS NOT NULL AND active_slot = 1) OR "
                           "(status <> 'active' AND active_slot IS NULL)", name="continuation_active_slot"),
    )


class Update(Record, db.Model):
    __tablename__ = "updates"
    continuation_id = db.Column(db.ForeignKey("continuations.id"), nullable=False, index=True)
    author_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    next_step = db.Column(db.String(240), nullable=False)
    link = db.Column(db.String(500), default="", nullable=False)
    review_status = db.Column(db.String(12), default="pending", nullable=False)
    review_note = db.Column(db.String(400), default="", nullable=False)
    reviewed_by = db.Column(db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    continuation = db.relationship(Continuation, back_populates="updates")
    author = db.relationship(User, foreign_keys=[author_id])
    media = db.relationship("Media", uselist=False, back_populates="update")


class Media(Record, db.Model):
    __tablename__ = "media"
    exhibit_id = db.Column(db.ForeignKey("exhibits.id"), nullable=True, index=True)
    update_id = db.Column(db.ForeignKey("updates.id"), nullable=True, unique=True)
    storage_key = db.Column(db.String(37), nullable=False, unique=True)
    alt_text = db.Column(db.String(180), nullable=False)
    mime_type = db.Column(db.String(30), default="image/webp", nullable=False)
    size = db.Column(db.Integer, nullable=False)
    exhibit = db.relationship(Exhibit, back_populates="media")
    update = db.relationship(Update, back_populates="media")
    __table_args__ = (db.CheckConstraint("(exhibit_id IS NULL) <> (update_id IS NULL)",
                                         name="media_one_parent"),)


class TimelineEvent(Record, db.Model):
    __tablename__ = "timeline_events"
    exhibit_id = db.Column(db.ForeignKey("exhibits.id"), nullable=False, index=True)
    actor_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    actor_name = db.Column(db.String(70), nullable=False)
    event_type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, default="", nullable=False)
    next_step = db.Column(db.String(240), default="", nullable=False)
    media_id = db.Column(db.ForeignKey("media.id"), nullable=True)
    update_id = db.Column(db.ForeignKey("updates.id"), nullable=True, unique=True)
    exhibit = db.relationship(Exhibit)
    media = db.relationship(Media)
    update = db.relationship(Update)


class Report(Record, db.Model):
    __tablename__ = "reports"
    exhibit_id = db.Column(db.ForeignKey("exhibits.id"), nullable=False, index=True)
    reporter_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.String(600), nullable=False)
    status = db.Column(db.String(12), default="open", nullable=False, index=True)
    exhibit = db.relationship(Exhibit)
    reporter = db.relationship(User)


class ModerationDecision(Record, db.Model):
    __tablename__ = "moderation_decisions"
    exhibit_id = db.Column(db.ForeignKey("exhibits.id"), nullable=False)
    moderator_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    report_id = db.Column(db.ForeignKey("reports.id"), nullable=True)
    action = db.Column(db.String(12), nullable=False)
    note = db.Column(db.String(600), nullable=False)
    exhibit = db.relationship(Exhibit)
    moderator = db.relationship(User)


class Bookmark(db.Model):
    __tablename__ = "bookmarks"
    user_id = db.Column(db.ForeignKey("users.id"), primary_key=True)
    exhibit_id = db.Column(db.ForeignKey("exhibits.id"), primary_key=True)


class Action(db.Model):
    __tablename__ = "form_actions"
    user_id = db.Column(db.ForeignKey("users.id"), primary_key=True)
    token = db.Column(db.String(32), primary_key=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
