"""Index clicks.url_id so per-link analytics don't scan every click

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_clicks_url_id", "clicks", ["url_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clicks_url_id", table_name="clicks")
