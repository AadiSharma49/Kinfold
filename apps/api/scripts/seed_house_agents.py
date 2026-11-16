"""Seed script: 5 house agents on real, open-weight models served by
Groq's OpenAI-compatible chat API — see docs/decisions.md, 2026-11-16.

Run with:
    uv run python scripts/seed_house_agents.py

Idempotent — safe to re-run: skips any agent or duel that already exists.

Each agent is created with is_house=True and sandbox_approved=True, so
all five can submit code-duel answers while KINFOLD_SANDBOX_RESTRICTED
is on, with no separate manual approval step (is_house alone already
grants sandbox access — sandbox_approved is set too because the task
asked for it explicitly, and it does no harm).

GROQ_API_KEY is read directly from the environment, not from Settings —
it is a script-only secret the running server never needs. Get a free
key at console.groq.com/keys. If it is not set, this script still
creates the 5 agents, but prints a clear message and makes no live call
and seeds no duel — never a fabricated answer standing in for a real one.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import NamedTuple

import httpx
from sqlalchemy import select

from kinfold_api.db import SessionLocal
from kinfold_api.models import Agent, Duel, Owner
from kinfold_api.services.agents import create_agent_with_key
from kinfold_api.services.duels import create_duel, submit_entry
from kinfold_api.services.events import append_event
from kinfold_api.services.receipts import ReceiptIn

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model ids checked against Groq's own model/deprecation docs on
# 2026-11-16, not assumed — see docs/decisions.md. All five are
# genuinely open-weight: Meta (Llama, Apache-ish Llama license),
# Alibaba (Qwen, Apache-2.0), and OpenAI's gpt-oss line specifically
# (Apache-2.0 — distinct from OpenAI's closed GPT models).
HOUSE_AGENTS = [
    {
        "name": "house-llama-70b",
        "model_name": "llama-3.3-70b-versatile",
        "model_family": "llama",
        "description": (
            "Kinfold house agent. Answers are generated live by Meta's "
            "Llama 3.3 70B, served by Groq — real model inference, not "
            "scripted."
        ),
    },
    {
        "name": "house-llama-8b",
        "model_name": "llama-3.1-8b-instant",
        "model_family": "llama",
        "description": (
            "Kinfold house agent. Answers are generated live by Meta's "
            "Llama 3.1 8B, served by Groq — real model inference, not "
            "scripted."
        ),
    },
    {
        "name": "house-qwen-27b",
        "model_name": "qwen/qwen3.8-27b",
        "model_family": "qwen",
        "description": (
            "Kinfold house agent. Answers are generated live by Alibaba's "
            "Qwen3.8 27B, served by Groq — real model inference, not "
            "scripted."
        ),
    },
    {
        "name": "house-gptoss-120b",
        "model_name": "openai/gpt-oss-120b",
        "model_family": "gpt-oss",
        "description": (
            "Kinfold house agent. Answers are generated live by OpenAI's "
            "open-weight gpt-oss-120b, served by Groq — real model "
            "inference, not scripted."
        ),
    },
    {
        "name": "house-gptoss-20b",
        "model_name": "openai/gpt-oss-20b",
        "model_family": "gpt-oss",
        "description": (
            "Kinfold house agent. Answers are generated live by OpenAI's "
            "open-weight gpt-oss-20b, served by Groq — real model "
            "inference, not scripted."
        ),
    },
]

CODE_DUEL_SYSTEM_PROMPT = (
    "You are competing in a coding duel. Reply with ONLY the Python source "
    "code that solves the task, reading input with input() and printing "
    "the answer with print(). No explanation, no markdown code fences, no "
    "comments."
)

# Real tasks with real hidden tests. Each pairs two of the five house
# agents so every agent gets at least one live, hidden-test-judged duel.
CODE_DUEL_TASKS = [
    {
        "prompt": "Read two integers on one line, separated by a space, and print their product.",
        "tests": [
            {"input": "6 7", "expected_output": "42"},
            {"input": "-3 5", "expected_output": "-15"},
        ],
        "agent_a": "house-llama-70b",
        "agent_b": "house-qwen-27b",
    },
    {
        "prompt": "Read a single integer n and print the sum of all integers from 1 to n.",
        "tests": [
            {"input": "5", "expected_output": "15"},
            {"input": "100", "expected_output": "5050"},
        ],
        "agent_a": "house-gptoss-120b",
        "agent_b": "house-llama-8b",
    },
    {
        "prompt": "Read a single word and print it in uppercase.",
        "tests": [{"input": "kinfold", "expected_output": "KINFOLD"}],
        "agent_a": "house-gptoss-20b",
        "agent_b": "house-qwen-27b",
    },
]

_FENCE_RE = re.compile(r"^```[a-zA-Z0-9]*\n(.*)\n```$", re.DOTALL)


def strip_code_fences(text: str) -> str:
    """Models often wrap code in ```python ... ``` even when told not to.
    Strips a single leading/trailing fenced block if present; otherwise
    returns the text unchanged. Pure, no network — testable on its own."""
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    return match.group(1) if match else stripped


class GroqAnswer(NamedTuple):
    code: str
    tokens_in: int | None
    tokens_out: int | None


def generate_code_answer(
    client: httpx.Client, *, api_key: str, model: str, prompt: str
) -> GroqAnswer:
    """Calls Groq's OpenAI-compatible chat completions endpoint for a real
    model answer to a real duel task. Raises on a non-2xx response or a
    malformed body — callers decide how to handle that; this never
    fabricates a fallback answer. `client` is injectable so tests can pass
    one built on httpx.MockTransport instead of hitting the real network.
    tokens_in/tokens_out come straight from Groq's own `usage` field — a
    real receipt, not an invented one."""
    response = client.post(
        GROQ_CHAT_COMPLETIONS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": CODE_DUEL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    code = strip_code_fences(data["choices"][0]["message"]["content"])
    usage = data.get("usage") or {}
    return GroqAnswer(
        code=code,
        tokens_in=usage.get("prompt_tokens"),
        tokens_out=usage.get("completion_tokens"),
    )


def get_or_create_owner(db, handle: str) -> Owner:
    owner = db.execute(select(Owner).where(Owner.handle == handle)).scalar_one_or_none()
    if owner is not None:
        return owner

    owner = Owner(handle=handle)
    db.add(owner)
    db.flush()
    append_event(
        db, type="owner.created", owner_id=owner.id, payload={"handle": owner.handle, "via": "seed"}
    )
    db.commit()
    db.refresh(owner)
    print(f"created house owner: {owner.handle}")
    return owner


def get_or_create_groq_house_agents(db) -> dict[str, Agent]:
    """Each house agent gets its own owner account (`house-owner-<name>`),
    not one shared owner. Two agents under the same owner can't duel each
    other (services/duels.py's owner-separation rule) — one shared house
    owner would make every house-vs-house duel below impossible. See
    docs/decisions.md, 2026-11-16."""
    agents: dict[str, Agent] = {}
    for spec in HOUSE_AGENTS:
        existing = db.execute(select(Agent).where(Agent.name == spec["name"])).scalar_one_or_none()
        if existing is not None:
            agents[spec["name"]] = existing
            continue

        owner = get_or_create_owner(db, f"house-owner-{spec['name']}")
        agent, _api_key, raw_key = create_agent_with_key(
            db,
            owner=owner,
            name=spec["name"],
            description=spec["description"],
            model_name=spec["model_name"],
            model_family=spec["model_family"],
            open_weights=True,
            is_house=True,
        )
        agent.sandbox_approved = True
        db.flush()
        append_event(
            db,
            type="agent.sandbox_approved",
            agent_id=agent.id,
            owner_id=owner.id,
            payload={"agent_name": agent.name, "via": "seed_house_agents"},
        )
        db.commit()
        db.refresh(agent)
        print(f"created house agent: {agent.name} ({spec['model_name']}, key: {raw_key})")
        agents[spec["name"]] = agent
    return agents


def seed_live_code_duels(
    db, agents: dict[str, Agent], *, api_key: str, client: httpx.Client | None = None
) -> None:
    """Each task: agent_a creates the duel with a real generated answer,
    agent_b joins with its own. A code duel resolves immediately against
    the hidden tests, so this either produces a real win/loss or (if a
    Groq call fails partway) leaves the duel for a later real opponent —
    never a guessed or scripted stand-in answer. `client` is injectable
    (tests pass one built on httpx.MockTransport); the default opens and
    closes a real one."""
    owns_client = client is None
    client = client or httpx.Client()
    try:
        for task in CODE_DUEL_TASKS:
            if db.execute(select(Duel).where(Duel.prompt == task["prompt"])).scalar_one_or_none():
                continue
            agent_a = agents[task["agent_a"]]
            agent_b = agents[task["agent_b"]]

            started_a = datetime.now(UTC)
            try:
                answer_a = generate_code_answer(
                    client, api_key=api_key, model=agent_a.model_name, prompt=task["prompt"]
                )
            except httpx.HTTPError as exc:
                print(f"Groq call failed for {agent_a.name}: {exc}. Skipping this task.")
                continue

            duel = create_duel(
                db,
                creator_agent=agent_a,
                category="code",
                prompt=task["prompt"],
                answer=answer_a.code,
                tests=[(t["input"], t["expected_output"]) for t in task["tests"]],
                receipt=ReceiptIn(
                    tokens_in=answer_a.tokens_in,
                    tokens_out=answer_a.tokens_out,
                    autonomous=True,
                    started_at=started_a,
                ),
            )

            started_b = datetime.now(UTC)
            try:
                answer_b = generate_code_answer(
                    client, api_key=api_key, model=agent_b.model_name, prompt=task["prompt"]
                )
            except httpx.HTTPError as exc:
                print(
                    f"Groq call failed for {agent_b.name}: {exc}. "
                    "Duel created and left open for a real opponent."
                )
                continue

            submit_entry(
                db,
                duel=duel,
                agent=agent_b,
                answer=answer_b.code,
                receipt=ReceiptIn(
                    tokens_in=answer_b.tokens_in,
                    tokens_out=answer_b.tokens_out,
                    autonomous=True,
                    started_at=started_b,
                ),
            )
            print(f"seeded live code duel ({agent_a.name} vs {agent_b.name}): {task['prompt'][:60]}")
    finally:
        if owns_client:
            client.close()


def main() -> None:
    db = SessionLocal()
    try:
        agents = get_or_create_groq_house_agents(db)

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            print(
                "GROQ_API_KEY is not set — created the 5 house agents, but "
                "skipping every live Groq call and duel seed. Set "
                "GROQ_API_KEY (see apps/api/.env.example) and re-run to "
                "seed real duels between them."
            )
            return

        seed_live_code_duels(db, agents, api_key=api_key)
        print("seed_house_agents complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()
