"""reports table; hidden_at on duels/duel_entries/votes; agents.is_disabled

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-31

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.UUID(), primary_key=True, default=uuid.uuid4),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column(
            "reporter_owner_id", sa.UUID(), sa.ForeignKey("owners.id"), nullable=True
        ),
        sa.Column(
            "reporter_agent_id", sa.UUID(), sa.ForeignKey("agents.id"), nullable=True
        ),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by_owner_id", sa.UUID(), sa.ForeignKey("owners.id"), nullable=True
        ),
        sa.CheckConstraint(
            "target_type IN ('duel', 'entry', 'judgment')", name="ck_reports_target_type"
        ),
        sa.CheckConstraint("char_length(reason) <= 500", name="ck_reports_reason_length"),
    )
    op.create_index("ix_reports_target_type", "reports", ["target_type"])
    op.create_index("ix_reports_target_id", "reports", ["target_id"])

    op.add_column("duels", sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("duel_entries", sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("votes", sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "agents",
        sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("agents", "is_disabled")
    op.drop_column("votes", "hidden_at")
    op.drop_column("duel_entries", "hidden_at")
    op.drop_column("duels", "hidden_at")
    op.drop_index("ix_reports_target_id", table_name="reports")
    op.drop_index("ix_reports_target_type", table_name="reports")
    op.drop_table("reports")
