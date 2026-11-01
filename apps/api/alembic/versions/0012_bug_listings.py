"""bugfix duel category ("bring a bug" listings): duels.created_by_agent_id
becomes nullable, new duels.created_by_human_owner_id, updated category
check constraint

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-01

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "duels",
        sa.Column("created_by_human_owner_id", sa.UUID(), sa.ForeignKey("owners.id"), nullable=True),
    )
    op.alter_column("duels", "created_by_agent_id", nullable=True)

    op.drop_constraint("ck_duels_category", "duels", type_="check")
    op.create_check_constraint(
        "ck_duels_category",
        "duels",
        "category IN ('code', 'bugfix', 'debate', 'explain', 'hinglish')",
    )
    op.create_check_constraint(
        "ck_duels_creator_kind",
        "duels",
        "(created_by_agent_id IS NOT NULL AND created_by_human_owner_id IS NULL) OR "
        "(created_by_agent_id IS NULL AND created_by_human_owner_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_duels_creator_kind", "duels", type_="check")
    op.drop_constraint("ck_duels_category", "duels", type_="check")
    op.create_check_constraint(
        "ck_duels_category",
        "duels",
        "category IN ('code', 'debate', 'explain', 'hinglish')",
    )
    op.alter_column("duels", "created_by_agent_id", nullable=False)
    op.drop_column("duels", "created_by_human_owner_id")
