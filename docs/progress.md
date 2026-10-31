# Progress log

One entry per milestone: date, what got built, what's left, anything risky. Newest at the top.

## 2026-10-31: Queue item 4 — agent and human profile pages

**Branch:** `feature/agent-profiles`. Merged into `main`.

**Built:** `GET /v1/agents/{name}/profile` and `/agents/{name}` — agent info (rating, judge rating, is_house), a real per-category win/loss/draw record (not a fabricated per-category Elo — see `docs/questions-for-owner.md`, 2026-10-31), and recent resolved-duel history with opponent revealed and whatever real receipt data exists (pass/fail counts for code duels). `GET /v1/owners/{handle}/profile` and `/humans/{handle}` — a human's own duel-entry history with their real receipt (time taken, declared AI tools). An owner with no agents and no human entries 404s rather than showing an empty page, and the 404 doesn't distinguish "doesn't exist" from "exists but has done nothing." Leaderboard and duel-entry displays now link to both profile types.

**Scope note, logged as a judgment call:** per-category Elo and full agent receipts (tokens, latency, tool calls — from CLAUDE.md's "receipts on everything," never actually implemented anywhere) are real, bigger features, not retrofitted here. What's shown is 100% real data, nothing invented to fill the shape of the request.

**Try it:** seed the database (`uv run python scripts/seed.py`) then visit `/agents/kinfold-house-1` or `/humans/kinfold-house` with the stack running.

**Tests:** 64/64 `apps/api` (5 new: agent profile with history, 404 for unknown agent, owner profile 404 with no activity, owner profile after real human activity, 404 for unknown handle). Web lint/typecheck/build clean. Verified live against a running API with real seeded data — profile endpoints, page rendering, and leaderboard/duel-entry links all checked by hand.

**Left undone:** per-category Elo, full agent receipts (both flagged above as separate future work, not skipped silently).

**Risky:** none. No schema changes — profiles are computed from existing tables.

## 2026-10-31: Queue item 3 — onboarding speed measured, one real friction point found and fixed

**Branch:** `feature/onboarding-speed`. Merged into `main`.

**What I measured:** wrote `apps/api/scripts/measure_onboarding.py`, which walks the exact 5 named steps (sign in, create agent, connect, first duel, first vote) against a real running API and times each. GitHub OAuth itself can't be scripted without a real browser and a real GitHub test account, so "sign in" uses `dev-signup` as a stand-in — same backend work (create an owner row, issue a key), just missing GitHub's own redirect/consent round-trip.

**Raw API latency (warmed connection, 3 runs):**

| Step | Time |
|---|---|
| 1. Sign in | 15-16ms |
| 2. Create agent (mints the key in the same call) | 23-25ms |
| 3. Connect (`GET /v1/agents/me`) | 11-12ms |
| 4. Create first duel | 15-18ms |
| 5. First vote (after a second entrant fills the duel) | 72-105ms |
| **Total** | **140-174ms** |

(The first unwarmed run showed step 1 at ~2000ms — that's a Windows localhost IPv6-then-IPv4 connection-setup artifact, nothing to do with Kinfold or dev-signup; confirmed by hitting `/v1/health` first and watching the "real" first request drop to 11ms. Script now warms the connection before timing.)

**Conclusion: the API was never the bottleneck.** Total backend latency for the whole path is under 200ms. The real 2-minute budget is spent on GitHub's own OAuth consent screen (seconds to tens of seconds, outside Kinfold's control) and human time reading the dashboard and typing into 3 form fields — both comfortably fit inside 2 minutes already.

**One real friction point found and fixed, not just measured:** `ConnectKeyForm`'s "Sign in with GitHub" link always sent the user back to `/duels` after login, regardless of where they started — so signing in from `/dashboard` (exactly the onboarding path this item is about) dropped the user on the wrong page, adding an extra manual navigation step. Fixed: the link now records `window.location.pathname` in `sessionStorage` before navigating to GitHub, and `/auth/callback` reads it back (`takePostLoginRedirect()`) instead of hardcoding `/duels`. Falls back to `/duels` if nothing was recorded, so a direct visit to `/auth/callback` still behaves.

**Try it:**
```bash
docker compose up -d && cd apps/api && uv run alembic upgrade head && uv run uvicorn kinfold_api.main:app --reload
uv run python scripts/measure_onboarding.py
```

**Tests:** no new automated tests for the measurement script itself (it's a diagnostic tool, not product behavior) — the redirect fix is a one-line client-side change with no server behavior to test; verified manually by tracing the fixed code path (sessionStorage round-trip) rather than a new unit test, since it has no backend surface and the existing `apps/web` build/typecheck/lint already cover it compiling and running correctly. `apps/api` 59/59, `apps/mcp` 12/12, `apps/training` 2/2 unaffected; web lint/typecheck/build clean.

**Left undone:** none from item 3's scope. The target ("sign-in to first duel under 2 minutes") is already met by a wide margin once the redirect fix is in.

## 2026-10-31: Queue items 1-2 — onboarding dashboard, human duel entries

**Branch:** `onboarding-slice` (predates the autonomous-mode queue's `feature/<name>` convention — see `docs/questions-for-owner.md`). Merged into `main`.

**Item 1 — onboarding, done:** `/dashboard` (GitHub sign-in, reusing the existing `ConnectKeyForm`/`useConnectedKey`): lists my agents (new `GET /v1/owners/me/agents`), creates an agent, mints/revokes keys, shows a new key once with a copy button and warning. Ready-to-paste connect configs (Claude Code, Cursor, Python) with the real API URL and the new key filled in, plus a working "test connection" button hitting `/v1/agents/me`. `KINFOLD_DEV_SIGNUP` confirmed and now tested: defaults to `False` in `Settings` itself (not just docs), route 404s when off.

**Item 2 — human entry, done:** a signed-in human can join (not create) an open crowd-category duel with a text answer — `POST /v1/duels/{id}/human-entry`. Judged blind on the same ladder, revealed after voting, same as an agent. Receipt (time taken, declared AI tools) added per the updated instructions — both self-reported, both gated behind the same blind-until-resolved reveal as identity (a bug I caught before merging: showing the receipt early would itself leak which entry is human). "Can you beat the AI?" section on the homepage, linking to a real open crowd duel fetched server-side.

**Real bug found and fixed by these tests:** `services/voting.py`'s self-vote guard crashed with `AttributeError` the instant either duel entry had no agent (i.e., a human entry) — existing tests never exercised this path. Fixed to use `human_owner_id` directly.

**Try it:** `docker compose up -d && cd apps/api && uv run alembic upgrade head && uv run uvicorn kinfold_api.main:app --reload`, then `cd apps/web && pnpm dev`, visit `/dashboard` and the homepage's "Can you beat the AI?" link.

**Tests:** 59/59 `apps/api` (10 new this round: 6 human-entry, 3 owner-agents-listing, 1 dev-signup-default), 12/12 `apps/mcp`, 2/2 `apps/training` — all unaffected. Web lint/typecheck/build clean. Verified live end to end through the actual proxy routes (not just unit tests): create agent, mint key, test-connection, list/revoke keys, human entry with hidden-then-revealed receipt, homepage CTA linking to a real duel.

**Left undone / skipped:** nothing from items 1-2 skipped. Item 3 (measure onboarding speed) is next.

**Risky:** none newly introduced. Migrations are additive (new nullable columns, new partial-unique indexes); `agent_id` on `duel_entries` went from `NOT NULL` to nullable, backed by a check constraint ensuring exactly one of agent/human is set, so no existing row can become invalid.

## 2026-10-29: Priority reorder, honest pitch, deploy plan, sandbox restriction, M7 first slice

**Built, in order (each its own commit):**
1. Logged the new priority order (deploy → outside agents → first training cycle → M5 → rest) and the "don't claim training is live" rule in `docs/decisions.md`.
2. Fixed every present-tense "trains the model / self-improves" claim across the website, README, `/llms.txt`, and the unposted draft launch copy — all now say "planned" / "the goal" / "not live yet."
3. `docs/deploy-plan.md` (Hetzner CPX21, ~$5.39/mo, reasoning) and `docs/deploy-checklist.md` (full numbered sequence) — for approval, nothing bought or deployed.
4. `KINFOLD_SANDBOX_RESTRICTED` + `agents.sandbox_approved`: code duels are blocked for everyone except house/approved agents when this is on (off by default locally). gVisor itself needs a real server, so it's a checklist step, not built yet.
5. Confirmed the website already reads `KINFOLD_API_URL` correctly — pointing Vercel at the real API is one dashboard action for the user once deployed, not a code change.
6. M7 first slice: `export_preference_pairs.py` (open-weight-only, live-tested), `apps/training` with a DPO+LoRA pipeline test on a tiny model (heavy deps gated behind `uv sync --group train`, not auto-installed) and a gen-vs-base duel harness that runs real duels and never fakes a crowd-duel result.

**Try it:** see each piece's own README (`apps/training/README.md`) or `docs/deploy-checklist.md` for the deployment steps.

**Left undone:** the actual deployment (waiting on your approval from `docs/deploy-plan.md`), gVisor, a real training run on a real model, M5, the rest of M3/M8.

**Risky:** none newly introduced — the sandbox restriction defaults off (matches existing test/dev behavior unchanged), the training pipeline only touches a throwaway tiny model, nothing was deployed or purchased.

## 2026-10-29: Agent judging — the first slice of M3

**Built:** `POST /v1/duels/{id}/judgments` — an agent (not an entrant) submits a structured critique (strengths, weaknesses, verdict, score) on a crowd duel. Hidden until the duel resolves, then revealed with whether it agreed with the human-vote result. Agreement/disagreement moves a new `judge_rating` on the agent. Never counts toward the duel's own result — only human votes decide that. New `judge_duel` MCP tool; `judge_rating` now shown on `/leaderboard`.

**Try it:**
```bash
docker compose up -d && cd apps/api && uv run alembic upgrade head && uv run uvicorn kinfold_api.main:app --reload
```
Create two agents, a crowd duel (`category` debate/explain/hinglish), have a third agent call `judge_duel` (or `POST /v1/duels/{id}/judgments` directly), then resolve with real human votes and check `GET /v1/duels/{id}/judgments` and the judge's profile.

**Left undone (see `docs/decisions.md`, 2026-10-29, for the full list):** judging human entries (humans can't submit duel entries yet at all), trap entries, content moderation on critique text, anti-sycophancy ranking, the agent-opinions feed. The rest of M5 (owner dashboard, agent profile pages) and the backend deployment are also still open.

**Risky:** none newly introduced. The migration adds nullable/defaulted columns and two partial-unique indexes; verified against a live Postgres (migration applied cleanly, full test suite + a real end-to-end run through the actual MCP tool, including the reveal and rating-update behavior).

## 2026-10-28: Leaderboard page, agent discovery docs, orientation/briefing/world-state

**Built:**
- `/leaderboard` on the website — every agent ranked by Elo, with house-agent labels and W/L/D (M5).
- `/llms.txt` and `/skill.md` — public, self-service docs so an agent (or crawler) can learn what Kinfold is and join without a human walking it through anything (M4).
- MCP server now sends a short, versioned orientation on connect, has a new `get_briefing` tool (what happened since the agent's last visit, built from the event log), and a `kinfold://world` resource (top agents, open/judging duels, recent results) (M4).
- `docs/launch.md` — draft social posts and a demo video script, not yet posted or recorded.
- `docs/vision.md` restructured into explicit M1-M9 milestones; `docs/ideas.md` created to hold everything outside that plan.

**Try it:**
```bash
docker compose up -d && cd apps/api && uv run alembic upgrade head && uv run uvicorn kinfold_api.main:app --reload
cd apps/mcp && uv sync   # connect per apps/mcp/README.md, call get_briefing first
```
Then visit `/leaderboard`, `/llms.txt`, `/skill.md` on the running site.

**Left undone:** M3 (agent judging, judge ratings, anti-sycophancy, safety rules — all planned in `docs/decisions.md`), owner dashboard and agent profile pages (rest of M5), the backend still isn't deployed anywhere public.

**Risky:** nothing new. The briefing feature adds one nullable column (`agents.last_briefing_at`) via a normal migration; everything else is additive, no existing behavior changed.

## 2026-10-27: MCP server

**Built:** `apps/mcp` — agents connect with their `kf_live_` key and get 6 tools (`whoami`, `list_open_duels`, `get_duel`, `create_duel`, `submit_answer`, `leaderboard`) over stdio (Claude Code, Cursor) or streamable-http. Thin client over `apps/api`, no duplicated logic. 10 tests (mocked transport); full real path verified by hand (real agents, a code duel resolving through the sandbox, correct Elo deltas). Merged to `main` locally, not pushed.

**Try it:**
```bash
docker compose up -d && cd apps/api && uv run uvicorn kinfold_api.main:app --reload
cd apps/mcp && uv sync
# point an MCP client at it per apps/mcp/README.md
```

**Left undone:** TypeScript client SDK (Python/MCP is the only client so far), owner dashboard and a leaderboard page on the website, `docs/security.md`, and the backend still isn't deployed anywhere public.

**Risky:** nothing new — same DooD sandbox tradeoff as before, this just adds a protocol layer on top of already-tested endpoints.

## Earlier milestones (house agents, GitHub OAuth, production deploy config, blind crowd duels, verified sandbox duels)

Not individually logged here yet — see `docs/decisions.md` for the architecture decisions behind each, and `git log` for what shipped when. Starting this log from here forward.
