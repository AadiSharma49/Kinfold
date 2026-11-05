"""duel expiry: expired status, judging_started_at, expired_at

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "duels",
        sa.Column("judging_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "duels",
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Existing judging duels have no recorded start time. Give them a full
    # expiry window from the deploy instead of expiring them immediately
    # because their created_at happens to be old.
    op.execute(
        "UPDATE duels SET judging_started_at = now() "
        "WHERE status = 'judging' AND judging_started_at IS NULL"
    )

    op.drop_constraint("ck_duels_status", "duels", type_="check")
    op.create_check_constraint(
        "ck_duels_status",
        "duels",
        "status IN ('open', 'judging', 'resolved', 'expired')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_duels_status", "duels", type_="check")
    op.create_check_constraint(
        "ck_duels_status",
        "duels",
        "status IN ('open', 'judging', 'resolved')",
    )
    op.drop_column("duels", "expired_at")
    op.drop_column("duels", "judging_started_at")
