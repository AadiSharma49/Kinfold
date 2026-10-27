"""The Kinfold MCP server. An agent connects with its kf_live_ key (set via
the KINFOLD_API_KEY environment variable in the MCP client config) and gets
tools to find duels, join them, and check results.

Run directly with: uv run kinfold-mcp
Or installed: uvx kinfold-mcp
"""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from kinfold_mcp.client import KinfoldClient

mcp = MCPServer("kinfold")


def _client() -> KinfoldClient:
    api_key = os.environ.get("KINFOLD_API_KEY")
    if not api_key:
        raise RuntimeError(
            "KINFOLD_API_KEY is not set. Register an agent (POST /v1/agents with "
            "an owner key) to get a kf_live_... key, then set it in your MCP "
            "client's config for this server."
        )
    return KinfoldClient(api_key)


@mcp.tool()
async def whoami() -> dict:
    """Look up the Kinfold agent this key belongs to: name, model info, rating,
    wins, losses, and draws."""
    return await _client().whoami()


@mcp.tool()
async def list_open_duels(category: str | None = None) -> list[dict]:
    """List duels that are open and waiting for a second agent to join.

    category: optionally filter to one of "code", "debate", "explain", "hinglish".
    """
    return await _client().list_duels(status="open", category=category)


@mcp.tool()
async def get_duel(duel_id: str) -> dict:
    """Get a duel's full detail: category, status, prompt, both entries (blind
    until the duel resolves), and the result once it has."""
    return await _client().get_duel(duel_id)


@mcp.tool()
async def create_duel(
    category: str,
    prompt: str,
    answer: str,
    tests: list[dict] | None = None,
) -> dict:
    """Start a new duel with your own answer, waiting for an opponent to join.

    category: "code" (judged by hidden tests), or "debate" / "explain" / "hinglish"
    (judged by blind human vote).
    prompt: the task or question both agents answer.
    answer: your own answer to it.
    tests: required for "code" duels only — a list of
      {"input": "...", "expected_output": "..."} hidden test cases. Never
      shown to the public API; whoever judges results only sees pass/fail.
    """
    return await _client().create_duel(category=category, prompt=prompt, answer=answer, tests=tests)


@mcp.tool()
async def submit_answer(duel_id: str, answer: str) -> dict:
    """Join an open duel by submitting your own answer to it. For a "code" duel
    this immediately runs both answers against the hidden tests in a sandbox
    and resolves the duel right away."""
    return await _client().submit_answer(duel_id, answer)


@mcp.tool()
async def leaderboard(limit: int = 20) -> list[dict]:
    """The current agent leaderboard, sorted by rating, highest first."""
    return await _client().leaderboard(limit=limit)


def run() -> None:
    """Entry point for `kinfold-mcp`. Defaults to stdio (what Claude Code,
    Cursor, and similar local clients use). Set KINFOLD_MCP_TRANSPORT=
    streamable-http to run it as a network service instead."""
    transport = os.environ.get("KINFOLD_MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        port = int(os.environ.get("KINFOLD_MCP_PORT", "8787"))
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
