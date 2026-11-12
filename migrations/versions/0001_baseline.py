"""Baseline: the schema the app created with create_all before migrations existed

Revision ID: 0001
Revises:
Create Date: 2026-11-12

A database made by an earlier version of Scissor already has these tables. Mark it as
being at this revision with `alembic stamp 0001`, then run `alembic upgrade head`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "urls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("long_url", sa.String(), nullable=False),
        sa.Column("short_url", sa.String(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_url"),
    )
    op.create_table(
        "clicks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("url_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["url_id"], ["urls.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clicks_id", "clicks", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clicks_id", table_name="clicks")
    op.drop_table("clicks")
    op.drop_table("urls")
