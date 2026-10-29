"""Export resolved duels as DPO preference pairs: {prompt, chosen, rejected}.

Open-weight only, per CLAUDE.md ("only open-weight model answers go into
training sets"): a pair is exported only if BOTH entrants' agents have
open_weights=True. If either side is closed-weight, the whole pair is
skipped — not just the closed side — because the rejected text would
still be training data otherwise. Draws are skipped too: no winner means
no preference signal.

Run with:
    uv run python scripts/export_preference_pairs.py [--out data/preference_pairs.jsonl]

Output is gitignored (apps/api/.gitignore already covers data/, see the
root .gitignore's same pattern) — this is real duel data, not something to
commit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from kinfold_api.db import SessionLocal
from kinfold_api.models import Agent, Duel, DuelEntry

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "preference_pairs.jsonl"


def export_pairs(db: Session, out_path: Path) -> int:
    """Core logic, taking an explicit session — same dependency-injection
    pattern as every service function, so tests can pass the test
    transaction's session instead of a brand-new connection to DATABASE_URL."""
    entry_a = aliased(DuelEntry)
    entry_b = aliased(DuelEntry)
    agent_a = aliased(Agent)
    agent_b = aliased(Agent)

    rows = db.execute(
        select(Duel, entry_a, entry_b, agent_a.open_weights, agent_b.open_weights)
        .join(entry_a, (entry_a.duel_id == Duel.id) & (entry_a.slot == 1))
        .join(entry_b, (entry_b.duel_id == Duel.id) & (entry_b.slot == 2))
        .join(agent_a, agent_a.id == entry_a.agent_id)
        .join(agent_b, agent_b.id == entry_b.agent_id)
        .where(Duel.status == "resolved", Duel.is_draw.is_(False))
    ).all()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for duel, e1, e2, a1_open, a2_open in rows:
            if not (a1_open and a2_open):
                continue
            if duel.winner_agent_id == e1.agent_id:
                chosen, rejected = e1.answer, e2.answer
            elif duel.winner_agent_id == e2.agent_id:
                chosen, rejected = e2.answer, e1.answer
            else:
                continue  # no recorded winner — shouldn't happen for a non-draw resolved duel

            f.write(
                json.dumps(
                    {
                        "duel_id": str(duel.id),
                        "category": duel.category,
                        "prompt": duel.prompt,
                        "chosen": chosen,
                        "rejected": rejected,
                    }
                )
                + "\n"
            )
            written += 1
    return written


def export(out_path: Path) -> int:
    """CLI entry point — opens its own connection to DATABASE_URL."""
    db = SessionLocal()
    try:
        return export_pairs(db, out_path)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    count = export(args.out)
    print(f"Wrote {count} preference pairs to {args.out}")
