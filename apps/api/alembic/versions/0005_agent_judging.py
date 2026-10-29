"""agent judging: votes.voter_type/critique, agents.judge_rating

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-29

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("judge_rating", sa.Integer(), nullable=False, server_default="1200"),
    )

    op.drop_constraint("uq_votes_duel_voter", "votes", type_="unique")

    op.add_column(
        "votes",
        sa.Column("voter_type", sa.String(length=10), nullable=False, server_default="human"),
    )
    op.alter_column("votes", "voter_owner_id", nullable=True)
    op.add_column("votes", sa.Column("voter_agent_id", sa.UUID(), nullable=True))
    op.add_column("votes", sa.Column("strengths", sa.String(length=1000), nullable=True))
    op.add_column("votes", sa.Column("weaknesses", sa.String(length=1000), nullable=True))
    op.add_column("votes", sa.Column("verdict", sa.String(length=280), nullable=True))
    op.add_column("votes", sa.Column("score", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_votes_voter_agent_id_agents", "votes", "agents", ["voter_agent_id"], ["id"]
    )

    op.create_check_constraint("ck_votes_voter_type", "votes", "voter_type IN ('human', 'agent')")
    op.create_check_constraint(
        "ck_votes_voter_matches_type",
        "votes",
        "(voter_type = 'human' AND voter_owner_id IS NOT NULL AND voter_agent_id IS NULL) OR "
        "(voter_type = 'agent' AND voter_agent_id IS NOT NULL AND voter_owner_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_votes_agent_critique_required",
        "votes",
        "voter_type = 'human' OR (score BETWEEN 1 AND 10 AND verdict IS NOT NULL)",
    )

    op.create_index(
        "uq_votes_duel_human_voter",
        "votes",
        ["duel_id", "voter_owner_id"],
        unique=True,
        postgresql_where=sa.text("voter_type = 'human'"),
    )
    op.create_index(
        "uq_votes_duel_agent_voter",
        "votes",
        ["duel_id", "voter_agent_id"],
        unique=True,
        postgresql_where=sa.text("voter_type = 'agent'"),
    )


def downgrade() -> None:
    op.drop_index("uq_votes_duel_agent_voter", table_name="votes")
    op.drop_index("uq_votes_duel_human_voter", table_name="votes")
    op.drop_constraint("ck_votes_agent_critique_required", "votes", type_="check")
    op.drop_constraint("ck_votes_voter_matches_type", "votes", type_="check")
    op.drop_constraint("ck_votes_voter_type", "votes", type_="check")
    op.drop_constraint("fk_votes_voter_agent_id_agents", "votes", type_="foreignkey")
    op.drop_column("votes", "score")
    op.drop_column("votes", "verdict")
    op.drop_column("votes", "weaknesses")
    op.drop_column("votes", "strengths")
    op.drop_column("votes", "voter_agent_id")
    op.alter_column("votes", "voter_owner_id", nullable=False)
    op.drop_column("votes", "voter_type")
    op.create_unique_constraint("uq_votes_duel_voter", "votes", ["duel_id", "voter_owner_id"])
    op.drop_column("agents", "judge_rating")
