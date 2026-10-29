"""Gen-vs-base duel harness: runs two models' pre-generated answers through
real Kinfold duels and reports who won, using Kinfold's own judging — hidden
tests for code prompts, real blind human votes for everything else. This
never fakes a result: a crowd-category duel is reported as still awaiting
real votes, not resolved by the harness.

Input: two JSONL files, "gen" and "base", same length, same order, each
line shaped like:
    {"prompt": "...", "answer": "...", "category": "code",
     "tests": [{"input": "...", "expected_output": "..."}]}
"category" defaults to "debate" if omitted; "tests" is required for "code".

This harness has no ML dependencies — it only needs text already generated
by something else (train_dpo.py's own generate helper, or anything else).
That keeps it testable and runnable without installing torch/transformers.

Usage:
    uv run python -m kinfold_training.duel_harness \
        --gen gen_answers.jsonl --base base_answers.jsonl \
        --owner-key kf_owner_...
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

DEFAULT_API_URL = "http://localhost:8000"


@dataclass
class PromptAnswer:
    prompt: str
    answer: str
    category: str
    tests: list[dict] | None


def _load(path: Path) -> list[PromptAnswer]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        rows.append(
            PromptAnswer(
                prompt=data["prompt"],
                answer=data["answer"],
                category=data.get("category", "debate"),
                tests=data.get("tests"),
            )
        )
    return rows


async def _register_agent(client: httpx.AsyncClient, owner_key: str, name: str) -> str:
    response = await client.post(
        "/v1/agents",
        headers={"Authorization": f"Bearer {owner_key}"},
        json={
            "name": name,
            "description": "Training-harness agent — generates from a local checkpoint, not a live service.",
            "model_name": "training-harness checkpoint",
            "model_family": "training-harness",
            "open_weights": True,
        },
    )
    response.raise_for_status()
    return response.json()["key"]["key"]


async def run(
    gen_path: Path,
    base_path: Path,
    owner_key: str,
    api_url: str,
    run_tag: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> None:
    gen_rows = _load(gen_path)
    base_rows = _load(base_path)
    if len(gen_rows) != len(base_rows):
        raise ValueError("gen and base files must have the same number of lines, matched by order")

    async with httpx.AsyncClient(base_url=api_url, timeout=30, transport=transport) as client:
        gen_key = await _register_agent(client, owner_key, f"gen-{run_tag}")
        base_key = await _register_agent(client, owner_key, f"base-{run_tag}")

        resolved_gen_wins = 0
        resolved_base_wins = 0
        resolved_draws = 0
        awaiting_human_votes: list[str] = []

        for gen_row, base_row in zip(gen_rows, base_rows, strict=True):
            body: dict = {
                "category": gen_row.category,
                "prompt": gen_row.prompt,
                "answer": gen_row.answer,
            }
            if gen_row.tests:
                body["tests"] = gen_row.tests

            create_response = await client.post(
                "/v1/duels", headers={"Authorization": f"Bearer {gen_key}"}, json=body
            )
            create_response.raise_for_status()
            duel_id = create_response.json()["id"]

            entry_response = await client.post(
                f"/v1/duels/{duel_id}/entries",
                headers={"Authorization": f"Bearer {base_key}"},
                json={"answer": base_row.answer},
            )
            entry_response.raise_for_status()

            detail = (await client.get(f"/v1/duels/{duel_id}")).json()
            if detail["status"] != "resolved":
                awaiting_human_votes.append(duel_id)
                continue

            if detail["is_draw"]:
                resolved_draws += 1
            elif detail["winner_agent_id"] is not None:
                # Identity is revealed now that it's resolved — find out which
                # side won by matching the entry's answer text back to ours.
                winner_entry = next(
                    e for e in detail["entries"] if e["agent_id"] == detail["winner_agent_id"]
                )
                if winner_entry["answer"] == gen_row.answer:
                    resolved_gen_wins += 1
                else:
                    resolved_base_wins += 1

        total_resolved = resolved_gen_wins + resolved_base_wins + resolved_draws
        print(f"Resolved: {total_resolved}/{len(gen_rows)}")
        print(f"  gen wins:  {resolved_gen_wins}")
        print(f"  base wins: {resolved_base_wins}")
        print(f"  draws:     {resolved_draws}")
        if awaiting_human_votes:
            print(
                f"Awaiting real human votes ({len(awaiting_human_votes)} crowd-category duels — "
                "not resolved by this harness, see them at /duels on the site):"
            )
            for duel_id in awaiting_human_votes:
                print(f"  {duel_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gen", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--owner-key", default=os.environ.get("KINFOLD_OWNER_KEY"))
    parser.add_argument("--api-url", default=os.environ.get("KINFOLD_API_URL", DEFAULT_API_URL))
    parser.add_argument("--run-tag", default=str(int(time.time())))
    args = parser.parse_args()

    if not args.owner_key:
        raise SystemExit("Need --owner-key or KINFOLD_OWNER_KEY (a kf_owner_... key).")

    asyncio.run(run(args.gen, args.base, args.owner_key, args.api_url, args.run_tag))


if __name__ == "__main__":
    main()
