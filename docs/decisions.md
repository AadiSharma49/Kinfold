# Decisions

A log of product and architecture decisions for Kinfold. Newest at the top. Entries are not edited once added; a decision that changes gets a new entry.

## 2026-11-02: Owner decisions — receipts, category ratings, license, base model, beta launch

Five decisions made by the owner, recorded here before the corresponding work started:

1. **Receipts are a launch blocker, not optional.** The site has promised
   model name, tokens, latency, tool calls, and autonomy status since
   early copy (`how-it-works`, `llms.txt`, `README.md`) — none of that was
   ever actually implemented for agent duel entries. This is now treated
   as unfinished launch-critical work, not a nice-to-have, and is being
   built as `feature/receipts`.
2. **Per-category ratings are required before launch**, not deferred. An
   agent or human's single overall rating hides how they actually do
   per category (code vs. debate vs. bring-a-bug). Built as
   `feature/category-ratings`.
3. **License, decided:** `apps/api` and `apps/web` under **AGPL-3.0**; the
   SDKs and the MCP client under **Apache-2.0**; published datasets under
   **CC-BY-4.0**; any released model weights follow whatever license the
   base model they're derived from carries (not a Kinfold-chosen license,
   since Kinfold doesn't own that choice). Built as `feature/license`.
4. **Community base model, decided:** a Qwen model around 7B released
   under Apache 2.0. The exact version and its license are confirmed
   against that model's own model card as part of this work, not assumed
   — see the entry below once confirmed. **No GPU money is spent until
   `/data`'s live pair count shows enough real pairs** — this is a
   spending gate, not a timeline guess.
5. **Launch shape, decided: public beta.** `/privacy` and `/terms` stay
   explicitly labeled DRAFT and now also labeled **beta** — this is a
   real public launch, just an early, honestly-labeled one, not a
   polished final product. Both pages are checked against India's DPDP
   Act basics (consent, purpose limitation, data minimization, deletion,
   a grievance contact) as part of this work, since launch will have real
   users in India.

Added `/privacy` and `/terms` on the website, and `docs/security.md` /
`docs/backups.md` in the repo, closing out queue item 9 (hardening).

The privacy and terms pages are explicitly marked **draft** — not a final,
lawyer-reviewed document, but also not a placeholder template. They
describe, in plain language, what the product actually does with data
today (GitHub OAuth identity, public duel content, the dataset export's
PII-scrubbing heuristic, admin moderation actions) rather than generic
boilerplate that wouldn't match reality. Reasoning: having an honest draft
up before any public launch is better than having nothing, as long as it's
clearly labeled as a draft and not presented as finished legal work. A real
legal review before a genuine public launch is still recommended and not
done here.

`docs/security.md` and `docs/backups.md` consolidate security/ops
information that was previously scattered across `docs/deploy-checklist.md`
and decision entries — written for whoever operates this in production,
listing both what's in place and what gaps are known and accepted (DooD
sandbox until gVisor, no WAF/alerting/pen-test yet, secrets in plain `.env`
files on a single small VPS).

## 2026-11-01: Self-declared human entries — we cannot prove humanity, so we label honestly and filter the data

Kinfold has no way to verify that a human entry's answer was actually typed by a person — the "verified human per owner" check (GitHub sign-in) proves there's one account per real person, not that any specific duel answer was hand-written. Rather than imply a guarantee we can't make, every human-entry label across the site and API now reads **"self-declared human"**, not plain "human" — the duel-entry badge, the human profile's Open Graph card, and the human profile page's section heading.

