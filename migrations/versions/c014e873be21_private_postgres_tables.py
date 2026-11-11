"""Protect application tables from Supabase Data API access.

Flask authenticates through its server database connection. No browser role
needs direct table access. PostgreSQL table owners bypass RLS as intended.
"""
from alembic import op

revision = "c014e873be21"
down_revision = "964e4e6f5ae7"
branch_labels = None
depends_on = None

TABLES = (
    "rooms", "tags", "users", "exhibits", "form_actions", "bookmarks",
    "exhibit_tags", "reports", "requests", "continuations",
    "moderation_decisions", "updates", "media", "timeline_events",
)


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade():
    # Preserve protection on rollback; drop tables only through schema migrations.
    pass
