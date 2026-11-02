# Progress log

One entry per milestone: date, what got built, what's left, anything risky. Newest at the top.

## 2026-11-02: Per-category ratings for agents and humans

**Branch:** `feature/category-ratings`. Merged into `main`.

**Built:** a new `category_ratings` table — one elo-updated row per
(entrant, category), independent of the one overall rating. Updates at
the same moment `apply_resolution` updates the overall rating, using the
same `elo_delta` function and K-factor, but as a fully separate number:
a code win doesn't move an agent's debate rating. Covers all five
categories (`code`, `bugfix`, `debate`, `explain`, `hinglish`) for
agents, and the three crowd categories a human can actually enter
(`debate`, `explain`, `hinglish`) for humans.

**Humans now get a real rating, overall and per category** —
`Owner.rating`/`wins`/`losses`/`draws`, starting at 1200 like an agent.
This replaces the fixed `HUMAN_VIRTUAL_RATING` stand-in and **supersedes**
the 2026-10-31 decision that humans get no rating at all — logged as a
new entry in `docs/decisions.md`, not an edit to the old one.

**Shown on profiles**: `/agents/[name]` and `/humans/[handle]` both show
an overall rating/record plus a per-category breakdown (rating, not just
win/loss/draw — the old `docs/questions-for-owner.md` choice not to track
this is also superseded). **Shown on the leaderboard**: `/leaderboard`
now has a category filter pill row; filtering to one category re-sorts
by that category's own rating and only lists agents who've actually had
a duel in it resolve (no fabricated 1200 for a category an agent has
never played).

**Scope choice, logged honestly:** no new human leaderboard page was
built — none existed before this round, and "per-category ratings"
reads as extending what exists (agent leaderboard, both profile pages),
not building a new page type from scratch. A human's own rating is
visible on their own profile.

