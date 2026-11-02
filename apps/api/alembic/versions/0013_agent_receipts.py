"""agent entry receipts: tokens in/out, tool calls, autonomous flag
(agent-reported), latency_ms (server-measured)

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("duel_entries", sa.Column("receipt_tokens_in", sa.Integer(), nullable=True))
    op.add_column("duel_entries", sa.Column("receipt_tokens_out", sa.Integer(), nullable=True))
    op.add_column("duel_entries", sa.Column("receipt_tool_calls", sa.Integer(), nullable=True))
    op.add_column("duel_entries", sa.Column("receipt_autonomous", sa.Boolean(), nullable=True))
    op.add_column("duel_entries", sa.Column("receipt_latency_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("duel_entries", "receipt_latency_ms")
    op.drop_column("duel_entries", "receipt_autonomous")
    op.drop_column("duel_entries", "receipt_tool_calls")
    op.drop_column("duel_entries", "receipt_tokens_out")
    op.drop_column("duel_entries", "receipt_tokens_in")
