from tests.helpers import create_agent, signup_owner


def test_agent_key_rejected_from_owner_route(client):
    _, owner_key = signup_owner(client, "owner_a")
    _, agent_key = create_agent(client, owner_key, "agent_a")

    response = client.get("/v1/owners/me", headers={"Authorization": f"Bearer {agent_key}"})
    assert response.status_code == 403


def test_owner_key_rejected_from_agent_route(client):
    _, owner_key = signup_owner(client, "owner_b")
    create_agent(client, owner_key, "agent_b")

    response = client.get("/v1/agents/me", headers={"Authorization": f"Bearer {owner_key}"})
    assert response.status_code == 403


def test_revoked_key_returns_401(client):
    _, owner_key = signup_owner(client, "owner_c")

    keys_response = client.get("/v1/keys", headers={"Authorization": f"Bearer {owner_key}"})
    assert keys_response.status_code == 200
    key_id = keys_response.json()[0]["id"]

    revoke_response = client.delete(
        f"/v1/keys/{key_id}", headers={"Authorization": f"Bearer {owner_key}"}
    )
    assert revoke_response.status_code == 200

    me_response = client.get("/v1/owners/me", headers={"Authorization": f"Bearer {owner_key}"})
    assert me_response.status_code == 401


def test_revoke_is_idempotent(client):
    _, owner_key = signup_owner(client, "owner_d")
    second_key_response = client.post(
        "/v1/owners/keys", json={"label": "second"}, headers={"Authorization": f"Bearer {owner_key}"}
    )
    key_id = second_key_response.json()["id"]

    first_revoke = client.delete(f"/v1/keys/{key_id}", headers={"Authorization": f"Bearer {owner_key}"})
    second_revoke = client.delete(f"/v1/keys/{key_id}", headers={"Authorization": f"Bearer {owner_key}"})

    assert first_revoke.status_code == 200
    assert second_revoke.status_code == 200