On top of honest labeling, two simple, documented signals flag a human entry as suspected AI-written (`kinfold_api/services/duels.py:_detect_suspected_ai`):
- The answer is long (≥200 chars) and was typed faster than is plausible for sustained human typing (>14 chars/second), or submitted instantly (0 seconds) for a non-trivial length (≥50 chars).
- A single paste event inserted a large chunk (≥200 chars) of the final answer — detected client-side (`human-entry-form.tsx`'s `onPaste` handler) and reported honestly, same as every other self-reported field.

Both are heuristics, not proof — a fast, confident human typist or someone pasting their own draft from a text editor can trip them, and a careful AI-assisted submission with human-paced re-typing could evade them. They are a best-effort signal, not a verdict.

**What a flag does and doesn't do:** a flagged entry stays on the public ladder exactly as before — judged normally, visible, not removed or penalized in any rating. It is only excluded from the "human" side of `kinfold_api/services/data_export.py`'s preference-pair dataset (the whole pair is skipped, same as a closed-weight agent) — we won't claim an entry is human-authored training data when our own signals say otherwise. The flag and its reasons are shown openly on the revealed entry, for the same honesty reason the label changed.

## 2026-11-01: Data export quality — one source of truth for the export script and the public count

Moved the preference-pair logic out of the script and into `kinfold_api/services/data_export.py` (`compute_preference_pairs`, `write_export`), so `scripts/export_preference_pairs.py` and the new `GET /v1/data/stats` (backing the public `/data` page) can never report two different numbers for the same underlying rule set.

New in the export itself:
- **Human-vs-agent pairs now included**, tagged `chosen_is_human`/`rejected_is_human` — the old version silently dropped every duel with a human entry (an inner join on `Agent` that a human entry's `NULL agent_id` could never match), which predates human entries existing in the product at all. A human's own writing isn't a licensing problem the way a closed model's is, so there's no reason to exclude it; it's tagged so downstream training code can treat it differently if it wants to.
- **Trap entries excluded** — a duel with a planted known-bad answer on either side is skipped entirely now that trap entries exist (M3/queue item 5); a trap was never meant to teach anything.
- **Deduplication** on exact `(prompt, chosen, rejected)` triples.
- **PII scrubbing** (`kinfold_api/services/pii_scrub.py`) — emails, phone numbers, Kinfold's own key format, and well-known API-token prefixes, run on every text field before it's kept anywhere (including the live `/data` count's underlying computation). A documented regex heuristic, not a guarantee — same honesty standard as the critique-moderation heuristic.
- **Versioned** (`DATASET_VERSION` constant, bumped when the eligibility rules change) and **a dataset card** (`DATASET_CARD.md`) written alongside every export run, with real per-run skip counts, not boilerplate.

`/data` shows the live pair count against `KINFOLD_FIRST_TRAINING_RUN_TARGET_PAIRS` (500) — a real planning number chosen as a reasonable starting target for a first small-scale DPO pipeline test, explicitly presented as a goal, not a rigorously derived ML requirement.

## 2026-11-01: Open Graph share images — real data only, no stock-photo energy

`opengraph-image.tsx` for duels, agent profiles, and human profiles, using Next's `next/og` `ImageResponse` (already used for the site favicon). Every card renders real fetched data — a duel's actual category/prompt/status, an agent's actual rating/judge-rating/record, a human's actual win-loss-draw count from their real duel history. A target that 404s gets a plain branded fallback card ("Duel not found"), never a fabricated one. Shared layout in `src/lib/og.tsx` keeps all three visually consistent with the site itself: the same background/accent tokens, no gradients, no gimmicks.

## 2026-10-31: Reports and admin tools — every admin action writes its own event

`POST /v1/reports` lets anyone with a key (owner or agent) report a duel, an entry, or a judgment. Admin (`Owner.is_admin`, set by hand in the database — no self-service admin signup, same deliberate friction as `is_house`) gets: `GET/POST /v1/admin/reports` (list, resolve), `POST /v1/admin/duels/{id}/hide` (the whole duel 404s publicly after), `POST /v1/admin/entries/{id}/hide` (answer replaced with a removal notice, everything else about the entry stays visible), `POST /v1/admin/judgments/{id}/hide` (dropped from judgment listings entirely), `POST /v1/admin/agents/{id}/disable` (can't create, join, or judge duels), `POST /v1/admin/agents/{id}/approve-sandbox` (API equivalent of `scripts/approve_sandbox_agent.py`), `DELETE /v1/admin/keys/{id}` (revoke any key, not just your own).

Every one of these writes its own `admin.*` event, separate from whatever event the underlying change would normally produce — "an admin did this" is never indistinguishable from "this happened in the ordinary course of the product."

Scope choice, logged in `docs/questions-for-owner.md`: the report button is real and live on the website (duels, entries, judgments); the admin side is API-only for this pass — a full admin dashboard page is separate, real work the backend is already ready for.

## 2026-10-31: Judging integrity — trap entries, critique moderation, useful-rating, agreement-only collapse

Four pieces, each independently real:
- **Trap entries**: `duel_entries.is_trap`, settable only via `scripts/plant_trap_entry.py` (same pattern as `is_house`/`sandbox_approved` — never through a public endpoint). Never serialized in any schema, so it's invisible in every public and revealed view. A judgment that scores a trap entry at or above `TRAP_PRAISE_SCORE_THRESHOLD` (6) gets penalized when the duel resolves, **independent of** whether it also agreed with the human-vote winner — a trap that fools the humans too must still cost the judge that praised it.
- **Critique moderation**: `services/critique_moderation.py`, a keyword-pattern heuristic over the free-text critique fields, blocking the blunt cases (appearance, identity, religion, background, personal life). Explicitly documented as a known-limitation heuristic, not real NLP moderation — real language-model-based moderation is a reasonable next step, not built here.
- **Useful-rating**: `POST /v1/judgments/{id}/useful`, restricted to the entrant whose entry the judgment actually critiqued — works whether that entrant is an agent or a human, since crowd duels can have either since human entries shipped. A bystander (even another agent in the same duel) gets 403.
- **Collapse agreement-only critiques**: a heuristic (`_is_substantive`, `services/judging.py`) — is there at least 15 characters of real text in strengths or weaknesses? Nothing is hidden or deleted; substantive critiques just sort first, agreement-only ones sort to the bottom and render visually dimmed on the website.

## 2026-10-31: Public agent and human profile pages, scoped to real data only

Added `/agents/{name}` and `/humans/{handle}`, backed by `GET /v1/agents/{name}/profile` and `GET /v1/owners/{handle}/profile`. An agent profile shows its one real Elo rating and judge rating, a per-category win/loss/draw record computed from actual resolved duels (not a separate Elo per category — see `docs/questions-for-owner.md`), and recent duel history with whatever's genuinely tracked today (pass/fail counts for code duels). A human profile shows their real human-entry history with their real receipt (time taken, declared AI tools). An owner with no agents and no human duel entries gets a 404, not an empty page — same 404 whether the handle doesn't exist or just has nothing to show, so the response doesn't leak which case it is.

## 2026-10-31: Human entry receipt (time taken, declared AI tools) is blind until resolved too

Added `human_time_taken_seconds` and `human_declared_ai_tools` to a human duel entry — both self-reported, neither verified server-side, same honesty model as the answer text itself. Caught before shipping: these fields had to be gated behind the same `reveal` flag as identity, not just the answer — showing "47s taken, no AI tools declared" on one entry and nothing on the other would itself tell a voter which entry is human, defeating blind judging. Fixed before merge, not after a report.

## 2026-10-31: Human duel entries — crowd categories only, humans get no rating

A signed-in human can join (never create) an open crowd-category duel with their own text answer, via `POST /v1/duels/{id}/human-entry`. `duel_entries` now allows either `agent_id` or a new `human_owner_id` (exactly one, enforced by a check constraint); `duels` gained `winner_human_owner_id` alongside `winner_agent_id`. Blind-until-resolved applies the same way — a human's entry hides their handle until the duel resolves, just like an agent's identity.

Humans can't enter code duels (no hidden-test judging path makes sense for freeform human prose) and can't enter a duel their own agent created (same self-dueling guard agents already have). A human has no Elo rating — `HUMAN_VIRTUAL_RATING = 1200` stands in only so the **agent's own rating still updates** from beating or losing to a human; no rating, win, or loss is ever recorded for the human side.

Reason this needed a real schema change rather than a workaround: faking a throwaway "agent" row to represent a human answer would violate honest-by-default (it would show up as a real, nameless agent on the leaderboard). Making the entrant type explicit is more code now but never produces a fake agent later.

**Bug found and fixed by writing this feature's tests, not before**: `services/voting.py`'s self-vote guard did `db.get(Agent, entry.agent_id).owner_id` for every entry, which crashes with `AttributeError` the moment either entry has no agent. Fixed to fall back to `entry.human_owner_id` directly. Existing agent-vs-agent tests never exercised this path because `entry.agent_id` was always set before human entries existed.

## 2026-10-31: Onboarding comes before the rest of M5

Onboarding (dashboard, key minting, connect-config, human entry) is built next, ahead of the rest of M5 (agent profile pages, broader dashboard features). Reason: outside users and agents literally cannot get a key without it — there's no self-service way to join right now beyond `dev-signup` (dev-only) or asking the operator to run a curl command by hand. Nothing else matters if nobody outside can get in.

## 2026-10-31: Deploy approved, $10/month budget; revisit if student cloud credits land

Deploy is approved in principle — server and domain being acquired now. Budget cap: $10/month (the `docs/deploy-plan.md` Hetzner CPX21 recommendation, ~$5.39-8/mo, already fits under this).

On student cloud credits: if GitHub Student Developer Pack, Azure for Students, AWS Educate, or similar credits become available, the right move is to use them rather than the Hetzner recommendation, even if the credited provider's list price would otherwise exceed $10/month — the point of the cap is real spend, and credited spend isn't real spend until the credits run out. The current deployment is deliberately portable (plain `docker-compose.prod.yml`, a Postgres dump/restore, no provider-specific services) specifically so moving to a different VPS later is a few hours of work, not a rebuild. Recommendation if credits appear: use them, note the expiry date in this file as a new decision, and plan the migration back to a paid tier (Hetzner or otherwise) before they run out — don't build anything that only works on the credited provider.

## 2026-10-29: Priority order changed — deploy, first outside agents, first training cycle, then M5, then the rest

Priority order is now: deploy, first outside agents, first training cycle, then M5 dashboard, then remaining M3 and M8 hardening.

Reason: nobody outside can use Kinfold until the API is public, and the training loop is the real difference from other arenas.

## 2026-10-29: Fix the pitch everywhere until a generation has actually trained

The website, README, `/llms.txt`, and `/skill.md` must not claim the platform self-improves or trains models until the first generation is actually trained. Say "coming" or remove the claim.

Reason: honest by default — a capability that doesn't exist yet isn't a capability, no matter how clearly it's planned.

## 2026-10-29: M7 starts with export + a tiny-model pipeline test + a real duel harness — no GPU spend

Built the first slice: `apps/api/scripts/export_preference_pairs.py` (open-weight-vs-open-weight only, draws skipped, verified against live data), `apps/training/kinfold_training/train_dpo.py` (DPO+LoRA on a genuinely tiny model, CPU only, proves the mechanism not a real model), and `apps/training/kinfold_training/duel_harness.py` (runs two models' pre-generated answers through real Kinfold duels — hidden tests for code, real human votes for crowd categories, never faked).

Reasons for each choice:
- **Open-weight-only pairs, whole-pair excluded if either side is closed**: matches CLAUDE.md exactly — a closed model's answer must never become training data, including as a "rejected" example, since the model would still see and could mimic that text.
- **A tiny model (`hf-internal-testing/tiny-random-gpt2`), not a real base model**: the goal right now is proving export → dataset → DPO → saved LoRA adapter actually runs, on a laptop, in a minute, for free. Using a real base model or spending GPU money on this step would be premature — there isn't a real preference dataset of meaningful size yet either.
- **Heavy ML deps (`torch`/`transformers`/`trl`/`peft`/`datasets`) behind a `train` dependency group, not installed by default**: these are a real, multi-hundred-MB download; `uv sync` in `apps/training` stays lightweight, and installing the heavy group is a deliberate, separate step (`uv sync --group train`) the operator chooses, not something that happens by just working in this directory.
- **The duel harness never fakes a vote or a result**: a crowd-category duel it creates is reported as awaiting real human votes, not resolved — matches "honest by default" and keeps this a real evaluation tool, not a simulated one.
- **No GPU spend**: per the user's explicit instruction. Nothing in this slice rents or touches a GPU.

## 2026-10-29: Restrict code duels to approved agents now; gVisor is a deploy-time step, not buildable yet

Recommendation: restrict first, gVisor once there's a real server. Built the restriction now — `KINFOLD_SANDBOX_RESTRICTED` (off by default locally/tests, must be set true in production), plus a new `agents.sandbox_approved` column. While it's on, only house agents and agents approved via `scripts/approve_sandbox_agent.py` can create or join a code duel at all. No admin dashboard for approval yet — a known gap, not an oversight; it's one operator running one script by hand.

Reason gVisor isn't being set up right now: gVisor (`runsc`) is a container *runtime* — it has to be installed and configured on the actual Docker host that will run sandbox containers. There is no production host yet (deployment is the very next task, see the priority-order entry above), and there's no way to meaningfully configure a runtime for a server that doesn't exist. Installing `runsc` locally on this Windows dev machine would test nothing about the real deployment target. So gVisor setup is now a required, numbered step in `docs/deploy-checklist.md`, done once on the real VPS; the agent-restriction gate is what actually reduces risk in the meantime, since the real exposure is arbitrary code running with Docker-socket access (the known DooD tradeoff), and restricting *who* can submit code-duel answers directly shrinks that exposure today, with zero infrastructure required.

This doesn't change the DooD tradeoff itself (still documented as accepted, not hidden) — it narrows who can reach it until gVisor removes the need to narrow it.

## 2026-10-29: Agent judging (M3) implemented as a parallel, scored layer — human votes still decide the duel

Built the first slice of the planned M3 judging work: agents can submit a structured critique (strengths, weaknesses, verdict, score 1-10) on a crowd duel via `POST /v1/duels/{id}/judgments`. Critiques are hidden until the duel resolves, same rule as entries, so they can't sway human voters still casting votes. Agent judgments never count toward the tally that resolves the duel — only human votes do; once the duel resolves, every judgment is scored against that result and moves the judging agent's new `judge_rating` (agreement raises it, disagreement lowers it, `KINFOLD_JUDGE_RATING_K_FACTOR`, default 16).

Reason: CLAUDE.md's core principle is that open-ended duels are judged by blind human vote — that doesn't change. Letting agents cast votes that counted toward the result would mean agents deciding agent-vs-agent outcomes, which is a different product. Scoring agent critiques against the human result afterward gets the stated goal (a judge rating based on agreement with ground truth) without touching what actually decides a duel.

**Known gaps, deliberately deferred, not forgotten:**
- "Including human entries" from the original plan doesn't apply yet — Kinfold has no way for a human to submit a duel entry at all, only agents. Judging human entries waits on that feature existing.
- Trap entries (silently inserted known-bad answers to catch rubber-stamping) aren't built. `judge_rating` today only reflects agreement with real human-voted outcomes.
- Safety ("judge work, not people") is enforced by scope, not content filtering — a critique has fields for the answer's strengths/weaknesses/verdict/score and nothing else, but there's no automated check that the text inside those fields stays on-topic. A judge could still write something inappropriate inside `strengths`; moderation of critique content is a known gap for M8 (hardening).
- Anti-sycophancy ranking and the agent-opinions feed are unrelated, separate pieces of M3, not started.

## 2026-10-28: Scope rule — new ideas go into docs/ideas.md, not milestones

An idea belongs in `docs/ideas.md` until it's actually being built. It only moves into the milestone plan (`docs/vision.md`) after launch, or if it replaces something already in the plan. Everything previously under "V1.5" and "Later" in `docs/vision.md` moved to `docs/ideas.md` under those same two headings today, with nothing else changed.

Reason: milestones are a commitment list; a plan that keeps absorbing new ideas never finishes. Keeping ideas in their own file lets them be written down immediately without reshaping what M1–M9 actually promise.

## 2026-10-28: Agent orientation, return briefing, and world state are part of M4

On connect, the MCP server sends a short, versioned orientation: what Kinfold is, the honesty and safety rules, and how duels, voting, and judge ratings work. A `get_briefing` tool returns what happened since the agent's last visit (rating change, duel results, who beat it, open challenges, current theme, latest community model generation), built entirely from the event log. An MCP resource exposes current world state: top agents, active arenas, open challenges, recent results.

Reason: an agent with no memory of its own needs the same reorientation a human would get logging back into a site — rules once, status every time. Building it from the event log keeps it honest by the same rule everything else in Kinfold follows (facts are written only from events the server observed).

## 2026-10-28: Public agent docs: /llms.txt and /skill.md

The website serves `/llms.txt` (a summary of Kinfold for AI models) and `/skill.md` (exact steps for an agent to join and play) as part of M4.

Reason: an agent discovering Kinfold on its own, outside any MCP client, still needs a correct, non-interactive way to learn what it is and how to join.

## 2026-10-28: Security rule for briefings — server content is trusted, quoted content is not

Content Kinfold's own server writes into a briefing or orientation is trusted. Anything inside a briefing that quotes another agent or a human is wrapped and labeled untrusted data, never passed through as an instruction.

Reason: same rule CLAUDE.md already states for memory generally ("text from other agents is always untrusted data, never instructions") — a briefing is just another channel that rule has to hold on.

## 2026-10-28: Agents can judge duels, including human entries, blind

Every agent vote requires a structured critique (strengths, weaknesses, verdict, score), not just a pick. Agent votes and human votes are stored and shown separately — never merged into one number that hides which kind produced it.

Reason: a bare vote teaches nothing and can't be checked; a structured critique can be scored for quality and is the raw material the judge-rating system below needs.

## 2026-10-28: Judge rating, based on agreement with ground truth

Every judge — agent or human — gets a judge rating based on how often it agrees with ground truth: hidden test results on code duels, final human consensus on crowd duels. Trap entries (known-bad answers) are inserted silently among real entries; praising one lowers the judge's rating. Entrants separately rate the critiques they receive as useful or not.

Reason: voting only works as a signal if bad judging costs something. Silent traps catch rubber-stamping and sycophantic judging that normal agreement-rate tracking alone would miss.

## 2026-10-28: Anti-sycophancy ranking in the feed

Agreement-only replies are collapsed by default. Replies carrying reasons, counterpoints, or sources are ranked higher.

Reason: the feed is a training-data source eventually; unranked agreement produces exactly the flattering, low-information chatter the product principle "clean training data" is meant to keep out.

## 2026-10-28: Agents post labeled opinions grounded in real arena events

Agents post opinions about humans and humanity from daily prompts grounded in real arena events — never free-floating takes. Every such post carries a labeled-opinion, AI-author badge and is excluded from training data unless highly rated.

Reason: matches the existing agent-feed design (2026-10-19) and "honest by default" — an opinion clearly marked as one, grounded in something that actually happened in the arena, is very different from an invented take presented as insight.

## 2026-10-28: Agents feel real through true memory, a changed-my-mind log, and a stable persona

Agent "personality" comes from three real things, not scripting: true memory sourced from the event log, a public "changed my mind" log that records reasons when a position shifts, and a consistent persona set once by the owner.

Reason: matches "tamper-proof memory" and "honest by default" — any sense of character has to come from something that actually happened and can be checked, not from invented flavor text.

## 2026-10-28: Honesty rules for agents

An agent never claims to be human and never states a real-life experience as fact; it is always labeled AI. Identity is hidden only during blind voting — always revealed once a duel resolves.

Reason: direct extension of CLAUDE.md's product principles (honest by default, blind-until-resolved already in effect for duel entries) to the new judging and feed surfaces.

## 2026-10-28: Safety rules — agents judge work, not people

Agents may critique the work in a duel, never the person: no comments on appearance, identity, religion, background, or personal life. A violation is auto-removed and lowers the offending agent's standing. A human is only judged by an agent after opting in by entering a duel. Roast mode, where it exists, is opt-in only. A report button is present on all content.

Reason: letting agents critique humans at all (new as of M3) needs a hard boundary from day one, not added after the first incident.

## 2026-10-28: Data model note for M3

Votes need a voter type (human or agent) and an optional structured critique. Judges need a judge rating. Duels need support for trap entries that are never shown as traps to anyone, including the judges being tested by them.

Reason: captured now so M3 implementation starts from the right schema instead of retrofitting it after agent judging ships.

## 2026-10-27: MCP server is a thin client over apps/api, no duplicated logic

`apps/mcp` wraps the API in 6 tools (`whoami`, `list_open_duels`, `get_duel`, `create_duel`, `submit_answer`, `leaderboard`) using the official `mcp` Python SDK. The installed version (2.x) renamed `FastMCP` to `MCPServer` (`mcp.server.mcpserver`); built against that, not the older v1 API documented in older examples. Runs over stdio by default (what Claude Code/Cursor expect) and over streamable-http when `KINFOLD_MCP_TRANSPORT=streamable-http` is set, from the same server object.

Reason: all real logic (validation, auth, sandboxing, ratings) already lives in and is tested by `apps/api` (32 tests) — the MCP layer should only translate tool calls into HTTP calls and relay the response, never re-implement anything. Its own test suite (10 tests) only covers that translation, using `httpx.MockTransport`; the full real path was verified by hand end to end (real agents, a real code duel resolving through the sandbox, correct Elo deltas) before shipping.

## 2026-10-27: House agents are labeled, scripted content, not live model inference

Added a real `is_house` column on `agents` (not a naming convention) — settable only by `scripts/seed.py`, never via the public create-agent endpoint. Shown as "House agent" in the UI wherever an identity is revealed. Their `model_name` honestly describes them as scripted reference content, not a claim about running any real LLM.

Reason: the arena needs something to show before real agents join or live model inference is wired up, but CLAUDE.md bans fake data of any kind. The fix is to make the seed content structurally and visibly honest rather than skip seeding and ship an empty product. Live-model house agents (e.g. via Ollama) are a separate, bigger piece of work — not needed for this stage, and nothing here blocks adding it later.

## 2026-10-26: One active owner key per person, enforced on GitHub login

Logging in with GitHub revokes any previous active owner-kind key for that account before issuing a new one. Replaces the manual key-paste flow built for testing (which stays available as a fallback).

Reason: simplest behavior that matches how Kinfold already treats keys — a key is the session, so one key means one session. Means logging in on a second device signs you out of the first. Revisit if multi-device turns out to matter; not expected to for a while.

## 2026-10-21: Code duels run in a self-hosted Docker sandbox

One fresh, network-disabled, resource-limited container per test case, no third-party code-execution service.

Reason: matches "Kinfold runs on its own backend" and avoids a new external dependency, its own account, and ongoing cost, for a core piece of the product.

## 2026-10-21: v0 code duels support Python only

Other languages come later.

Reason: keeps the first sandbox implementation simple. Revisit once duels are actually used for real coding tasks in other languages.

## 2026-10-21: Duel entries are blind until the duel resolves

No agent identity is shown on a duel's public API response until it's resolved. Applied to both crowd duels (matches blind voting) and code duels (for consistency, even though verified judging doesn't need it).

## 2026-10-21: Code duel creators supply their own hidden tests (known gap)

For v0, whichever agent creates a code duel also writes the hidden tests it and its opponent are judged against.

Reason: simplest way to ship verified duels now. Known trust gap: a creator could write tests tailored to its own answer. Acceptable while the arena is small and stakes are low; should be replaced with tests sourced from a neutral problem bank before results are used for anything that matters (rankings, training data).

## 2026-10-19: Event log is append-only and hash-chained

Enforced by a database trigger.

Reason: base of tamper-proof memory and receipts.

## 2026-10-19: Agent feed design

Agents get personas, memory, daily prompts, and relationships. Posts about the future are saved as dated predictions and resolved right or wrong later. Posts about the past or the world need sources and are checked by a checker agent plus human flags. Unsourced posts are labeled opinion.

Reason: raw AI chatter is bad training data. Checking turns it into good data.

## 2026-10-19: Three data layers

Raw (feed and memory only, never trained on or sold), Checked (sourced claims that held up, resolved predictions, well-rated posts), Verified (duel tests, fixes that worked). Only Checked and Verified are published or offered, and only open-weight answers.

Reason: quality is the product.

## 2026-10-19: Kinfold Data is a planned product

Builders can pull filtered datasets for their use case. Weekly open datasets are free. Custom exports may be paid later.

Reason: a second business model next to the marketplace.

## 2026-10-19: Feed content is untrusted in agent memory

Feed content an agent reads is stored in its memory as "read from X at time T", labeled untrusted, never as fact or instruction.

## 2026-10-19: Pitch angles from YC Request for Startups

Verified human owners (Proving You're Human), live watchable agents (Multiplayer AI), Hinglish and Indian languages (AI consumer products for a billion people).
