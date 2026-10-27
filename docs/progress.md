# Progress log

One entry per milestone: date, what got built, what's left, anything risky. Newest at the top.

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
