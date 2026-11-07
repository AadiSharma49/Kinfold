"""Start the real stdio server and check what it advertises.

The client tests mock the HTTP transport; this one runs the actual
`kinfold-mcp` entry point as an MCP client would, over stdio, and reads
back the tool list. No Kinfold API is contacted — initialize and
tools/list never call the HTTP client.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

EXPECTED_TOOLS = {
    "whoami",
    "list_open_duels",
    "get_duel",
    "create_duel",
    "submit_answer",
    "leaderboard",
    "get_briefing",
    "judge_duel",
    "get_judgments",
    "rate_judgment_useful",
}


def _server_params() -> StdioServerParameters:
    # Prefer the installed console script, because that is what uvx and
    # npx end up running; fall back to the module for environments where
    # the script is not on PATH.
    exe = shutil.which("kinfold-mcp")
    command = exe if exe else sys.executable
    args: list[str] = [] if exe else ["-m", "kinfold_mcp.server"]
    return StdioServerParameters(
        command=command,
        args=args,
        env={**os.environ, "KINFOLD_API_KEY": "kf_live_test"},
    )


async def _list_tools() -> set[str]:
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
    return {tool.name for tool in result.tools}


async def test_stdio_server_lists_ten_tools() -> None:
    names = await asyncio.wait_for(_list_tools(), timeout=30)

    assert names == EXPECTED_TOOLS
    assert len(names) == 10
