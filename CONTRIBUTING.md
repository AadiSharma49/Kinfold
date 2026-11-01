# Contributing to Kinfold

Kinfold is early and built in the open. This doc is about actually
contributing code or docs, not about using the product — see `README.md`
for that.

## Before you start

- Read `CLAUDE.md` — the ground rules for this repo apply to any
  contributor, human or AI, not just Claude Code sessions.
- Read `docs/vision.md` for the roadmap and `docs/decisions.md` for why
  things are built the way they are. A lot of "why not just do X" is
  already answered there.
- Open an issue before a large change, especially anything touching the
  sandbox, auth, or the training pipeline — these have real tradeoffs
  already made and logged; a PR that reopens one without discussion is
  likely to get redirected rather than merged.

## Local setup

```bash
# Postgres + Redis
docker compose up -d

# Backend
cd apps/api
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn kinfold_api.main:app --reload

# Website (separate terminal)
cd apps/web
cp .env.example .env.local
pnpm install
pnpm dev
```

See `apps/api/README.md` and `apps/mcp/README.md` for component-specific
detail.

## Making a change

1. Branch off `main`: `git checkout -b feature/your-change`.
2. Write the code. Match the style already in the file you're editing
   over any outside convention — this codebase favors plain language,
   short sentences, no emoji, no hype words, and comments that explain
   *why* something is the way it is, not *what* the code does.
3. Before opening a PR, all of these must pass:
   ```bash
   cd apps/api && uv run ruff check . && uv run pytest
   cd apps/web && pnpm lint && pnpm exec tsc --noEmit && pnpm build
   ```
4. If your change affects a product or architecture decision (not just an
   implementation detail), add an entry to `docs/decisions.md` explaining
   why, not just what.
5. No fake data, ever — not in tests passing as real demos, not on the
   website, not in docs. See CLAUDE.md's "honest by default."

## What needs real review before merging

- Anything in the sandbox path (`kinfold_api/services/sandbox.py`) — it
  runs untrusted code; see `docs/security.md` for the current isolation
  model and its accepted gaps.
- Anything touching auth, API keys, or admin access.
- Changes to the event log (`services/events.py`) — it's append-only by
  design; a change that makes it mutable needs a documented reason.
- Anything that adds a third-party backend service dependency — not
  allowed per `CLAUDE.md` without an explicit decision to change that
  rule.

## Reporting a security issue

Don't open a public issue for a real vulnerability. See `docs/security.md`
for the current posture and known gaps, and open an issue marked clearly
(or contact the maintainer directly) for anything you believe is
exploitable.

## Code of conduct

Be direct and honest, same standard the product itself holds to. Critique
the work, not the person — the same rule Kinfold enforces on duel judges
(`docs/decisions.md`, 2026-10-31) applies to how contributors talk to each
other here.
