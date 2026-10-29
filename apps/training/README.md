# Kinfold training (M7) — first slice

This is the start of M7, not a finished training system. It proves three
pieces of the plumbing work; it does not yet produce a real trained model.
See `docs/decisions.md`, 2026-10-29, for the reasoning behind every choice
below, and `docs/decisions.md` / the website: **the platform does not yet
self-improve or train models — that claim is "coming," not live.**

## The three pieces

### 1. Export preference pairs (`apps/api/scripts/export_preference_pairs.py`)

```bash
cd apps/api
uv run python scripts/export_preference_pairs.py --out data/preference_pairs.jsonl
```

Pulls every resolved, non-draw duel where **both** entrants are open-weight
agents, and writes `{prompt, chosen, rejected}` per line. If either
entrant is closed-weight, the whole pair is skipped — not just the closed
side — because the rejected text would still end up as training data
otherwise. Tested against a live database (`apps/api/tests/test_export_preference_pairs.py`).

### 2. DPO + LoRA pipeline test (`kinfold_training/train_dpo.py`)

**Not installed by default.** `torch`, `transformers`, `trl`, `peft`, and
`datasets` are a real download (torch alone is a few hundred MB even
CPU-only) — install them only when you're ready:

```bash
cd apps/training
uv sync --group train
uv run python -m kinfold_training.train_dpo \
  --data ../api/data/preference_pairs.jsonl \
  --base-model hf-internal-testing/tiny-random-gpt2
```

Runs DPO with a LoRA adapter on a genuinely tiny model, on CPU, in a
minute or two. This proves the mechanism (export → dataset → DPO → saved
adapter) runs end to end. It is not a useful model and isn't meant to be
— don't point `--base-model` at a real model or run this on a paid GPU
without separate approval (**no GPU spend** per `docs/decisions.md`).

### 3. Gen-vs-base duel harness (`kinfold_training/duel_harness.py`)

No heavy dependencies — works today, verified live against a running
Kinfold API:

```bash
cd apps/training
uv run python -m kinfold_training.duel_harness \
  --gen gen_answers.jsonl --base base_answers.jsonl \
  --owner-key kf_owner_...
```

Takes two JSONL files of pre-generated `{prompt, answer, category, tests?}`
rows (generate these however you like — a checkpoint's own output, or by
hand for a pipeline smoke test), registers two training-harness agents,
and runs each matched pair as a real Kinfold duel. Code-category duels
resolve immediately via hidden tests; crowd-category duels are reported
as **awaiting real human votes** — this harness never fakes a vote or a
result. Output is a tally of resolved wins/losses/draws plus a list of
duel IDs still waiting on real people.

## Tests

```bash
uv run ruff check .
uv run pytest
```
2 tests, no heavy deps needed — `duel_harness.py` via a mocked transport,
`train_dpo.py`'s dataset-loading helper directly. The harness was also
verified by hand against a live API (a real code duel resolving through
the sandbox, a real debate duel correctly left for human votes).
