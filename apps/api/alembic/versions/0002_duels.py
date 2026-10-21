"""duels, duel_entries, duel_tests, votes

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "duels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("prompt", sa.String(length=2000), nullable=False),
        sa.Column(
            "created_by_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False
        ),
        sa.Column(
            "winner_agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True
        ),
        sa.Column("is_draw", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "category IN ('code', 'debate', 'explain', 'hinglish')", name="ck_duels_category"
        ),
        sa.CheckConstraint("status IN ('open', 'judging', 'resolved')", name="ck_duels_status"),
        sa.CheckConstraint("char_length(prompt) <= 2000", name="ck_duels_prompt_length"),
    )
    op.create_index("ix_duels_category", "duels", ["category"])
    op.create_index("ix_duels_status", "duels", ["status"])

    op.create_table(
        "duel_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("duel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("duels.id"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("answer", sa.String(length=20000), nullable=False),
        sa.Column("passed_tests", sa.Integer(), nullable=True),
        sa.Column("total_tests", sa.Integer(), nullable=True),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.UniqueConstraint("duel_id", "slot", name="uq_duel_entries_duel_slot"),
        sa.UniqueConstraint("duel_id", "agent_id", name="uq_duel_entries_duel_agent"),
        sa.CheckConstraint("slot IN (1, 2)", name="ck_duel_entries_slot"),
        sa.CheckConstraint("char_length(answer) <= 20000", name="ck_duel_entries_answer_length"),
    )
    op.create_index("ix_duel_entries_duel_id", "duel_entries", ["duel_id"])
    op.create_index("ix_duel_entries_agent_id", "duel_entries", ["agent_id"])

    op.create_table(
        "duel_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("duel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("duels.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("input", sa.String(length=4000), nullable=False, server_default=sa.text("''")),
        sa.Column("expected_output", sa.String(length=4000), nullable=False),
        sa.UniqueConstraint("duel_id", "order_index", name="uq_duel_tests_duel_order"),
    )
    op.create_index("ix_duel_tests_duel_id", "duel_tests", ["duel_id"])

    op.create_table(
        "votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("duel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("duels.id"), nullable=False),
        sa.Column(
            "voter_owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id"), nullable=False
        ),
        sa.Column(
            "chosen_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("duel_entries.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.UniqueConstraint("duel_id", "voter_owner_id", name="uq_votes_duel_voter"),
    )
    op.create_index("ix_votes_duel_id", "votes", ["duel_id"])
    op.create_index("ix_votes_voter_owner_id", "votes", ["voter_owner_id"])


def downgrade() -> None:
    op.drop_table("votes")
    op.drop_table("duel_tests")
    op.drop_table("duel_entries")
    op.drop_table("duels")
