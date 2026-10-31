from kinfold_api.config import get_settings
from tests.helpers import create_agent, create_duel, signup_owner, submit_human_entry


def test_human_can_join_an_open_crowd_duel(client):
    _, owner_a_key = signup_owner(client, "owner_human_a")
    _, owner_b_key = signup_owner(client, "owner_human_b")
    _, agent_a_key = create_agent(client, owner_a_key, "human_duel_agent_a")

    duel = create_duel(client, agent_a_key, category="debate", answer="AI's answer")
    response = submit_human_entry(client, owner_b_key, duel["id"], "Human's answer")

    assert response.status_code == 201, response.text
    assert response.json()["slot"] == 2

    detail = client.get(f"/v1/duels/{duel['id']}").json()
    assert detail["status"] == "judging"


def test_human_cannot_join_a_duel_their_own_agent_created(client):
    _, owner_key = signup_owner(client, "owner_human_self")
    _, agent_key = create_agent(client, owner_key, "human_self_agent")

    duel = create_duel(client, agent_key, category="debate", answer="AI's answer")
    response = submit_human_entry(client, owner_key, duel["id"], "My own answer")

    assert response.status_code == 409, response.text


def test_human_cannot_join_a_code_duel(client):
    _, owner_a_key = signup_owner(client, "owner_human_code_a")
    _, owner_b_key = signup_owner(client, "owner_human_code_b")
    _, agent_a_key = create_agent(client, owner_a_key, "human_code_agent_a")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        answer="print(1)",
        tests=[{"input": "", "expected_output": "1"}],
    )
    response = submit_human_entry(client, owner_b_key, duel["id"], "I'd write it like this...")

    assert response.status_code == 409, response.text
    assert "crowd duel" in response.json()["detail"]


def test_human_entry_is_blind_until_resolved_then_revealed(client):
    _, owner_a_key = signup_owner(client, "owner_human_reveal_a")
    _, owner_b_key = signup_owner(client, "owner_human_reveal_b")
    _, agent_a_key = create_agent(client, owner_a_key, "human_reveal_agent_a")

    duel = create_duel(client, agent_a_key, category="explain", answer="AI's answer")
    entry = submit_human_entry(client, owner_b_key, duel["id"], "Human's answer").json()
    assert entry["human_owner_handle"] is None  # not resolved yet — blind

    blind_detail = client.get(f"/v1/duels/{duel['id']}").json()
    human_entry_blind = next(e for e in blind_detail["entries"] if e["answer"] == "Human's answer")
    assert human_entry_blind["human_owner_handle"] is None
    assert human_entry_blind["agent_id"] is None

    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_human_reveal_voter_{i}")
        vote_response = client.post(
            f"/v1/duels/{duel['id']}/vote",
            json={"entry_id": entry["id"]},
            headers={"Authorization": f"Bearer {voter_key}"},
        )
        assert vote_response.status_code == 204, vote_response.text

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    assert resolved["status"] == "resolved"
    human_entry_revealed = next(e for e in resolved["entries"] if e["id"] == entry["id"])
    assert human_entry_revealed["human_owner_handle"] == "owner_human_reveal_b"


def test_human_win_updates_duel_and_agent_rating_without_crashing(client):
    _, owner_a_key = signup_owner(client, "owner_human_win_a")
    _, owner_b_key = signup_owner(client, "owner_human_win_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "human_win_agent_a")

    duel = create_duel(client, agent_a_key, category="hinglish", answer="AI's answer")
    entry = submit_human_entry(client, owner_b_key, duel["id"], "Human's answer").json()

    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_human_win_voter_{i}")
        client.post(
            f"/v1/duels/{duel['id']}/vote",
            json={"entry_id": entry["id"]},
            headers={"Authorization": f"Bearer {voter_key}"},
        )

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    assert resolved["status"] == "resolved"
    assert resolved["winner_agent_id"] is None
    assert resolved["winner_human_owner_id"] is not None

    agent_profile = client.get(f"/v1/agents/{agent_a['name']}").json()
    assert agent_profile["losses"] == 1
    assert agent_profile["rating"] < agent_a["rating"]
