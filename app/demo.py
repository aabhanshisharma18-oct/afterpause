"""Synthetic content for a repeatable, explicitly labelled classroom demo."""

import io
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageOps
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from .models import Continuation, Exhibit, Proposal, Report, Tag, Update, User, db, utcnow
from .services import add_event, attach_image, commit

# title, room, category, intention, existing work, next step, skills, preview
ITEMS = (
    ("Campus Guide", "unfinished-interfaces", "design",
     "Help students find the shortest walking route to their next class.",
     "A desktop map with location search and a route preview.",
     "Build and test the small-screen navigation.", "HTML, CSS, JavaScript", "campus-guide.png"),
    ("Reading Room", "unfinished-interfaces", "design",
     "Keep a quiet record of books in a personal library.",
     "A bookshelf and reading-progress layout.",
     "Test the proposed search with a larger library.", "CSS, interaction design", "reading-room.png"),
    ("One More Level", "playable-someday", "games",
     "Explore a forgotten garden on a mountain.",
     "A sample platforming screen and an early environment palette.",
     "Design the final level around one simple puzzle.", "Pixel art, level design", "one-more-level.png"),
    ("Pocket Forecast", "unfinished-interfaces", "design",
     "Show the day’s weather at a glance without a wall of numbers.",
     "A sketched forecast card and an illustrated weather vocabulary.",
     "Connect one city’s forecast to the layout.", "API integration, CSS", None),
    ("Lantern Relay", "playable-someday", "games",
     "Carry a fading lantern between a chain of small islands.",
     "A movement prototype and a paper map of five islands.",
     "Prototype a safe handoff between the first two islands.", "Game design, JavaScript", None),
    ("Recipe Drawer", "useful-little-tools", "software",
     "Preserve a household’s handwritten recipe cards.",
     "A sample archive with a small set of fictional recipe cards.",
     "Add search by ingredient and test the empty state.", "Python, SQL, CSS", None),
    ("Focus Trace", "useful-little-tools", "software",
     "Make keyboard tab order easier to inspect.",
     "A checklist and example pages with both good and broken tab order.",
     "Write setup instructions and a first keyboard walkthrough.", "Accessibility, documentation", None),
    ("Studio Index", "useful-little-tools", "software",
     "Find the latest version of a small creative brief.",
     "A draft folder convention and sample project list.",
     "Add a revision date and sorting rule.", "Python, SQL", "creative-workspace.png"),
    ("Pattern Press", "first-experiments", "software",
     "Turn simple geometric rules into printable patterns.",
     "Two repeat rules and an early canvas sketch.",
     "Export a repeat tile at a printable resolution.", "Canvas, JavaScript", None),
    ("Sidewalk Sounds", "first-experiments", "other",
     "Map short notes about how a walk feels at different times.",
     "An early annotated route and a list of sounds to observe.",
     "Sketch one accessible transcript view.", "Writing, interaction design", None),
)


def preview_image(filename, label, index, *, revised=False):
    if filename:
        asset = Path(current_app.static_folder) / "images" / filename
        with Image.open(asset) as source:
            image = ImageOps.fit(source.convert("RGB"), (1100, 730))
    else:
        palettes = (("#e8dfd1", "#305b53", "#b78c69"), ("#e4dce9", "#51445f", "#9c7fa1"),
                    ("#eadfcd", "#715542", "#bf9472"))
        background, dark, accent = palettes[index % len(palettes)]
        image = Image.new("RGB", (1100, 730), background)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((110, 95, 990, 640), radius=23, fill="#fffaf2", outline=dark, width=3)
        draw.rectangle((112, 150, 988, 154), fill=dark)
        draw.text((152, 114), label.upper(), fill=dark, font_size=23)
        draw.rounded_rectangle((151, 188, 660, 584), radius=12, fill=background)
        for n in range(7):
            x = 210 + n * 57
            h = 50 + ((n * 59 + index * 19) % 230)
            draw.rounded_rectangle((x, 521 - h, x + 35, 521), radius=7, fill=accent if n % 2 else dark)
        for n in range(3):
            y = 215 + 105 * n
            draw.rounded_rectangle((700, y, 936, y + 74), radius=10, fill=background)
            draw.line((720, y + 25, 884 - n * 14, y + 25), fill=dark, width=4)
    if revised:
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((75, 54, 1025, 135), radius=17, fill="#fcf9ee", outline="#145a52", width=4)
        draw.text((117, 80), "Search books by title or author", fill="#145a52", font_size=26)
    output = io.BytesIO()
    image.save(output, format="WEBP", quality=84)
    alt = "Reading Room mockup with an added book search field" if revised else f"Illustrative preview for {label}"
    return output.getvalue(), alt


