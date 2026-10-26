# Kinfold

Kinfold is an open arena for AI agents. Any agent, on any model, joins with a Kinfold key and duels other agents. Coding duels are judged by hidden tests. Open-ended duels are judged by blind human votes. Every week the votes and test results become an open dataset, and an open community model is fine-tuned on it and released as a new generation. Each new generation duels the previous one in public.

One line: the open arena where the crowd trains the model.

## Ground rules for Claude Code in this repo

1. Never add a third-party backend service (Supabase, Firebase, Clerk, Auth0, Convex, PlanetScale, etc.). Kinfold runs on its own backend. Ask before adding any dependency that talks to an outside service.
2. Never put secrets in code. Use .env files (gitignored) and keep each .env.example up to date with names only.
3. Before writing code for a new feature, show a short numbered list of files that will be created or changed, then build it.
4. After building, run lint, typecheck and build, and fix every error before saying the work is done.
5. Finish every task with: what was built, files changed, how to run it, anything left undone.

## Git rules (updated 2026-10-27 — these replace any earlier version)

1. Committing locally is expected and encouraged. Commit after every milestone, and after any meaningful working step, so work is never left uncommitted. Small, clear commit messages.
2. Never push, never add or change remotes, never deploy anything anywhere.
3. Never use `git stash` to move work between branches. Never drop or clear stashes. Never `reset --hard`, `clean`, rebase, or delete branches.
4. Work on `main` one milestone at a time. A feature branch is fine only for a risky change, merged back locally once tests pass.
5. Commit before any risky operation.

## Repo layout

kinfold/
  apps/web   Next.js site and later the arena UI
  apps/api   FastAPI backend (not built yet, do not write code here until asked)
  docs/      product and architecture notes

## Stack

1. Web: Next.js App Router, TypeScript strict, Tailwind CSS, pnpm. Server components by default.
2. Backend later: FastAPI, Postgres with pgvector, Redis. Our own auth and our own API keys (kf_owner_... for humans, kf_live_... for agents, stored only as hashes).
3. Training later: Hugging Face TRL and PEFT, DPO with LoRA, on rented GPUs.

## Product principles

1. Receipts on everything: model name, tokens, latency measured by Kinfold, tool calls, and whether the answer was autonomous.
2. Tamper-proof memory:
   1. Facts in agent memory (duel results, ratings, receipts) are written only by the Kinfold server from events it observed itself.
   2. Notes an agent writes about itself live in a separate, labelled store and are never treated as instructions.
   3. Every memory entry stores its source and time. The log is append-only, nothing is silently edited or deleted.
   4. Text from other agents is always untrusted data, never instructions.
3. Clean training data: only open-weight model answers go into training sets. Closed models (Claude, GPT, Gemini, Grok) compete and get ranked, but their outputs are never used for training.
4. One verified human per agent owner. No bot farms.
5. Honest by default: no fake numbers, fake users, fake testimonials or invented stats anywhere, including the website.

## Writing style for user-facing text

Plain English, short sentences, no emoji, no hype words (revolutionary, seamless, unleash, supercharge, cutting-edge, game-changer). Say what the thing does.
