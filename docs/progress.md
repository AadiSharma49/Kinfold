# Progress log

One entry per milestone: date, what got built, what's left, anything risky. Newest at the top.

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
