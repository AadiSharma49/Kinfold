from tests.helpers import create_agent, signup_owner


def test_list_my_agents_returns_only_my_own(client):
    _, owner_a_key = signup_owner(client, "owner_myagents_a")
    _, owner_b_key = signup_owner(client, "owner_myagents_b")
    create_agent(client, owner_a_key, "myagents_a1")
    create_agent(client, owner_a_key, "myagents_a2")
    create_agent(client, owner_b_key, "myagents_b1")

    response = client.get("/v1/owners/me/agents", headers={"Authorization": f"Bearer {owner_a_key}"})
    assert response.status_code == 200, response.text
    names = {a["name"] for a in response.json()}
    assert names == {"myagents_a1", "myagents_a2"}


def test_list_my_agents_requires_owner_key(client):
    _, owner_key = signup_owner(client, "owner_myagents_noauth")
    _, agent_key = create_agent(client, owner_key, "myagents_noauth_agent")

    response = client.get("/v1/owners/me/agents", headers={"Authorization": f"Bearer {agent_key}"})
    assert response.status_code == 403, response.text


def test_list_my_agents_empty_for_a_fresh_owner(client):
    _, owner_key = signup_owner(client, "owner_myagents_empty")

    response = client.get("/v1/owners/me/agents", headers={"Authorization": f"Bearer {owner_key}"})
    assert response.status_code == 200, response.text
    assert response.json() == []
