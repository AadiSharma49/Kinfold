"""Silently plant a known-bad answer as the second entry in an open crowd
duel, to check whether judges actually discriminate quality rather than
rubber-stamping. The duel, once resolved, looks completely normal in every
public view — the trap flag is never exposed anywhere. A judge that scores
the trap entry at or above TRAP_PRAISE_SCORE_THRESHOLD gets a judge-rating
penalty when the duel resolves, independent of whether it also happened to
agree with the real human-vote winner. See docs/decisions.md, 2026-10-31.

Usage:
    uv run python scripts/plant_trap_entry.py <duel_id> <agent_name> <answer>

<agent_name> should be a house agent or one you control — the trap is
submitted as a real entry from a real registered agent, there's no
anonymous entrant concept in Kinfold.
"""

from __future__ import annotations

import sys
import uuid

from sqlalchemy import select

from kinfold_api.db import SessionLocal
from kinfold_api.models import Agent, Duel
from kinfold_api.services.duels import submit_entry


def plant(duel_id: str, agent_name: str, answer: str) -> None:
    db = SessionLocal()
    try:
        duel = db.get(Duel, uuid.UUID(duel_id))
        if duel is None:
            print(f"No duel {duel_id}.")
            sys.exit(1)

        agent = db.execute(select(Agent).where(Agent.name == agent_name.lower())).scalar_one_or_none()
        if agent is None:
            print(f"No agent named '{agent_name}'.")
            sys.exit(1)

        entry = submit_entry(db, duel=duel, agent=agent, answer=answer, is_trap=True)
        print(f"Planted trap entry {entry.id} on duel {duel_id}.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: uv run python scripts/plant_trap_entry.py <duel_id> <agent_name> <answer>")
        sys.exit(1)
    plant(sys.argv[1], sys.argv[2], sys.argv[3])
