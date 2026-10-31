"""judging integrity: duel_entries.is_trap, votes.entrant_rated_useful

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-31

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "duel_entries",
        sa.Column("is_trap", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("votes", sa.Column("entrant_rated_useful", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("votes", "entrant_rated_useful")
    op.drop_column("duel_entries", "is_trap")
