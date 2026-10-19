"""initial schema: owners, agents, api_keys, events (append-only, hash-chained)

Revision ID: 0001
Revises:
Create Date: 2026-10-19

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "owners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("handle", sa.String(length=40), nullable=False),
        sa.Column("github_id", sa.String(length=64), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("handle ~ '^[a-z0-9_-]{3,40}$'", name="ck_owners_handle_format"),
    )
    op.create_index("ix_owners_handle", "owners", ["handle"], unique=True)
    op.create_index("ix_owners_github_id", "owners", ["github_id"], unique=True)

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=280), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("model_family", sa.String(length=40), nullable=False),
        sa.Column("open_weights", sa.Boolean(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint("name ~ '^[a-z0-9_-]{3,40}$'", name="ck_agents_name_format"),
        sa.CheckConstraint("char_length(description) <= 280", name="ck_agents_description_length"),
    )
    op.create_index("ix_agents_owner_id", "agents", ["owner_id"])
    op.create_index("ix_agents_name", "agents", ["name"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id"), nullable=False),
        sa.Column(
            "agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True
        ),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('owner', 'agent')", name="ck_api_keys_kind"),
    )
    op.create_index("ix_api_keys_owner_id", "api_keys", ["owner_id"])
    op.create_index("ix_api_keys_agent_id", "api_keys", ["agent_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=60), nullable=False),
        sa.Column(
            "agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id"), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default=sa.text("'server'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_events_seq", "events", ["seq"], unique=True)
    op.create_index("ix_events_hash", "events", ["hash"], unique=True)

    # Append-only: block UPDATE and DELETE on events at the database level,
    # regardless of which role or application issues the statement.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'events is append-only: % is not allowed', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER events_no_update
        BEFORE UPDATE ON events
        FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER events_no_delete
        BEFORE DELETE ON events
        FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS events_no_delete ON events")
    op.execute("DROP TRIGGER IF EXISTS events_no_update ON events")
    op.execute("DROP FUNCTION IF EXISTS prevent_event_mutation()")
    op.drop_table("events")
    op.drop_table("api_keys")
    op.drop_table("agents")
    op.drop_table("owners")
