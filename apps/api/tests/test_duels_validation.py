from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry


def test_agent_cannot_duel_itself(client):
    _, owner_key = signup_owner(client, "owner_selfduel")
    _, agent_key = create_agent(client, owner_key, "selfduel_agent")

    duel = create_duel(client, agent_key, category="debate")
    response = submit_entry(client, agent_key, duel["id"], "my own second answer")
    assert response.status_code == 409


def test_code_duel_requires_tests(client):
    _, owner_key = signup_owner(client, "owner_notests")
    _, agent_key = create_agent(client, owner_key, "notests_agent")

    response = client.post(
        "/v1/duels",
        json={"category": "code", "prompt": "add two numbers", "answer": "print(1)"},
        headers={"Authorization": f"Bearer {agent_key}"},
    )
    assert response.status_code == 422


def test_non_code_duel_rejects_tests(client):
    _, owner_key = signup_owner(client, "owner_extratests")
    _, agent_key = create_agent(client, owner_key, "extratests_agent")

    response = client.post(
        "/v1/duels",
        json={
            "category": "debate",
            "prompt": "topic",
            "answer": "opinion",
            "tests": [{"input": "", "expected_output": "x"}],
        },
        headers={"Authorization": f"Bearer {agent_key}"},
    )
    assert response.status_code == 422


def test_owner_cannot_vote_on_duel_their_own_agent_is_in(client):
    _, owner_a_key = signup_owner(client, "owner_vself_a")
    _, owner_b_key = signup_owner(client, "owner_vself_b")
    _, agent_a_key = create_agent(client, owner_a_key, "vself_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "vself_agent_b")

    duel = create_duel(client, agent_a_key, category="debate")
    submit_entry(client, agent_b_key, duel["id"], "second answer")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_id = detail["entries"][0]["id"]

    response = client.post(
        f"/v1/duels/{duel['id']}/vote",
        json={"entry_id": entry_id},
        headers={"Authorization": f"Bearer {owner_a_key}"},
    )
    assert response.status_code == 403


def test_double_vote_rejected(client):
    _, owner_a_key = signup_owner(client, "owner_dvote_a")
    _, owner_b_key = signup_owner(client, "owner_dvote_b")
    _, voter_key = signup_owner(client, "owner_dvote_voter")
    _, agent_a_key = create_agent(client, owner_a_key, "dvote_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "dvote_agent_b")

    duel = create_duel(client, agent_a_key, category="debate")
    submit_entry(client, agent_b_key, duel["id"], "second answer")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_id = detail["entries"][0]["id"]

    first = client.post(
        f"/v1/duels/{duel['id']}/vote",
        json={"entry_id": entry_id},
        headers={"Authorization": f"Bearer {voter_key}"},
    )
    second = client.post(
        f"/v1/duels/{duel['id']}/vote",
        json={"entry_id": entry_id},
        headers={"Authorization": f"Bearer {voter_key}"},
    )
    assert first.status_code == 204
    assert second.status_code == 409


def test_cannot_vote_on_code_duel(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_cvote_a")
    _, owner_b_key = signup_owner(client, "owner_cvote_b")
    _, voter_key = signup_owner(client, "owner_cvote_voter")
    _, agent_a_key = create_agent(client, owner_a_key, "cvote_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "cvote_agent_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        answer="a=input()\nprint(a)",
        tests=[{"input": "5", "expected_output": "5"}],
    )
    submit_entry(client, agent_b_key, duel["id"], "a=input()\nprint(a)")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_id = detail["entries"][0]["id"]

    response = client.post(
        f"/v1/duels/{duel['id']}/vote",
        json={"entry_id": entry_id},
        headers={"Authorization": f"Bearer {voter_key}"},
    )
    assert response.status_code == 409
