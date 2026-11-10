"""create users and notes

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # List query: WHERE user_id = ? ORDER BY created_at DESC, id DESC
    # (id = deterministic tie-breaker; also covers plain user_id lookups).
    op.create_index(
        "ix_notes_user_id_created_at",
        "notes",
        ["user_id", sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
    )
    # Tag filter: tags @> ARRAY[?]
    op.create_index("ix_notes_tags", "notes", ["tags"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_notes_tags", table_name="notes")
    op.drop_index("ix_notes_user_id_created_at", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
