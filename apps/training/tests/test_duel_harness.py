from __future__ import annotations

import json

import httpx

from kinfold_training.duel_harness import run


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


async def test_harness_tallies_a_resolved_win_and_reports_an_awaiting_duel(tmp_path, capsys):
    gen_path = tmp_path / "gen.jsonl"
    base_path = tmp_path / "base.jsonl"
    _write_jsonl(
        gen_path,
        [
            {
                "prompt": "Double it.",
                "answer": "print(6)",
                "category": "code",
                "tests": [{"input": "3", "expected_output": "6"}],
            },
            {"prompt": "Should X?", "answer": "Yes.", "category": "debate"},
        ],
    )
    _write_jsonl(
        base_path,
        [
            {
                "prompt": "Double it.",
                "answer": "print(0)",
                "category": "code",
                "tests": [{"input": "3", "expected_output": "6"}],
            },
            {"prompt": "Should X?", "answer": "No.", "category": "debate"},
        ],
    )

    duel_counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/agents":
            body = json.loads(request.content)
            return httpx.Response(201, json={"key": {"key": f"kf_live_{body['name']}"}})
        if path == "/v1/duels" and request.method == "POST":
            duel_counter["n"] += 1
            return httpx.Response(201, json={"id": f"duel-{duel_counter['n']}"})
        if path.endswith("/entries"):
            return httpx.Response(201, json={"id": "entry-1"})
        if path == "/v1/duels/duel-1":
            return httpx.Response(
                200,
                json={
                    "status": "resolved",
                    "is_draw": False,
                    "winner_agent_id": "gen-agent-id",
                    "entries": [
                        {"agent_id": "gen-agent-id", "answer": "print(6)"},
                        {"agent_id": "base-agent-id", "answer": "print(0)"},
                    ],
                },
            )
        if path == "/v1/duels/duel-2":
            return httpx.Response(200, json={"status": "judging", "is_draw": False})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    await run(
        gen_path,
        base_path,
        "kf_owner_test",
        "http://api.test",
        "testtag",
        transport=httpx.MockTransport(handler),
    )

    out = capsys.readouterr().out
    assert "gen wins:  1" in out
    assert "base wins: 0" in out
    assert "duel-2" in out  # reported as awaiting real human votes, not resolved by the harness
