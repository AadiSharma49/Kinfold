"""duel_entries AI-suspicion signals for self-declared human entries:
human_large_paste_detected, human_suspected_ai, human_suspected_ai_reasons

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "duel_entries",
        sa.Column(
            "human_large_paste_detected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "duel_entries",
        sa.Column(
            "human_suspected_ai",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "duel_entries",
        sa.Column("human_suspected_ai_reasons", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("duel_entries", "human_suspected_ai_reasons")
    op.drop_column("duel_entries", "human_suspected_ai")
    op.drop_column("duel_entries", "human_large_paste_detected")
