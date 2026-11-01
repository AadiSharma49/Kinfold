"""Builds the preference-pair dataset: resolved, non-draw, non-trap duels
where both sides are "clean" — an open-weight agent or a human (humans
have no model to be closed-weight, so they're always eligible). This is
the single source of truth both the export script and the public /data
page's live count read from, so the two numbers can never drift apart.

Rules, each with a reason:
- Closed-weight agent on either side -> whole pair skipped (not just that
  side) — CLAUDE.md: only open-weight answers go into training sets, and
  the rejected text would still be training data otherwise.
- Either entry is_trap -> whole duel skipped — a trap is deliberately bad,
  never meant to teach a model anything, agent or human side.
- Either human entry is flagged human_suspected_ai -> whole pair skipped.
  We cannot prove humanity, so we don't claim it in training data when our
  own signals say the entry doesn't look human-typed — see
  docs/decisions.md, 2026-11-01. The entry stays on the public ladder;
  it's only excluded here.
- Draws -> skipped — no winner means no preference signal.
- Exact duplicate (prompt, chosen, rejected) triples -> only the first is
  kept.
- Every text field is run through pii_scrub.scrub_pii before being kept
  anywhere, including in a live count's underlying rows.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.models import Agent, Duel, DuelEntry
from kinfold_api.services.duels import winning_entry_id
from kinfold_api.services.pii_scrub import scrub_pii

DATASET_VERSION = "1"  # bump when the eligibility rules above change


@dataclass
class PreferencePair:
    duel_id: uuid.UUID
    category: str
    prompt: str
    chosen: str
    rejected: str
    chosen_is_human: bool
    rejected_is_human: bool

    def as_dict(self) -> dict:
        return {
            "duel_id": str(self.duel_id),
            "category": self.category,
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "chosen_is_human": self.chosen_is_human,
            "rejected_is_human": self.rejected_is_human,
        }


@dataclass
class ExportManifest:
    version: str
    generated_at: datetime
    pair_count: int
    duels_considered: int
    duels_skipped_closed_weight: int
    duels_skipped_trap: int
    duels_skipped_duplicate: int
    duels_skipped_suspected_ai: int
    files: list[str] = field(default_factory=list)


def _entry_eligibility(
    entry: DuelEntry, agents_by_id: dict[uuid.UUID, Agent]
) -> tuple[bool, bool, bool]:
    """Returns (eligible, is_human, is_suspected_ai)."""
    if entry.human_owner_id is not None:
        if entry.human_suspected_ai:
            return False, True, True
        return True, True, False
    agent = agents_by_id.get(entry.agent_id) if entry.agent_id else None
    if agent is None:
        return False, False, False
    return agent.open_weights, False, False


def compute_preference_pairs(db: Session) -> tuple[list[PreferencePair], ExportManifest]:
    duels = db.execute(
        select(Duel).where(Duel.status == "resolved", Duel.is_draw.is_(False))
    ).scalars().all()

    pairs: list[PreferencePair] = []
    seen: set[tuple[str, str, str]] = set()
    skipped_closed = 0
    skipped_trap = 0
    skipped_dup = 0
    skipped_suspected_ai = 0

    for duel in duels:
        entries = db.execute(
            select(DuelEntry).where(DuelEntry.duel_id == duel.id)
        ).scalars().all()
        if len(entries) != 2:
            continue

        if any(e.is_trap for e in entries):
            skipped_trap += 1
            continue

        winner_id = winning_entry_id(duel, entries)
        if winner_id is None:
            continue

        chosen_entry = next(e for e in entries if e.id == winner_id)
        rejected_entry = next(e for e in entries if e.id != winner_id)

        agent_ids = [e.agent_id for e in entries if e.agent_id is not None]
        agents_by_id = (
            {a.id: a for a in db.execute(select(Agent).where(Agent.id.in_(agent_ids))).scalars()}
            if agent_ids
            else {}
        )

        chosen_ok, chosen_is_human, chosen_suspected = _entry_eligibility(chosen_entry, agents_by_id)
        rejected_ok, rejected_is_human, rejected_suspected = _entry_eligibility(
            rejected_entry, agents_by_id
        )
        if not (chosen_ok and rejected_ok):
            if chosen_suspected or rejected_suspected:
                skipped_suspected_ai += 1
            else:
                skipped_closed += 1
            continue

        prompt = scrub_pii(duel.prompt)
        chosen_text = scrub_pii(chosen_entry.answer)
        rejected_text = scrub_pii(rejected_entry.answer)

        key = (prompt, chosen_text, rejected_text)
        if key in seen:
            skipped_dup += 1
            continue
        seen.add(key)

        pairs.append(
            PreferencePair(
                duel_id=duel.id,
                category=duel.category,
                prompt=prompt,
                chosen=chosen_text,
                rejected=rejected_text,
                chosen_is_human=chosen_is_human,
                rejected_is_human=rejected_is_human,
            )
        )

    manifest = ExportManifest(
        version=DATASET_VERSION,
        generated_at=datetime.now(UTC),
        pair_count=len(pairs),
        duels_considered=len(duels),
        duels_skipped_closed_weight=skipped_closed,
        duels_skipped_trap=skipped_trap,
        duels_skipped_duplicate=skipped_dup,
        duels_skipped_suspected_ai=skipped_suspected_ai,
    )
    return pairs, manifest


_DATASET_CARD_TEMPLATE = """# Kinfold preference pairs — dataset card

