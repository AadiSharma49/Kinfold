from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from kinfold_api.models.base import Base


class Duel(Base):
    """created_by_agent_id is set for every category except "bugfix" (a
    bug listing — see docs/bring-a-bug.md), where a human lists the bug
    instead and created_by_human_owner_id is set — exactly one of the
    two, never both, mirroring DuelEntry's agent/human entrant split."""

    __tablename__ = "duels"
    __table_args__ = (
        CheckConstraint(
            "category IN ('code', 'bugfix', 'debate', 'explain', 'hinglish')",
            name="ck_duels_category",
        ),
        CheckConstraint(
            "status IN ('open', 'judging', 'resolved', 'expired')",
            name="ck_duels_status",
        ),
        CheckConstraint("char_length(prompt) <= 2000", name="ck_duels_prompt_length"),
        CheckConstraint(
            "(created_by_agent_id IS NOT NULL AND created_by_human_owner_id IS NULL) OR "
            "(created_by_agent_id IS NULL AND created_by_human_owner_id IS NOT NULL)",
            name="ck_duels_creator_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    prompt: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    created_by_human_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id"), nullable=True
    )
    winner_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    # Set instead of winner_agent_id when a human entry wins — never both.
    winner_human_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id"), nullable=True
    )
    is_draw: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # When the duel entered "judging" (both entries present). Expiry is
    # measured from here, not created_at, so an open duel waiting for an
    # opponent is never expired for that reason. Null while open.
    judging_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Set when a judging duel passes KINFOLD_DUEL_EXPIRY_MINUTES. Expired
    # duels have no rating change; an admin can retry them.
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set by an admin action in response to a report. A hidden duel 404s
    # from every public route — see docs/decisions.md, 2026-10-31.
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set when an entry in this duel is hidden after the duel resolved and
    # the rating changes are reversed. Public profiles and the dataset
    # export omit voided duels so a moderated entry cannot keep changing
    # ratings or stats — see services/duels.py:void_duel_ratings.
    ratings_voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
