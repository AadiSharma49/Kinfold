from kinfold_api.config import get_settings
from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry


def _resolve_with_human_votes(client, duel_id, winning_entry_id):
    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_profile_voter_{duel_id[:8]}_{i}")
        client.post(
            f"/v1/duels/{duel_id}/vote",
            json={"entry_id": winning_entry_id},
            headers={"Authorization": f"Bearer {voter_key}"},
        )


def test_agent_profile_includes_category_record_and_history(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_profile_a")
    _, owner_b_key = signup_owner(client, "owner_profile_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "profile_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "profile_agent_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        prompt="Double the input.",
        answer="n=int(input())\nprint(n*2)",
        tests=[{"input": "3", "expected_output": "6"}],
    )
    submit_entry(client, agent_b_key, duel["id"], "print(0)")

    response = client.get(f"/v1/agents/{agent_a['name']}/profile")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["agent"]["name"] == "profile_agent_a"
    assert body["category_record"]["code"] == {"wins": 1, "losses": 0, "draws": 0}
    assert len(body["recent_duels"]) == 1
    entry = body["recent_duels"][0]
    assert entry["result"] == "win"
    assert entry["passed_tests"] == 1
    assert entry["total_tests"] == 1
    assert entry["opponent_agent_name"] == "profile_agent_b"


def test_agent_profile_404_for_unknown_name(client):
    response = client.get("/v1/agents/does-not-exist/profile")
    assert response.status_code == 404


def test_owner_profile_404_with_no_activity(client):
    signup_owner(client, "owner_profile_empty")
    response = client.get("/v1/owners/owner_profile_empty/profile")
    assert response.status_code == 404


def test_owner_profile_shows_human_duel_history_after_activity(client):
    _, owner_a_key = signup_owner(client, "owner_profile_human_a")
    _, owner_b_key = signup_owner(client, "owner_profile_human_b")
    _, agent_a_key = create_agent(client, owner_a_key, "profile_human_agent_a")

    duel = create_duel(client, agent_a_key, category="debate", answer="AI's answer")
    entry = client.post(
        f"/v1/duels/{duel['id']}/human-entry",
        json={
            "answer": "Human's answer",
            "time_taken_seconds": 30,
            "declared_ai_tools": "none",
        },
        headers={"Authorization": f"Bearer {owner_b_key}"},
    ).json()

    _resolve_with_human_votes(client, duel["id"], entry["id"])

    response = client.get("/v1/owners/owner_profile_human_b/profile")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["owner"]["handle"] == "owner_profile_human_b"
    assert "id" not in body["owner"]

    assert len(body["human_duel_history"]) == 1
    history_entry = body["human_duel_history"][0]
    assert history_entry["result"] == "win"
    assert history_entry["time_taken_seconds"] == 30
    assert history_entry["declared_ai_tools"] == "none"
    assert history_entry["opponent_agent_name"] == "profile_human_agent_a"


def test_owner_profile_404_for_unknown_handle(client):
    response = client.get("/v1/owners/no-such-handle-at-all/profile")
    assert response.status_code == 404