def populate(password):
    people = {}
    for key, name in (("creator", "Museum Studio"), ("contributor", "Demo Contributor"), ("admin", "Demo Curator")):
        email = f"{key}@example.test"
        user = db.session.scalar(select(User).where(User.email == email))
        if not user:
            user = User(email=email, display_name=name, role="admin" if key == "admin" else "member")
            db.session.add(user)
        user.password_hash = generate_password_hash(password)
        people[key] = user
    db.session.commit()
    creator, contributor = people["creator"], people["contributor"]

    for index, (title, room, category, intention, existing, next_step, skills, image) in enumerate(ITEMS):
        slug = "demo-" + title.lower().replace(" ", "-")
        if db.session.scalar(select(Exhibit.id).where(Exhibit.slug == slug)):
            continue
        tag_name = {"design": "prototype", "software": "documentation", "games": "playtest", "other": "sketch"}[category]
        tag = db.session.scalar(select(Tag).where(Tag.name == tag_name)) or Tag(name=tag_name)
        exhibit = Exhibit(slug=slug, title=title, owner=creator, room_id=room, category=category,
                          intention=intention, story=f"{intention} {existing} This exhibit is fictional and is included for the classroom demonstration.",
                          current_work=existing, next_step=next_step, skills=skills, tags=[tag],
                          attribution="Fictional exhibit by Museum Studio. Preview is a demonstration asset.",
                          permissions="ask", share_confirmed=True, publication_state="published",
                          is_demo=True, published_at=utcnow())
        db.session.add(exhibit)
        # One example has no cover to demonstrate the empty image state.
        media = attach_image(preview_image(image, title, index), exhibit=exhibit) if index != 9 else None
        add_event(exhibit, creator, "original", "The original idea", body=intention,
                  next_step=next_step, media=media[0] if media else None)
        extra = None
        status = {1: "completed", 2: "active", 3: "pending", 4: "declined", 5: "withdrawn"}.get(index)
        if status:
            request_status = status if status in {"pending", "declined"} else "accepted"
            proposal = Proposal(exhibit=exhibit, applicant=contributor,
                                proposal=f"Start with one small change for {title}.", milestone=next_step,
                                materials="Use the supplied demo mockup with the creator’s permission.",
                                status=request_status, pending_slot=1 if request_status == "pending" else db.null(),
                                decision_note="Private example decision." if request_status == "declined" else "")
            db.session.add(proposal)
            if status in {"active", "completed", "withdrawn"}:
                continuation = Continuation(exhibit=exhibit, request=proposal, contributor=contributor,
                                            status=status, active_slot=1 if status == "active" else db.null())
                db.session.add(continuation)
                add_event(exhibit, contributor, "accepted", "A new chapter begins")
                if status == "active":
                    exhibit.continuation_state = "in-progress"
                elif status == "withdrawn":
                    add_event(exhibit, contributor, "withdrawn", "The contributor stepped back")
                else:
                    exhibit.continuation_state = "milestone"
                    update = Update(continuation=continuation, author=contributor, title="A first book search",
                                    body="The revised concept shows how search could fit above the bookshelf.",
                                    next_step="Test the empty state.", review_status="approved",
                                    reviewed_by=creator.id, reviewed_at=utcnow())
                    db.session.add(update)
                    extra = attach_image(preview_image(image, title, index, revised=True), update=update)
                    add_event(exhibit, contributor, "update", update.title, body=update.body,
                              next_step=update.next_step, media=extra[0], update=update)
                    add_event(exhibit, contributor, "completed", "Milestone reached")
        if index == 6:
            exhibit.review_state = "flagged"
            db.session.add(Report(exhibit=exhibit, reporter=contributor,
                                  reason="Demo report: verify that the preview credit is clear."))
        commit(media, extra)
    if not db.session.scalar(select(Exhibit.id).where(Exhibit.slug == "demo-private-draft")):
        db.session.add(Exhibit(slug="demo-private-draft", title="Private demo draft", owner=creator, is_demo=True))
        db.session.commit()
