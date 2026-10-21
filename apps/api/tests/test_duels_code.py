from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry

WINNING_CODE = "n = int(input())\nprint(n * n)"
LOSING_CODE = "print(0)"


def test_code_duel_resolves_via_sandbox_and_updates_ratings(client):
    require_docker()

    _, owner_a_key = signup_owner(client, "owner_code_a")
    _, owner_b_key = signup_owner(client, "owner_code_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "coder_a")
    agent_b, agent_b_key = create_agent(client, owner_b_key, "coder_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        prompt="Read an integer and print its square.",
        answer=WINNING_CODE,
        tests=[{"input": "4", "expected_output": "16"}],
    )
    assert duel["status"] == "open"

    response = submit_entry(client, agent_b_key, duel["id"], LOSING_CODE)
    assert response.status_code == 201

    resolved = client.get(f"/v1/duels/{duel['id']}").json()
    assert resolved["status"] == "resolved"
    assert resolved["winner_agent_id"] == agent_a["id"]
    assert resolved["is_draw"] is False

    winning_entry = next(e for e in resolved["entries"] if e["agent_id"] == agent_a["id"])
    losing_entry = next(e for e in resolved["entries"] if e["agent_id"] == agent_b["id"])
    assert winning_entry["passed_tests"] == 1
    assert winning_entry["total_tests"] == 1
    assert losing_entry["passed_tests"] == 0
    assert losing_entry["total_tests"] == 1

    agent_a_after = client.get(f"/v1/agents/{agent_a['name']}").json()
    agent_b_after = client.get(f"/v1/agents/{agent_b['name']}").json()
    assert agent_a_after["wins"] == 1
    assert agent_b_after["losses"] == 1
    assert agent_a_after["rating"] > 1200
    assert agent_b_after["rating"] < 1200
