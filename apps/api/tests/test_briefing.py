from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry


def _briefing(client, agent_key: str) -> dict:
    response = client.get(
        "/v1/agents/me/briefing", headers={"Authorization": f"Bearer {agent_key}"}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_briefing_with_no_history_is_empty_but_honest(client):
    _, owner_key = signup_owner(client, "owner_briefing_empty")
    _, agent_key = create_agent(client, owner_key, "briefing_empty_agent")

    body = _briefing(client, agent_key)

    assert body["since"] is None
    assert body["results"] == []
    assert body["rating_change"] == 0
    assert body["current_theme"] is None
    assert body["latest_generation"] is None
    assert isinstance(body["open_challenges"], int)


def test_briefing_reports_a_resolved_code_duel(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_briefing_a")
    _, owner_b_key = signup_owner(client, "owner_briefing_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "briefing_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "briefing_agent_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        prompt="Return the input unchanged.",
        answer="import sys\nprint(sys.stdin.read(), end='')",
        tests=[{"input": "hi", "expected_output": "hi"}],
    )
    submit_entry(client, agent_b_key, duel["id"], "print('wrong')")

    body = _briefing(client, agent_a_key)

    assert len(body["results"]) == 1
    result = body["results"][0]
    assert result["duel_id"] == duel["id"]
    assert result["outcome"] == "win"
    assert result["rating_delta"] > 0
    assert result["opponent_name"] == "briefing_agent_b"
    assert body["rating_change"] == result["rating_delta"]
    assert body["rating"] == agent_a["rating"] + result["rating_delta"]


def test_briefing_does_not_repeat_already_seen_results(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_briefing_repeat_a")
    _, owner_b_key = signup_owner(client, "owner_briefing_repeat_b")
    _, agent_a_key = create_agent(client, owner_a_key, "briefing_repeat_a")
    _, agent_b_key = create_agent(client, owner_b_key, "briefing_repeat_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        prompt="Return the input unchanged.",
        answer="import sys\nprint(sys.stdin.read(), end='')",
        tests=[{"input": "hi", "expected_output": "hi"}],
    )
    submit_entry(client, agent_b_key, duel["id"], "print('wrong')")

    first = _briefing(client, agent_a_key)
    assert len(first["results"]) == 1

    second = _briefing(client, agent_a_key)
    assert second["results"] == []
    assert second["rating_change"] == 0
    assert second["since"] == first["generated_at"]
