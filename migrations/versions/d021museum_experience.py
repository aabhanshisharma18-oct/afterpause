"""Demo workspaces, museum placards, guest books and flowers."""
from alembic import op
import sqlalchemy as sa
revision = "d021museum"
down_revision = "c014e873be21"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("sandbox_id", sa.String(32), nullable=True))
    op.create_index("ix_users_sandbox_id", "users", ["sandbox_id"])
    for column in (
        sa.Column("sandbox_id", sa.String(32), nullable=True),
        sa.Column("born_on", sa.Date(), nullable=True),
        sa.Column("paused_on", sa.Date(), nullable=True),
        sa.Column("lessons", sa.Text(), nullable=False, server_default=sa.text("('')")),
        sa.Column("differently", sa.Text(), nullable=False, server_default=sa.text("('')")),
        sa.Column("curator_pick", sa.Boolean(), nullable=False, server_default=sa.false()),
    ):
        op.add_column("exhibits", column)
    op.create_index("ix_exhibits_sandbox_id", "exhibits", ["sandbox_id"])
    op.add_column("media", sa.Column("bundled_asset", sa.String(100), nullable=True))
    op.create_table("flowers",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("exhibit_id", sa.Integer(), sa.ForeignKey("exhibits.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("guest_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("exhibit_id", sa.Integer(), sa.ForeignKey("exhibits.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.String(600), nullable=False))
    op.create_index("ix_guest_entries_exhibit_id", "guest_entries", ["exhibit_id"])
    if op.get_bind().dialect.name == "postgresql":
        for table in ("flowers", "guest_entries"):
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')


def downgrade():
    op.drop_table("guest_entries")
    op.drop_table("flowers")
    op.drop_column("media", "bundled_asset")
    op.drop_index("ix_exhibits_sandbox_id", table_name="exhibits")
    for name in ("curator_pick", "differently", "lessons", "paused_on", "born_on", "sandbox_id"):
        op.drop_column("exhibits", name)
    op.drop_index("ix_users_sandbox_id", table_name="users")
    op.drop_column("users", "sandbox_id")