**Version:** {version}
**Generated:** {generated_at}
**Pairs:** {pair_count}

## What this is

Each row is a real Kinfold duel that actually resolved: a prompt, the
answer that won ("chosen"), and the answer that lost ("rejected"). The
winner was decided either by hidden tests (code duels) or by real,
un-fakeable blind human votes (crowd duels) — never by a model or by
Kinfold itself.

## Inclusion rules

- Resolved, non-draw duels only ({duels_considered} duels considered this run).
- Both sides open-weight-or-human — a closed-weight agent on either side
  skips the whole pair, not just that side ({duels_skipped_closed_weight} duels skipped for this).
- No trap entries (silently planted known-bad answers used to test judges)
  on either side ({duels_skipped_trap} duels skipped for this).
- Exact-duplicate (prompt, chosen, rejected) triples: only the first copy
  kept ({duels_skipped_duplicate} duplicates skipped).
- A self-declared human entry flagged by Kinfold's own AI-suspicion signals
  (answer length/speed, large single pastes) skips the whole pair
  ({duels_skipped_suspected_ai} duels skipped for this). We cannot prove
  humanity, so we label honestly and filter the data instead of claiming
  it — see `docs/decisions.md`. The entry stays on the public ladder; it's
  only excluded here.
- `chosen_is_human` / `rejected_is_human` tag which side (if either) was a
  self-declared human's own answer, not an agent's.

## Known limitations

- PII scrubbing (emails, phone numbers, Kinfold keys, common API token
  shapes) is a regex heuristic, not a guarantee — see
  `kinfold_api/services/pii_scrub.py`. It catches the common,
  unambiguous cases; it is not audited against every possible leak.
- Small scale. This is real data from a young, small arena — treat
  absolute counts as what they are, not a large benchmark dataset.
"""


def write_export(db: Session, out_path: Path) -> ExportManifest:
    pairs, manifest = compute_preference_pairs(db)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair.as_dict()) + "\n")

    manifest_path = out_path.with_suffix(".manifest.json")
    manifest_path.write_text(
        json.dumps(
            {
                "version": manifest.version,
                "generated_at": manifest.generated_at.isoformat(),
                "pair_count": manifest.pair_count,
                "duels_considered": manifest.duels_considered,
                "duels_skipped_closed_weight": manifest.duels_skipped_closed_weight,
                "duels_skipped_trap": manifest.duels_skipped_trap,
                "duels_skipped_duplicate": manifest.duels_skipped_duplicate,
                "duels_skipped_suspected_ai": manifest.duels_skipped_suspected_ai,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    card_path = out_path.parent / "DATASET_CARD.md"
    card_path.write_text(
        _DATASET_CARD_TEMPLATE.format(
            version=manifest.version,
            generated_at=manifest.generated_at.isoformat(),
            pair_count=manifest.pair_count,
            duels_considered=manifest.duels_considered,
            duels_skipped_closed_weight=manifest.duels_skipped_closed_weight,
            duels_skipped_trap=manifest.duels_skipped_trap,
            duels_skipped_duplicate=manifest.duels_skipped_duplicate,
            duels_skipped_suspected_ai=manifest.duels_skipped_suspected_ai,
        ),
        encoding="utf-8",
    )

    manifest.files = [out_path.name, manifest_path.name, card_path.name]
    return manifest
