"""Human duel entries: duel_entries.human_owner_id, duels.winner_human_owner_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-31

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("duels", sa.Column("winner_human_owner_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_duels_winner_human_owner_id_owners", "duels", "owners", ["winner_human_owner_id"], ["id"]
    )

    op.add_column("duel_entries", sa.Column("human_owner_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_duel_entries_human_owner_id_owners",
        "duel_entries",
        "owners",
        ["human_owner_id"],
        ["id"],
    )

    op.drop_constraint("uq_duel_entries_duel_agent", "duel_entries", type_="unique")
    op.alter_column("duel_entries", "agent_id", nullable=True)

    op.create_check_constraint(
        "ck_duel_entries_entrant_kind",
        "duel_entries",
        "(agent_id IS NOT NULL AND human_owner_id IS NULL) OR "
        "(agent_id IS NULL AND human_owner_id IS NOT NULL)",
    )
    op.create_index(
        "uq_duel_entries_duel_agent",
        "duel_entries",
        ["duel_id", "agent_id"],
        unique=True,
        postgresql_where=sa.text("agent_id IS NOT NULL"),
    )
    op.create_index(
        "uq_duel_entries_duel_human",
        "duel_entries",
        ["duel_id", "human_owner_id"],
        unique=True,
        postgresql_where=sa.text("human_owner_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_duel_entries_duel_human", table_name="duel_entries")
    op.drop_index("uq_duel_entries_duel_agent", table_name="duel_entries")
    op.drop_constraint("ck_duel_entries_entrant_kind", "duel_entries", type_="check")
    op.alter_column("duel_entries", "agent_id", nullable=False)
    op.create_unique_constraint(
        "uq_duel_entries_duel_agent", "duel_entries", ["duel_id", "agent_id"]
    )
    op.drop_constraint("fk_duel_entries_human_owner_id_owners", "duel_entries", type_="foreignkey")
    op.drop_column("duel_entries", "human_owner_id")

    op.drop_constraint("fk_duels_winner_human_owner_id_owners", "duels", type_="foreignkey")
    op.drop_column("duels", "winner_human_owner_id")
