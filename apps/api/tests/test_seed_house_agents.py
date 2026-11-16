"""scripts/seed_house_agents.py — see docs/decisions.md, 2026-11-16.
Every test here mocks the Groq call (httpx.MockTransport); none needs a
real GROQ_API_KEY. The full live-duel path still needs Docker for the
sandbox, same as any other code-duel test."""

from __future__ import annotations

import json

import httpx
import pytest
from sqlalchemy import select

from kinfold_api.models import Agent, Duel
from scripts.seed_house_agents import (
    CODE_DUEL_TASKS,
    HOUSE_AGENTS,
    GroqAnswer,
    generate_code_answer,
    get_or_create_groq_house_agents,
    seed_live_code_duels,
    strip_code_fences,
)
from tests.helpers import require_docker


def test_strip_code_fences_removes_a_fenced_block():
    text = "```python\nprint('hi')\n```"
    assert strip_code_fences(text) == "print('hi')"


def test_strip_code_fences_removes_a_fence_with_no_language_tag():
    text = "```\nprint(1)\n```"
    assert strip_code_fences(text) == "print(1)"


def test_strip_code_fences_leaves_unfenced_text_unchanged():
    text = "print('no fence here')"
    assert strip_code_fences(text) == text


def test_strip_code_fences_strips_surrounding_whitespace():
    text = "\n\n  print(1)  \n\n"
    assert strip_code_fences(text) == "print(1)"


def _mock_groq_transport(reply_code: str, *, tokens_in: int = 42, tokens_out: int = 7):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": reply_code}}],
                "usage": {"prompt_tokens": tokens_in, "completion_tokens": tokens_out},
            },
        )

    return httpx.MockTransport(handler), captured


def test_generate_code_answer_sends_the_right_request_and_parses_usage():
    transport, captured = _mock_groq_transport("```python\nprint(1)\n```")

    with httpx.Client(transport=transport) as client:
        result = generate_code_answer(
            client, api_key="test-key", model="llama-3.3-70b-versatile", prompt="do a thing"
        )

    assert result == GroqAnswer(code="print(1)", tokens_in=42, tokens_out=7)
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    assert captured["body"]["model"] == "llama-3.3-70b-versatile"
    assert captured["body"]["messages"][1]["content"] == "do a thing"


def test_generate_code_answer_raises_on_an_error_response_rather_than_fabricating():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid api key"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            generate_code_answer(client, api_key="bad-key", model="llama-3.3-70b-versatile", prompt="x")


def test_house_agents_are_created_house_sandbox_approved_and_open_weight(db_session):
    agents = get_or_create_groq_house_agents(db_session)

    assert set(agents.keys()) == {spec["name"] for spec in HOUSE_AGENTS}
    for spec in HOUSE_AGENTS:
        agent = agents[spec["name"]]
        assert agent.is_house is True
        assert agent.sandbox_approved is True
        assert agent.open_weights is True
        assert agent.model_name == spec["model_name"]
        assert agent.model_family == spec["model_family"]
        assert "real model inference" in agent.description


def test_seeding_house_agents_twice_does_not_duplicate_them(db_session):
    get_or_create_groq_house_agents(db_session)
    get_or_create_groq_house_agents(db_session)

    count = db_session.execute(
        select(Agent).where(Agent.name.in_([spec["name"] for spec in HOUSE_AGENTS]))
    ).scalars().all()
    assert len(count) == len(HOUSE_AGENTS)


def test_seed_live_code_duels_resolves_a_real_duel_from_mocked_groq_answers(db_session):
    require_docker()
    agents = get_or_create_groq_house_agents(db_session)

    # First task is house-llama-70b vs house-qwen-27b, product of two ints.
    # Correct answer for both, so it should resolve as a draw rather than
    # erroring, and both entries should carry a real (mocked) receipt.
    correct = "a, b = map(int, input().split())\nprint(a * b)"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": correct}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        seed_live_code_duels(db_session, agents, api_key="test-key", client=client)

    duel = db_session.execute(
        select(Duel).where(
            Duel.prompt == "Read two integers on one line, separated by a space, and print their product."
        )
    ).scalar_one()
    assert duel.status == "resolved"
    assert duel.is_draw is True  # both sides submitted the same correct answer


def test_seed_live_code_duels_is_idempotent(db_session):
    require_docker()
    agents = get_or_create_groq_house_agents(db_session)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "print(input())"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        seed_live_code_duels(db_session, agents, api_key="test-key", client=client)
        seed_live_code_duels(db_session, agents, api_key="test-key", client=client)

    duels = db_session.execute(
        select(Duel).where(Duel.prompt.in_([t["prompt"] for t in CODE_DUEL_TASKS]))
    ).scalars().all()
    assert len(duels) == len(CODE_DUEL_TASKS)  # one per task, not doubled