**Tests:** 131/131 `apps/api` (6 new: agent category rating on a win,
category ratings move independently of each other, human overall +
category rating, leaderboard category filter excluding agents who
haven't played it, bad-category 400). 16/16 `apps/mcp` unaffected. Web
lint/typecheck/build clean.

**Risky:** none newly introduced — new table, new nullable-free columns
with safe defaults (1200/0/0/0) backfilled by the migration itself for
every existing owner.

## 2026-11-02: Receipts — a launch blocker, now actually built

**Branch:** `feature/receipts`. Merged into `main`.

**Built:** every agent entry (the duel creator's own answer and the
opponent's/fix's answer, including bugfix listings) can now carry a real
receipt: `model_name` (from the agent's own registration), `tokens_in`,
`tokens_out`, `tool_calls`, `autonomous` — all agent-reported, never
verified — and `latency_ms`, the one field Kinfold actually computes
itself from an agent-declared `started_at` timestamp against its own
server clock at submission. New migration `0013`. All fields optional —
an agent that reports nothing still submits fine, the receipt just shows
what's missing rather than inventing a value. Gated behind the same
`reveal` rule as agent identity, so a receipt can't leak which entry is
which before a crowd duel resolves.

Shown on duel pages after reveal (`duel-entries.tsx`), and in the dataset
export (`chosen_receipt`/`rejected_receipt` on every preference pair,
null for a human-authored side) — `DATASET_VERSION` bumped to `2` since
the row shape changed. MCP's `create_duel`/`submit_answer` tools and the
underlying `KinfoldClient` take the same optional receipt fields.

**Audited every receipt claim on the site** (`how-it-works`, the
homepage's receipt card and differentiator copy, `/privacy`) and
reworded each to say what's actually true now: fields are agent-reported
except latency, and any field can be missing rather than guaranteed
present. `README.md`, `llms.txt`, and `skill.md` had no receipt claims to
fix. Also removed "Bring a bug" from the roadmap's V1.5 list (it shipped
last round) now that it's cleanup, not just this round's work.

**Tests:** 127/127 `apps/api` (4 new: creator-entry receipt storage and
reveal, null-latency when `started_at` omitted, blind-until-resolved for
a crowd duel, export receipt fields). 16/16 `apps/mcp` (2 new: receipt
fields omitted when not given, included when given). Web lint/typecheck/
build clean.

**Risky:** none. Purely additive — new nullable columns, new optional
request fields, no existing behavior changed for a caller that sends
nothing new.

## 2026-11-01: Full git-history secret scan (gitleaks) — clean

Ran `gitleaks git --log-opts="--all"` (v8.30.1, downloaded directly from
the project's GitHub releases for this one-off scan, not added as a repo
dependency) over the entire local history — 44 commits, every branch.

**Result: 10 findings, all false positives, no real secret in history.**

- 8 `curl-auth-header` matches in `README.md`, `apps/mcp/README.md`, and
  `apps/web/src/app/skill.md/route.ts` — every one is the literal
  documentation placeholder `kf_owner_...` / `kf_live_...` (an ellipsis,
  not real key material) inside an example curl command.
- 2 `generic-api-key` matches in `apps/api/tests/test_judging_integrity.py`
  — test fixture agent names (`collapse_judge1`, `collapse_judge2`)
  sitting next to a `_key` variable name, not an actual key or token.

No rewrite of history was needed or performed, per standing instruction.

## 2026-11-01: Critique moderation audit — how it decides "personal comment," tested on 20 examples

**How it decides today:** `kinfold_api/services/critique_moderation.py` is a
keyword/regex heuristic, documented as such — not real NLP. It checks every
free-text judgment field against a fixed list of regex patterns (bare
personal-insult words; subject-plus-attribute patterns like "he is
obviously a..."; topic words for race/religion/sexuality/immigration
status; possessive-plus-personal-topic patterns like "his family..."). Any
match blocks the submission with a 400 and a fixed message. It has no
understanding of meaning, context, or language beyond literal
string/pattern matching — it either contains a blocked token/shape or it
doesn't.

**Test: 20 example critiques** (5 each: normal English, normal Hinglish,
personal-attack English, personal-attack Hinglish — full list in the new
`tests/test_critique_moderation.py`). Before any fix: 9/10 normal critiques
correctly allowed (1 false positive) and 6/10 personal attacks correctly
blocked (4 misses) — 15/20 (75%) correct overall.

Concretely, before the fix: **1 false positive** — "This looks like it was
rushed..." was blocked, because the original pattern matched any "looks
like" phrase, not just "looks like an idiot"-shaped insults. **4 misses**:
"This person is clearly an idiot..." (the subject pattern only recognized
he/she/they, not "this person"/"the writer"); "...sounds foreign..." (the
word list had "foreigner" but not "foreign"); a Hinglish sentence using the
English word "dumb" on its own ("...pakka dumb hai...": the original word
list only blocked "stupid"/"dumb" when preceded by "looks", not standalone);
and a Hinglish personal-background attack using Hindi possessives ("Uski
family background...": the pattern required English "his/her/their", which
"uski" never matches). Net: 15/20 correct (75%) before any change — the
heuristic's keyword-only nature meant it had essentially zero native
Hinglish coverage beyond catching an English slur that happened to be
embedded in an otherwise-Hindi sentence.

**Fix applied** (still a keyword heuristic — real NLP moderation remains a
reasonable future step, not built here): added a standalone personal-insult
word list (stupid, dumb, idiot, moron, incompetent, plus common Hinglish
insults — bewakoof, nalayak, pagal, ullu — the original list had zero
non-English words); narrowed the "looks X" pattern to drop "like" so the
common benign phrase "looks like..." stops false-positiving; widened the
subject pattern to cover "this person"/"the writer"/"the author"/"whoever
wrote this", not just he/she/they; added "foreign" alongside "foreigner";
added Hinglish possessives (uski/uska/iska/iski) alongside his/her/their
for the personal-background pattern. Re-ran the same 20 examples: **20/20
correct**, 0 false positives, 0 misses, now with real Hinglish-specific
coverage instead of accidental catches. Locked in by
`tests/test_critique_moderation.py` (20 new tests) so a future edit can't
silently reopen these.

**Known remaining limitation, unchanged:** still keyword/regex, not
semantic — a personal attack phrased without any of these specific words or
shapes (in either language) will not be caught, and an unusual but
legitimate critique that happens to contain a listed word could still be
blocked. This is the same honesty tradeoff as before, just with a measured
baseline and a real fix instead of an unverified claim.

**Tests:** 117/117 `apps/api` (20 new). No frontend changes.

**Risky:** none — stricter in a few directions (Hinglish insults, "this
person" phrasing), looser in exactly one (the "looks like" false positive),
all covered by the new test file.

## 2026-11-01: Hardening — trusted-proxy IP fix + load test / capacity estimate

**Branch:** `feature/hardening`.

**Trusted-proxy fix:** the request middleware's rate limiter previously trusted
`X-Forwarded-For` from anyone — any client could spoof a new IP on every
request and dodge the rate limit entirely. Now `X-Forwarded-For` is only
honored when the direct TCP peer is in `KINFOLD_TRUSTED_PROXY_IPS` (comma-
separated IPs/CIDR ranges, defaults to loopback only). In production, this
must be set to Caddy's static address on the compose network
(`172.28.0.10`, now pinned in `docker-compose.prod.yml`) — documented in
`docs/deploy-checklist.md`. 3 new tests prove: an untrusted peer's spoofed
header is ignored (all requests land in the real peer's rate-limit bucket),
a trusted peer's header is honored per real client IP, and a CIDR range
works. 93/93 `apps/api` tests passing.

**Load test — real numbers, this machine:**

Using `scripts/load_test.py` against a locally running API with
`KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE` relaxed to isolate raw throughput
from the rate limiter itself:

| Concurrency | Requests | Errors | req/s | p50 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|
| 10 | 300 | 0 | 163.9 | 45ms | 114ms | 368ms | 388ms |
| 20 | 500 | 0 | 120.4 | 121ms | 444ms | 543ms | 761ms |
| 50 | 500 | 0 | 151.7 | 280ms | 537ms | 614ms | 631ms |

Separately, with the rate limiter at its real default (120/min) and seeded
data present, a concurrency-20/200-request run correctly rejected 30/200
requests with 429s — confirmation the hardening itself works under
concurrent load from one IP, not a flaw in the numbers above.

**Test conditions (be honest about what this is and isn't):** AMD Ryzen 5
5600X, 6 cores / 12 threads, Windows, Docker Desktop running Postgres +
Redis + sandbox containers alongside everything else on the machine at the
same time — not a clean dedicated benchmark box. The API itself ran as one
local `uvicorn` process with no concurrency tuning. Treat these as rough
orientation numbers, not a lab-grade benchmark.

**Capacity note:** the production `Dockerfile` runs `uvicorn` with no
`--workers` flag — one Python process in production today, same as this
test. On a Hetzner CPX21 (3 vCPU, 4GB RAM), that process also shares the
box with Postgres, Redis, and on-demand sandbox containers for code duels —
real competition for the same 3 vCPUs, worse than this test machine's spare
capacity. Given these read-heavy endpoints (`/v1/duels`, `/v1/agents`,
`/v1/data/stats`) measured at 120-165 req/s here with a 6-core/12-thread
machine doing other work too, a rough, hedged estimate for a CPX21 running
everything (API + Postgres + Redis) is on the order of **40-80 req/s
sustained** before p95 latency climbs past what feels responsive —
materially lower than this box because of fewer cores and CPU sharing with
the database and sandbox containers. This is a planning estimate, not a
guarantee; the real number should be re-measured against the actual server
once it exists. The clearest lever if this turns out too low: add
`--workers N` to the Dockerfile's `CMD` (N ≈ vCPU count), which this build
does not currently use.

**Risky:** none — documentation-only change for the load test write-up; the
trusted-proxy fix changes production behavior (rate-limit bypass closed)
but is covered by tests and matches the existing default-to-loopback
behavior for anyone who hasn't set `KINFOLD_TRUSTED_PROXY_IPS` yet.

## 2026-11-01: Queue item 8 — data export quality + public /data page

**Branch:** `feature/data-quality`. Merged into `main`.

**Built:** moved export logic into `kinfold_api/services/data_export.py` as a shared service (export script + `GET /v1/data/stats` both call it — one source of truth). New: human-vs-agent pairs now included and tagged (previously silently dropped — a real bug fixed, predates human entries existing), trap-entry exclusion, exact-triple deduplication, PII scrubbing (emails/phones/Kinfold keys/common token prefixes, documented heuristic), dataset versioning, and a real per-run `DATASET_CARD.md`. New public `/data` page shows the live pair count against `KINFOLD_FIRST_TRAINING_RUN_TARGET_PAIRS` (500, a real chosen planning number, labeled honestly as a goal not a derived requirement).

**Try it:** `uv run python scripts/export_preference_pairs.py` for a real export (JSONL + manifest + dataset card); visit `/data` on the running site for the live count.

**Tests:** 86/86 `apps/api` (7 new: PII scrubbing, human-tagging, trap exclusion, dedup, manifest/card writing, stats endpoint × 2). Web lint/typecheck/build clean. Verified live end to end: real stats endpoint count, matching `/data` page number, and a full real export run producing all three files with correct content.

**Risky:** none. No new tables/columns — `data_export.py` reads existing tables; the export refactor kept the old `export_pairs(db, out_path)` signature so nothing else calling it needed to change.

## 2026-11-01: Queue item 7 — Open Graph share images

**Branch:** `feature/share-cards`. Merged into `main`.

**Built:** `opengraph-image.tsx` for `/duels/[id]`, `/agents/[name]`, `/humans/[handle]`, using Next's built-in `next/og` (same mechanism already used for the site favicon). Every card shows real fetched data — a duel's real category/prompt/status, an agent's real rating/judge-rating/record, a human's real win-loss-draw tally — never placeholder content. A not-found target gets a plain branded fallback card. Shared layout (`src/lib/og.tsx`) matches the site's own plain, honest visual language — no gradients, no stock-photo energy.

**Try it:** with the stack running, visit e.g. `http://localhost:3000/agents/kinfold-house-1/opengraph-image` directly, or just share a duel/profile link on X/LinkedIn/Slack once deployed — the preview card is this image.

**Tests:** no new automated tests — these are static image-rendering routes with no business logic to unit test; verified live by hand (all three routes return real 1200×630 PNGs built from live seeded data, confirmed visually). `apps/api` 79/79 unaffected. Web lint/typecheck/build clean.

**Risky:** none. No backend changes at all — purely new frontend routes reading existing public endpoints.

## 2026-11-01: Queue item 6 — reports and admin tools

**Branch:** `feature/reports-and-admin`. Merged into `main`.

**Built:** `POST /v1/reports` (anyone with a key can report a duel/entry/judgment) and a full admin surface behind `Owner.is_admin` (set by hand in the DB, no self-signup): list/resolve reports, hide a duel/entry/judgment, disable an agent, approve an agent for the sandbox, revoke any key. Every admin action writes its own `admin.*` event. A "Report" button is live on the website for duels, entries, and judgments.

**Scope choice:** admin tools are API-only this pass (no dashboard page yet) — logged in `docs/questions-for-owner.md`. The backend is fully ready for one; it's a frontend-only addition when wanted.

**Try it:** file a report via the website's Report button, or `POST /v1/reports` directly; flip `owners.is_admin` to `true` for your own row in the database to act on it via the `/v1/admin/*` endpoints.

**Tests:** 79/79 `apps/api` (9 new). Web lint/typecheck/build clean. Verified live end to end: report filing, 403 for a non-admin, admin promotion via direct DB update, listing reports, hiding a duel (confirmed 404 afterward), and the report button's correct show/hide behavior based on sign-in state.

**Risky:** none newly introduced. All migrations additive (a new table, new nullable/defaulted columns).

## 2026-10-31: Queue item 5 — judging integrity (traps, moderation, useful-rating, agreement-only collapse)

**Branch:** `feature/judging-integrity`. Merged into `main`.

**Built:**
- Trap entries: `scripts/plant_trap_entry.py` silently plants a known-bad answer; never exposed in any API response (verified by test and by hand); a judge that scores it ≥6 gets penalized on resolution, even if the trap also fooled the human vote.
- Critique moderation: a documented keyword heuristic blocks comments on appearance/identity/religion/background/personal life in judgment text — "judge the work, never the person."
- `POST /v1/judgments/{id}/useful`: only the critiqued entrant (agent or human) can rate a judgment useful; everyone else gets 403.
- Agreement-only critiques collapse to the bottom of the list (substantive ones first) via a length-based heuristic, both in the API's own ordering and visually dimmed on the website.
- MCP tools `get_judgments` and `rate_judgment_useful` so agent entrants have the same path as human entrants (who rate through the website).

**Try it:** seed/create a crowd duel, judge it, resolve it, then `POST /v1/judgments/{id}/useful` as the entrant — or just visit a resolved crowd duel's page on the website to see critiques rendered with the collapse styling.

**Tests:** 70/70 `apps/api` (6 new), 14/14 `apps/mcp` (2 new). Web lint/typecheck/build clean. Verified live end to end: moderation rejection, a real judgment, resolution via real votes, useful-rating, and the website rendering it all correctly.

**Left undone:** real NLP-based moderation (the keyword heuristic is a documented first pass, not full coverage) — logged as a known gap, not hidden.

**Risky:** none newly introduced. All migrations additive (new nullable/defaulted columns).

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
