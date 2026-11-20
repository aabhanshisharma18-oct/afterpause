"""Bundled museum samples and private, per-visitor demonstration workspaces."""
from datetime import date
from secrets import token_hex
from uuid import uuid4

from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .models import Exhibit, GuestEntry, Media, Proposal, Room, ROOMS, User, db, utcnow
from .services import add_event

SAMPLES = (
    ("Campus Guide", "software", "unfinished-interfaces", "campus-guide-reference.png", "scope",
     "A campus map that makes finding your next class feel effortless.",
     "The desktop map and route preview work. Mobile navigation is still a sketch.",
     "Build a mobile route panel with keyboard-friendly controls."),
    ("Reading Room", "software", "useful-little-tools", "reading-room.png", "time",
     "A quiet home for your books, reading notes, and unfinished reading lists.",
     "A bookshelf prototype with reading-progress cards and a revised search concept.",
     "Add an accessible empty state for book search."),
    ("One More Level", "games", "playable-someday", "one-more-level.png", "burnout",
     "A tiny platform game set in a forgotten mountain garden.",
     "One playable level, a character sprite, and a rough plan for five more worlds.",
     "Finish one short level using the existing movement rules."),
    ("Seedling AI", "ai", "first-experiments", "creative-workspace.png", "alternative",
     "Turn a messy list of ideas into a small, achievable learning plan.",
     "A Python prototype and a handwritten evaluation checklist. No model is deployed.",
     "Create a small evaluation dataset before adding more features."),
    ("BorrowBox", "startups", "useful-little-tools", "creative-workspace.png", "funding",
     "Help students borrow equipment instead of buying it for a single assignment.",
     "A catalogue concept, availability cards, and an early pickup workflow.",
     "Prototype one item reservation and return flow."),
    ("Desk Garden", "hardware", "first-experiments", "creative-workspace.png", "job",
     "A small desk plant monitor built with open hardware.",
     "A circuit sketch and sample readings; no physical prototype is supplied.",
     "Document the sensor wiring and test one moisture reading."),
)


def ensure_rooms():
    for slug, (name, description) in ROOMS.items():
        if not db.session.get(Room, slug):
            db.session.add(Room(slug=slug, name=name, description=description))


def specimen(owner, index, prefix, sandbox_id=None, *, draft=False):
    title, category, room, asset, reason, intention, existing, next_step = SAMPLES[index]
    item = Exhibit(
        slug=f"{prefix}-{index}", owner=owner, sandbox_id=sandbox_id, title=title,
        category=category, room_id=room, intention=intention,
        story=f"{intention} It began as a weekend experiment, grew beyond the first plan, and was eventually put on pause.",
        current_work=existing, next_step=next_step, skills="Python, JavaScript, CSS",
        pause_reason=reason, pause_note="The original scope needed more time than one person could give it.",
        born_on=date(2024, index + 1, 12), paused_on=date(2024, index + 4, 20),
        lessons="A small working slice teaches more than a long list of planned features.",
        differently="Start with one user task, validate it early, and document a clear handoff.",
        attribution="Fictional classroom exhibit. Images are illustrative concept assets.",
        permissions="ask", share_confirmed=True, is_demo=True, curator_pick=index in (0, 2),
        publication_state="draft" if draft else "published", published_at=None if draft else utcnow(),
    )
    image = Media(exhibit=item, storage_key=f"{uuid4().hex}.webp", bundled_asset=asset,
                  alt_text=f"Illustrative concept preview for {title}", size=0)
    db.session.add_all([item, image])
    if not draft:
        add_event(item, owner, "original", "The original idea", body=existing, next_step=next_step, media=image)
    return item


def seed_gallery():
    """Idempotent startup fixture loader; never modifies user work or passwords."""
    ensure_rooms()
    owner = db.session.scalar(select(User).where(User.role == "collection").order_by(User.id).limit(1))
    if not owner:
        owner = User(email=f"collection-{uuid4().hex}@afterpause.invalid", display_name="Museum Collection", role="collection",
                     password_hash=generate_password_hash(token_hex(32)))
        db.session.add(owner)
    for index in range(len(SAMPLES)):
        slug = f"collection-{index}"
        if not db.session.scalar(select(Exhibit.id).where(Exhibit.slug == slug)):
            specimen(owner, index, "collection")
    db.session.commit()


def create_workspace():
    ensure_rooms()
    sandbox = uuid4().hex
    people = {}
    for role, name in (("creator", "Demo Creator"), ("contributor", "Demo Contributor")):
        people[role] = User(email=f"demo-{sandbox}-{role}@afterpause.invalid", display_name=name,
                            password_hash=generate_password_hash(token_hex(32)), sandbox_id=sandbox)
        db.session.add(people[role])
    db.session.flush()
    creator, contributor = people["creator"], people["contributor"]
    own = specimen(creator, 0, sandbox, sandbox)
    reading = specimen(contributor, 1, sandbox, sandbox)
    game = specimen(contributor, 2, sandbox, sandbox)
    specimen(contributor, 3, sandbox, sandbox)
    specimen(contributor, 5, sandbox, sandbox)
    specimen(creator, 4, sandbox, sandbox, draft=True)
    db.session.flush()
    pending = Proposal(exhibit=own, applicant=contributor,
                       proposal="I would like to make the campus map usable on a phone.",
                       milestone="Build the mobile route panel", materials="The supplied map mockup; ask before reuse")
    reading_request = Proposal(exhibit=reading, applicant=creator,
                               proposal="Add book search and test keyboard navigation.",
                               milestone="A working search concept",
                               materials="The supplied bookshelf mockup")
    db.session.add_all([pending, reading_request])
    db.session.add(GuestEntry(exhibit_id=game.id, author_id=creator.id,
                             body="This world deserves one more level. The smaller first milestone feels achievable."))
    db.session.commit()
    return sandbox, creator
