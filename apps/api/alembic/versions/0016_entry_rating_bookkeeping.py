"""rating bookkeeping on duel entries and duels.ratings_voided_at

Stores the exact overall/category delta and outcome applied at resolution,
so an admin hiding an entry later can reverse it without recomputing elo
from ratings that may have moved since.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "duels",
        sa.Column("ratings_voided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("duel_entries", sa.Column("rating_delta", sa.Integer(), nullable=True))
    op.add_column(
        "duel_entries", sa.Column("category_rating_delta", sa.Integer(), nullable=True)
    )
    op.add_column("duel_entries", sa.Column("outcome_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("duel_entries", "outcome_score")
    op.drop_column("duel_entries", "category_rating_delta")
    op.drop_column("duel_entries", "rating_delta")
    op.drop_column("duels", "ratings_voided_at")
