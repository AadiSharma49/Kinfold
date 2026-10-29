from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from kinfold_api.models.base import Base


class Vote(Base):
    """One blind vote or judgment in a crowd-judged duel.

    A human vote (voter_type="human") is a bare pick: voter_owner_id is set,
    no critique. An agent judgment (voter_type="agent") is a structured
    critique: voter_agent_id is set, strengths/weaknesses/verdict/score are
    required. Agent judgments never count toward resolving the duel — only
    human votes do (see services/voting.py); they're scored afterward
    against the human result to produce a judge rating.
    """

    __tablename__ = "votes"
    __table_args__ = (
        CheckConstraint("voter_type IN ('human', 'agent')", name="ck_votes_voter_type"),
        CheckConstraint(
            "(voter_type = 'human' AND voter_owner_id IS NOT NULL AND voter_agent_id IS NULL) OR "
            "(voter_type = 'agent' AND voter_agent_id IS NOT NULL AND voter_owner_id IS NULL)",
            name="ck_votes_voter_matches_type",
        ),
        CheckConstraint(
            "voter_type = 'human' OR (score BETWEEN 1 AND 10 AND verdict IS NOT NULL)",
            name="ck_votes_agent_critique_required",
        ),
        Index(
            "uq_votes_duel_human_voter",
            "duel_id",
            "voter_owner_id",
            unique=True,
            postgresql_where="voter_type = 'human'",
        ),
        Index(
            "uq_votes_duel_agent_voter",
            "duel_id",
            "voter_agent_id",
            unique=True,
            postgresql_where="voter_type = 'agent'",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duels.id"), nullable=False, index=True
    )
    voter_type: Mapped[str] = mapped_column(String(10), nullable=False, default="human")
    voter_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id"), nullable=True, index=True
    )
    voter_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True
    )
    chosen_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duel_entries.id"), nullable=False
    )
    # Structured critique — only agent judgments fill these in.
    strengths: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    weaknesses: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(280), nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
