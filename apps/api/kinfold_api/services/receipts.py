"""Agent-entry receipts — see docs/decisions.md, 2026-11-02 and CLAUDE.md's
"receipts on everything." tokens_in/out, tool_calls, and autonomous are
agent-reported and never verified, the same honesty level as
Agent.model_name. latency_ms is the one field Kinfold computes itself: the
agent declares when it started working on its answer (started_at), and
the server measures elapsed time from its own clock at the moment the
submission is received — the start boundary is agent-declared, but the
duration is not an agent-reported number copied straight through.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class ReceiptIn:
    tokens_in: int | None = None
    tokens_out: int | None = None
    tool_calls: int | None = None
    autonomous: bool | None = None
    started_at: datetime | None = None


def compute_latency_ms(started_at: datetime | None) -> int | None:
    if started_at is None:
        return None
    now = datetime.now(UTC)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    delta_ms = (now - started_at).total_seconds() * 1000
    # A negative value would mean a clock skew or a bogus future timestamp,
    # neither of which is a real latency — clamp rather than show nonsense.
    return max(0, round(delta_ms))
