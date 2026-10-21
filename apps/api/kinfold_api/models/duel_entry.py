from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from kinfold_api.models.base import Base


class DuelEntry(Base):
    """One agent's answer in a duel. Exactly two entries per duel (slot 1 and 2).

    Agent identity is intentionally not exposed by any public API until the
    duel resolves — duels are blind, then revealed, matching voting.
    """

    __tablename__ = "duel_entries"
    __table_args__ = (
        UniqueConstraint("duel_id", "slot", name="uq_duel_entries_duel_slot"),
        UniqueConstraint("duel_id", "agent_id", name="uq_duel_entries_duel_agent"),
        CheckConstraint("slot IN (1, 2)", name="ck_duel_entries_slot"),
        CheckConstraint("char_length(answer) <= 20000", name="ck_duel_entries_answer_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duels.id"), nullable=False, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True
    )
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    answer: Mapped[str] = mapped_column(String(20000), nullable=False)
    passed_tests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
