"""category_ratings table; owners.rating/wins/losses/draws (humans get a
real rating instead of the fixed HUMAN_VIRTUAL_RATING stand-in)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("owners", sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"))
    op.add_column("owners", sa.Column("wins", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("owners", sa.Column("losses", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("owners", sa.Column("draws", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "category_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column(
            "human_owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id"), nullable=True
        ),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "category IN ('code', 'bugfix', 'debate', 'explain', 'hinglish')",
            name="ck_category_ratings_category",
        ),
        sa.CheckConstraint(
            "(agent_id IS NOT NULL AND human_owner_id IS NULL) OR "
            "(agent_id IS NULL AND human_owner_id IS NOT NULL)",
            name="ck_category_ratings_entrant_kind",
        ),
    )
    op.create_index("ix_category_ratings_agent_id", "category_ratings", ["agent_id"])
    op.create_index("ix_category_ratings_human_owner_id", "category_ratings", ["human_owner_id"])
    op.create_index(
        "ix_category_ratings_agent_category",
        "category_ratings",
        ["agent_id", "category"],
        unique=True,
        postgresql_where=sa.text("agent_id IS NOT NULL"),
    )
    op.create_index(
        "ix_category_ratings_human_category",
        "category_ratings",
        ["human_owner_id", "category"],
        unique=True,
        postgresql_where=sa.text("human_owner_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("category_ratings")
    op.drop_column("owners", "draws")
    op.drop_column("owners", "losses")
    op.drop_column("owners", "wins")
    op.drop_column("owners", "rating")
