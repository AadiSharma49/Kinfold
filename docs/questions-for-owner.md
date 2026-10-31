# Questions for the owner

Judgment calls made while working autonomously, so they're reviewable and reversible. Newest at the top.

## 2026-10-31: "Rating per category" and "receipts" on agent profiles — scoped to what's real

**Question:** Item 4 asks for agent profiles with "rating per category" and "duel history with receipts." Kinfold only tracks one overall Elo rating per agent (not a separate Elo per category) — building true per-category Elo would mean a new table and changing how every duel resolution writes ratings, a bigger change than a profile page. Separately, CLAUDE.md's "receipts on everything" (model, tokens, latency, tool calls, autonomous) was never actually implemented for agent duel entries anywhere in the codebase — only this session's new human-entry receipt (time taken, declared AI tools) is real. Building full agent receipts would mean the API accepting that data on submission, which it doesn't today.

**Choice:** "Rating per category" on the agent profile is a real win/loss/draw record broken out by category (code, debate, explain, hinglish), computed from actual duel history — not a fabricated separate Elo number per category. The one real Elo rating and judge rating are both shown once, same as the leaderboard. "Receipts" on agent duel history show whatever's genuinely tracked today: timestamp and, for code duels, the real pass/fail test count — nothing invented. A human's duel history shows their real receipt (time taken, declared AI tools) since that part was actually built this session.

**To change it later:** per-category Elo and full agent receipts (tokens/latency/tool-calls) are both real, buildable features — they just need their own schema work (a rating-history table; the submit-entry endpoints accepting receipt metadata) rather than being retrofitted into a profile-page task. Worth a dedicated queue item if wanted.

## 2026-10-31: Branch naming for items already in progress

**Question:** The autonomous-mode instructions say every queue item gets its own `feature/<short-name>` branch. Items 1 (onboarding) and 2 (human-entry) were already partway done on a branch named `onboarding-slice`, created just before autonomous mode started.

**Choice:** Finished items 1 and 2 on `onboarding-slice` rather than restarting on `feature/onboarding` / `feature/human-entry`, to avoid throwing away committed work. Every queue item from here on (3 onward) uses the `feature/<short-name>` naming exactly as instructed.

**To change it later:** if you want items 1/2 split into separate `feature/`-named branches retroactively, that's a `git branch -m` rename or a cherry-pick — ask and it's a small job, not a rebuild.
