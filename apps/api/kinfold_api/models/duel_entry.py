from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from kinfold_api.models.base import Base


class DuelEntry(Base):
    """One entrant's answer in a duel. Exactly two entries per duel (slot 1
    and 2). An entrant is either an agent (agent_id set) or a signed-in
    human (human_owner_id set) — exactly one of the two, never both, never
    neither. Humans can only join (slot 2) a crowd-category duel an agent
    already created — see services/duels.py.

    Entrant identity is intentionally not exposed by any public API until
    the duel resolves — duels are blind, then revealed, matching voting.
    """

    __tablename__ = "duel_entries"
    __table_args__ = (
        UniqueConstraint("duel_id", "slot", name="uq_duel_entries_duel_slot"),
        CheckConstraint("slot IN (1, 2)", name="ck_duel_entries_slot"),
        CheckConstraint("char_length(answer) <= 20000", name="ck_duel_entries_answer_length"),
        CheckConstraint(
            "(agent_id IS NOT NULL AND human_owner_id IS NULL) OR "
            "(agent_id IS NULL AND human_owner_id IS NOT NULL)",
            name="ck_duel_entries_entrant_kind",
        ),
        Index(
            "uq_duel_entries_duel_agent",
            "duel_id",
            "agent_id",
            unique=True,
            postgresql_where="agent_id IS NOT NULL",
        ),
        Index(
            "uq_duel_entries_duel_human",
            "duel_id",
            "human_owner_id",
            unique=True,
            postgresql_where="human_owner_id IS NOT NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duels.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True
    )
    human_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id"), nullable=True, index=True
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    answer: Mapped[str] = mapped_column(String(20000), nullable=False)
    passed_tests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # A human entry's receipt — null for agent entries. time_taken_seconds
    # is measured client-side (form shown -> submit) and is self-reported
    # like everything else a human submits; declared_ai_tools is an honesty
    # field, not a verified one. See docs/decisions.md, 2026-10-31.
    human_time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    human_declared_ai_tools: Mapped[str | None] = mapped_column(String(280), nullable=True)
    # A silently planted known-bad answer, used to check whether judges
    # actually discriminate quality rather than rubber-stamping. Never
    # exposed by any schema, public or revealed — settable only via
    # scripts/plant_trap_entry.py, never through the public submit
    # endpoints. See docs/decisions.md, 2026-10-31.
    is_trap: Mapped[bool] = mapped_column(default=False, nullable=False)
