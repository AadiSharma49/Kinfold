from tests.helpers import create_agent, signup_owner


def test_no_response_ever_contains_key_hash(client):
    _, owner_key = signup_owner(client, "owner_leak")

    signup_response = client.post("/v1/owners/dev-signup", json={"handle": "owner_leak_2"})
    assert "key_hash" not in signup_response.text

    agent, _ = create_agent(client, owner_key, "agent_leak")

    me_response = client.get("/v1/owners/me", headers={"Authorization": f"Bearer {owner_key}"})
    assert "key_hash" not in me_response.text

    keys_response = client.get("/v1/keys", headers={"Authorization": f"Bearer {owner_key}"})
    assert "key_hash" not in keys_response.text

    list_agents_response = client.get("/v1/agents")
    assert "key_hash" not in list_agents_response.text

    agent_profile_response = client.get(f"/v1/agents/{agent['name']}")
    assert "key_hash" not in agent_profile_response.text

    create_key_response = client.post(
        f"/v1/agents/{agent['id']}/keys",
        json={"label": "extra"},
        headers={"Authorization": f"Bearer {owner_key}"},
    )
    assert "key_hash" not in create_key_response.text
