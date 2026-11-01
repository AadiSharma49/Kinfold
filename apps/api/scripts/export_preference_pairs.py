"""Export resolved duels as DPO preference pairs: {prompt, chosen, rejected}.

The real logic lives in kinfold_api.services.data_export — this is a thin
CLI wrapper, so the exact same eligibility/dedup/scrub rules back both
this script and the public /data page's live count (one source of truth,
never two numbers that can drift apart).

Run with:
    uv run python scripts/export_preference_pairs.py [--out data/preference_pairs.jsonl]

Writes three files: the JSONL pairs, a `.manifest.json` with run stats,
and a `DATASET_CARD.md` describing the dataset. All gitignored
(apps/api/.gitignore covers data/) — this is real duel data, not
something to commit.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from kinfold_api.db import SessionLocal
from kinfold_api.services.data_export import ExportManifest, write_export

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "preference_pairs.jsonl"


def export_pairs(db: Session, out_path: Path) -> int:
    """Kept for callers (including existing tests) that just want the
    count of pairs written, using an already-open session."""
    manifest = write_export(db, out_path)
    return manifest.pair_count


def export(out_path: Path) -> ExportManifest:
    """CLI entry point — opens its own connection to DATABASE_URL."""
    db = SessionLocal()
    try:
        return write_export(db, out_path)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    result = export(args.out)
    print(f"Wrote {result.pair_count} preference pairs to {args.out}")
    print(
        f"Considered {result.duels_considered} duels — skipped "
        f"{result.duels_skipped_closed_weight} closed-weight, "
        f"{result.duels_skipped_trap} trap, "
        f"{result.duels_skipped_duplicate} duplicate, "
        f"{result.duels_skipped_suspected_ai} suspected-AI human entry."
    )
    print(f"Also wrote: {', '.join(result.files[1:])}")
