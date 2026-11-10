"""Add the four curated museum rooms."""

from alembic import op
import sqlalchemy as sa

revision = "964e4e6f5ae7"
down_revision = "8f2558adace8"
branch_labels = None
depends_on = None

ROOMS = (
    ("unfinished-interfaces", "Unfinished Interfaces", "Designs waiting for the next interaction."),
    ("playable-someday", "Playable Someday", "Games and worlds with more to explore."),
    ("useful-little-tools", "Useful Little Tools", "Small projects that make everyday work easier."),
    ("first-experiments", "First Experiments", "Early ideas with room to grow."),
)


def rooms_table():
    return sa.table("rooms", sa.column("slug", sa.String), sa.column("name", sa.String),
                    sa.column("description", sa.String))


def upgrade():
    op.bulk_insert(rooms_table(), [dict(slug=slug, name=name, description=description)
                                   for slug, name, description in ROOMS])


def downgrade():
    rooms = rooms_table()
    exhibits = sa.table("exhibits", sa.column("room_id", sa.String))
    keys = [slug for slug, _, _ in ROOMS]
    op.execute(exhibits.update().where(exhibits.c.room_id.in_(keys)).values(room_id=None))
    op.execute(rooms.delete().where(rooms.c.slug.in_(keys)))
