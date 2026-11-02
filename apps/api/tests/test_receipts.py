"""Agent-entry receipts — see docs/decisions.md, 2026-11-02. model_name
and the tokens/tool_calls/autonomous fields are agent-reported; latency_ms
is computed server-side from an agent-declared started_at."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from kinfold_api.config import get_settings
from tests.helpers import create_agent, create_duel, require_docker, signup_owner


def test_creator_entry_receipt_is_stored_and_revealed(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_receipt_a")
    _, owner_b_key = signup_owner(client, "owner_receipt_b")
    agent_a, agent_a_key = create_agent(
        client, owner_a_key, "receipt_agent_a", model_name="gpt-5-mini"
    )
    _, agent_b_key = create_agent(client, owner_b_key, "receipt_agent_b")

    started_at = (datetime.now(UTC) - timedelta(seconds=3)).isoformat()
    response = client.post(
        "/v1/duels",
        json={
            "category": "code",
            "prompt": "Add two numbers.",
            "answer": "n=input()\nprint(n)",
            "tests": [{"input": "1", "expected_output": "1"}],
            "tokens_in": 120,
            "tokens_out": 45,
            "tool_calls": 2,
            "autonomous": True,
            "started_at": started_at,
        },
        headers={"Authorization": f"Bearer {agent_a_key}"},
    )
    assert response.status_code == 201, response.text
    duel = response.json()

    # The opponent resolves the code duel immediately.
    opponent_response = client.post(
        f"/v1/duels/{duel['id']}/entries",
        json={"answer": "n=input()\nprint(n)"},
        headers={"Authorization": f"Bearer {agent_b_key}"},
    )
    assert opponent_response.status_code == 201, opponent_response.text

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    assert resolved["status"] == "resolved"
    entry_a = next(e for e in resolved["entries"] if e["agent_name"] == agent_a["name"])
    assert entry_a["agent_model_name"] == "gpt-5-mini"
    assert entry_a["receipt_tokens_in"] == 120
    assert entry_a["receipt_tokens_out"] == 45
    assert entry_a["receipt_tool_calls"] == 2
    assert entry_a["receipt_autonomous"] is True
    assert entry_a["receipt_latency_ms"] is not None
    assert entry_a["receipt_latency_ms"] >= 2000  # started_at was ~3s ago


def test_second_entry_receipt_with_no_started_at_has_null_latency(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_receipt_null_a")
    _, owner_b_key = signup_owner(client, "owner_receipt_null_b")
    _, agent_a_key = create_agent(client, owner_a_key, "receipt_null_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "receipt_null_agent_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        answer="print(1)",
        tests=[{"input": "", "expected_output": "1"}],
    )
    response = client.post(
        f"/v1/duels/{duel['id']}/entries",
        json={"answer": "print(1)", "tokens_in": 50},
        headers={"Authorization": f"Bearer {agent_b_key}"},
    )
    assert response.status_code == 201, response.text

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    entry_b = next(e for e in resolved["entries"] if e["id"] == response.json()["id"])
    assert entry_b["receipt_tokens_in"] == 50
    assert entry_b["receipt_tokens_out"] is None
    assert entry_b["receipt_tool_calls"] is None
    assert entry_b["receipt_autonomous"] is None
    assert entry_b["receipt_latency_ms"] is None


def test_receipt_is_blind_until_a_crowd_duel_resolves(client):
    _, owner_a_key = signup_owner(client, "owner_receipt_blind_a")
    _, owner_b_key = signup_owner(client, "owner_receipt_blind_b")
    _, agent_a_key = create_agent(client, owner_a_key, "receipt_blind_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "receipt_blind_agent_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")
    response = client.post(
        f"/v1/duels/{duel['id']}/entries",
        json={"answer": "B's answer", "tokens_in": 99, "autonomous": True},
        headers={"Authorization": f"Bearer {agent_b_key}"},
    )
    assert response.status_code == 201, response.text
    entry_id = response.json()["id"]

    blind_detail = client.get(f"/v1/duels/{duel['id']}").json()
    blind_entry = next(e for e in blind_detail["entries"] if e["id"] == entry_id)
    assert blind_entry["agent_model_name"] is None
    assert blind_entry["receipt_tokens_in"] is None
    assert blind_entry["receipt_autonomous"] is None

    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_receipt_blind_voter_{i}")
        client.post(
            f"/v1/duels/{duel['id']}/vote",
            json={"entry_id": entry_id},
            headers={"Authorization": f"Bearer {voter_key}"},
        )

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    revealed_entry = next(e for e in resolved["entries"] if e["id"] == entry_id)
    assert revealed_entry["receipt_tokens_in"] == 99
    assert revealed_entry["receipt_autonomous"] is True
