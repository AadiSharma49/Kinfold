from kinfold_api.config import get_settings
from tests.helpers import create_agent, create_duel, signup_owner, submit_entry


def _judge(client, agent_key, duel_id, entry_id, **overrides):
    body = {
        "entry_id": entry_id,
        "strengths": "Clear and concrete.",
        "weaknesses": "A bit short.",
        "verdict": "Entry A is more convincing.",
        "score": 7,
        **overrides,
    }
    return client.post(
        f"/v1/duels/{duel_id}/judgments",
        json=body,
        headers={"Authorization": f"Bearer {agent_key}"},
    )


_voter_counter = 0


def _resolve_with_human_votes(client, duel_id, winning_entry_id):
    global _voter_counter
    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for _ in range(min_votes):
        _voter_counter += 1
        _, voter_key = signup_owner(client, f"owner_judge_voter_{_voter_counter}")
        response = client.post(
            f"/v1/duels/{duel_id}/vote",
            json={"entry_id": winning_entry_id},
            headers={"Authorization": f"Bearer {voter_key}"},
        )
        assert response.status_code == 204, response.text


def test_agent_cannot_judge_a_duel_it_entered(client):
    _, owner_a_key = signup_owner(client, "owner_judge_self_a")
    _, owner_b_key = signup_owner(client, "owner_judge_self_b")
    _, agent_a_key = create_agent(client, owner_a_key, "judge_self_a")
    _, agent_b_key = create_agent(client, owner_b_key, "judge_self_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")
    submit_entry(client, agent_b_key, duel["id"], "B's answer")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_id = detail["entries"][0]["id"]

    response = _judge(client, agent_a_key, duel["id"], entry_id)
    assert response.status_code == 403, response.text


def test_agent_cannot_judge_a_code_duel(client):
    _, owner_a_key = signup_owner(client, "owner_judge_code_a")
    _, owner_c_key = signup_owner(client, "owner_judge_code_c")
    _, agent_a_key = create_agent(client, owner_a_key, "judge_code_a")
    _, agent_c_key = create_agent(client, owner_c_key, "judge_code_c")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        answer="print('x')",
        tests=[{"input": "", "expected_output": "x"}],
    )
    # Category is checked before entries, so an arbitrary UUID is fine here.
    response = _judge(client, agent_c_key, duel["id"], duel["id"])
    assert response.status_code == 409, response.text
    assert "crowd duels" in response.json()["detail"]


def test_agent_cannot_judge_the_same_duel_twice(client):
    _, owner_a_key = signup_owner(client, "owner_judge_twice_a")
    _, owner_b_key = signup_owner(client, "owner_judge_twice_b")
    _, owner_c_key = signup_owner(client, "owner_judge_twice_c")
    _, agent_a_key = create_agent(client, owner_a_key, "judge_twice_a")
    _, agent_b_key = create_agent(client, owner_b_key, "judge_twice_b")
    _, agent_c_key = create_agent(client, owner_c_key, "judge_twice_c")

    duel = create_duel(client, agent_a_key, category="explain", answer="A's answer")
    submit_entry(client, agent_b_key, duel["id"], "B's answer")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_id = detail["entries"][0]["id"]

    first = _judge(client, agent_c_key, duel["id"], entry_id)
    assert first.status_code == 201, first.text
    second = _judge(client, agent_c_key, duel["id"], entry_id)
    assert second.status_code == 409, second.text


def test_judgments_are_hidden_until_resolved_then_revealed_and_scored(client):
    _, owner_a_key = signup_owner(client, "owner_judge_reveal_a")
    _, owner_b_key = signup_owner(client, "owner_judge_reveal_b")
    _, owner_judge_key = signup_owner(client, "owner_judge_reveal_j")
    _, agent_a_key = create_agent(client, owner_a_key, "judge_reveal_a")
    _, agent_b_key = create_agent(client, owner_b_key, "judge_reveal_b")
    judge_agent, judge_key = create_agent(client, owner_judge_key, "judge_reveal_judge")

    duel = create_duel(client, agent_a_key, category="hinglish", answer="A's answer")
    submit_entry(client, agent_b_key, duel["id"], "B's answer")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_a_id = detail["entries"][0]["id"]

    judge_response = _judge(client, judge_key, duel["id"], entry_a_id)
    assert judge_response.status_code == 201, judge_response.text
    assert judge_response.json()["agreed_with_result"] is None

    # Not yet resolved — judgments stay hidden, same rule as blind entries.
    before = client.get(f"/v1/duels/{duel['id']}/judgments").json()
    assert before == []

    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    after = client.get(f"/v1/duels/{duel['id']}/judgments").json()
    assert len(after) == 1
    assert after[0]["agent_name"] == "judge_reveal_judge"
    assert after[0]["chosen_entry_id"] == entry_a_id
    assert after[0]["agreed_with_result"] is True

    judge_profile = client.get(f"/v1/agents/{judge_agent['name']}").json()
    assert judge_profile["judge_rating"] == 1200 + get_settings().KINFOLD_JUDGE_RATING_K_FACTOR


def test_judge_rating_drops_on_disagreement(client):
    _, owner_a_key = signup_owner(client, "owner_judge_wrong_a")
    _, owner_b_key = signup_owner(client, "owner_judge_wrong_b")
    _, owner_judge_key = signup_owner(client, "owner_judge_wrong_j")
    _, agent_a_key = create_agent(client, owner_a_key, "judge_wrong_a")
    _, agent_b_key = create_agent(client, owner_b_key, "judge_wrong_b")
    judge_agent, judge_key = create_agent(client, owner_judge_key, "judge_wrong_judge")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")
    submit_entry(client, agent_b_key, duel["id"], "B's answer")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_a_id = detail["entries"][0]["id"]
    entry_b_id = detail["entries"][1]["id"]

    _judge(client, judge_key, duel["id"], entry_a_id)
    # Humans pick B — the judge picked A, so it disagreed with the result.
    _resolve_with_human_votes(client, duel["id"], entry_b_id)

    judge_profile = client.get(f"/v1/agents/{judge_agent['name']}").json()
    assert judge_profile["judge_rating"] == 1200 - get_settings().KINFOLD_JUDGE_RATING_K_FACTOR
