from kinfold_api.config import get_settings
from tests.helpers import create_agent, create_duel, signup_owner, submit_entry


def test_crowd_duel_resolves_after_enough_votes_and_updates_ratings(client):
    _, owner_a_key = signup_owner(client, "owner_crowd_a")
    _, owner_b_key = signup_owner(client, "owner_crowd_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "debater_a")
    agent_b, agent_b_key = create_agent(client, owner_b_key, "debater_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="debate",
        prompt="Should agents vote on agents?",
        answer="Yes, because it keeps humans in the loop.",
    )
    assert duel["status"] == "open"

    entry_response = submit_entry(client, agent_b_key, duel["id"], "No, it's slower than tests.")
    assert entry_response.status_code == 201

    detail = client.get(f"/v1/duels/{duel['id']}").json()
    assert detail["status"] == "judging"
    assert len(detail["entries"]) == 2
    # Blind: no agent identity revealed before resolution.
    assert all(e["agent_id"] is None for e in detail["entries"])
    entry_for_a = next(e for e in detail["entries"] if e["answer"].startswith("Yes"))

    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_crowd_voter_{i}")
        vote_response = client.post(
            f"/v1/duels/{duel['id']}/vote",
            json={"entry_id": entry_for_a["id"]},
            headers={"Authorization": f"Bearer {voter_key}"},
        )
        assert vote_response.status_code == 204, vote_response.text

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    assert resolved["status"] == "resolved"
    assert resolved["winner_agent_id"] == agent_a["id"]
    assert resolved["is_draw"] is False
    # Revealed now that it's resolved.
    assert any(e["agent_id"] == agent_a["id"] for e in resolved["entries"])

    agent_a_after = client.get(f"/v1/agents/{agent_a['name']}").json()
    agent_b_after = client.get(f"/v1/agents/{agent_b['name']}").json()
    assert agent_a_after["wins"] == 1
    assert agent_b_after["losses"] == 1
    assert agent_a_after["rating"] > 1200
    assert agent_b_after["rating"] < 1200


def test_crowd_duel_tied_vote_is_a_draw(client, monkeypatch):
    # Force an even threshold so a clean 1-1 tie is reachable deterministically.
    monkeypatch.setattr(get_settings(), "KINFOLD_MIN_VOTES_TO_RESOLVE", 2)

    _, owner_a_key = signup_owner(client, "owner_draw_a")
    _, owner_b_key = signup_owner(client, "owner_draw_b")
    _, agent_a_key = create_agent(client, owner_a_key, "draw_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "draw_agent_b")

    duel = create_duel(client, agent_a_key, category="explain", answer="Answer A")
    submit_entry(client, agent_b_key, duel["id"], "Answer B")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_a_id = next(e for e in detail["entries"] if e["answer"] == "Answer A")["id"]
    entry_b_id = next(e for e in detail["entries"] if e["answer"] == "Answer B")["id"]

    _, voter_1_key = signup_owner(client, "owner_draw_voter_1")
    _, voter_2_key = signup_owner(client, "owner_draw_voter_2")
    client.post(
        f"/v1/duels/{duel['id']}/vote",
        json={"entry_id": entry_a_id},
        headers={"Authorization": f"Bearer {voter_1_key}"},
    )
    client.post(
        f"/v1/duels/{duel['id']}/vote",
        json={"entry_id": entry_b_id},
        headers={"Authorization": f"Bearer {voter_2_key}"},
    )

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    assert resolved["status"] == "resolved"
    assert resolved["is_draw"] is True
    assert resolved["winner_agent_id"] is None
