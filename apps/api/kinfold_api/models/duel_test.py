from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from kinfold_api.models.base import Base


class DuelTest(Base):
    """A hidden test case for a 'code' duel: stdin in, expected stdout out.

    Supplied by the duel's creator at creation time (v0 trust model — see
    docs/decisions.md). Never exposed by any public API.
    """

    __tablename__ = "duel_tests"
    __table_args__ = (UniqueConstraint("duel_id", "order_index", name="uq_duel_tests_duel_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("duels.id"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    input: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    expected_output: Mapped[str] = mapped_column(String(4000), nullable=False)
