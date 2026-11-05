from __future__ import annotations

from tests.helpers import create_agent, signup_owner

_INTERNAL_FIELDS = {"owner_id", "sandbox_approved", "is_disabled"}


def _agents_from(body) -> list[dict]:
    if isinstance(body, list):
        return body
    if isinstance(body, dict) and isinstance(body.get("agent"), dict):
        return [body["agent"]]
    return [body]


def test_public_agent_endpoints_omit_internal_fields(client):
    _, owner_key = signup_owner(client, "owner_public_agent")
    agent, _ = create_agent(client, owner_key, "public_agent")

    responses = [
        client.get("/v1/agents"),
        client.get(f"/v1/agents/{agent['name']}"),
        client.get(f"/v1/agents/{agent['name']}/profile"),
    ]
    for response in responses:
        assert response.status_code == 200, response.text
        assert "key_hash" not in response.text
        for public_agent in _agents_from(response.json()):
            if public_agent.get("name") != agent["name"]:
                continue
            assert public_agent["owner_handle"] == "owner_public_agent"
            for field in _INTERNAL_FIELDS:
                assert field not in public_agent, f"{field} leaked in {response.request.url}"


def test_authenticated_agent_still_sees_its_owner_id(client):
    _, owner_key = signup_owner(client, "owner_private_agent")
    agent, agent_key = create_agent(client, owner_key, "private_agent")

    response = client.get("/v1/agents/me", headers={"Authorization": f"Bearer {agent_key}"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["owner_id"] is not None
    assert body["id"] == agent["id"]
