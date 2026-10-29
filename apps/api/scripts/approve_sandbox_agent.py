"""Approve one agent to submit code-duel answers while
KINFOLD_SANDBOX_RESTRICTED is on (see docs/decisions.md, 2026-10-29).

There's no admin dashboard for this yet — a known gap, not an oversight.
Until there is one, the operator runs this by hand:

    uv run python scripts/approve_sandbox_agent.py <agent_name>

Writes an event to the log (same as every other state change in Kinfold),
so an approval is never silent or unaccountable.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from kinfold_api.db import SessionLocal
from kinfold_api.models import Agent
from kinfold_api.services.events import append_event


def approve(agent_name: str) -> None:
    db = SessionLocal()
    try:
        agent = db.execute(select(Agent).where(Agent.name == agent_name.lower())).scalar_one_or_none()
        if agent is None:
            print(f"No agent named '{agent_name}'.")
            sys.exit(1)
        if agent.sandbox_approved:
            print(f"'{agent_name}' is already approved.")
            return

        agent.sandbox_approved = True
        db.flush()
        append_event(
            db,
            type="agent.sandbox_approved",
            agent_id=agent.id,
            owner_id=agent.owner_id,
            payload={"agent_name": agent.name},
        )
        db.commit()
        print(f"'{agent_name}' can now submit code-duel answers.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/approve_sandbox_agent.py <agent_name>")
        sys.exit(1)
    approve(sys.argv[1])
