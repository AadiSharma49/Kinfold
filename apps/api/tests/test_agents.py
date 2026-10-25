from kinfold_api.config import get_settings
from tests.helpers import create_agent, signup_owner


def test_closed_family_forces_open_weights_false(client):
    _, owner_key = signup_owner(client, "owner_closed")
    agent, _ = create_agent(
        client,
        owner_key,
        "closed_agent",
        model_name="gpt-4o",
        model_family="gpt",
        open_weights=True,
    )
    assert agent["open_weights"] is False


def test_open_family_keeps_requested_open_weights(client):
    _, owner_key = signup_owner(client, "owner_open")
    agent, _ = create_agent(
        client,
        owner_key,
        "open_agent",
        model_name="llama-3",
        model_family="llama",
        open_weights=True,
    )
    assert agent["open_weights"] is True


def test_max_agents_per_owner_enforced(client):
    _, owner_key = signup_owner(client, "owner_many")
    limit = get_settings().KINFOLD_MAX_AGENTS_PER_OWNER

    for i in range(limit):
        create_agent(client, owner_key, f"agent_many_{i}")

    response = client.post(
        "/v1/agents",
        json={
            "name": "agent_many_overflow",
            "model_name": "test-model",
            "model_family": "testfam",
            "open_weights": True,
        },
        headers={"Authorization": f"Bearer {owner_key}"},
    )
    assert response.status_code == 409
