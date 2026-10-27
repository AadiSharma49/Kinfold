from kinfold_api.config import get_settings
from kinfold_api.models import Owner
from kinfold_api.services.agents import create_agent_with_key
from tests.helpers import create_agent, create_duel, signup_owner, submit_entry


def test_public_signup_cannot_set_is_house(client):
    _, owner_key = signup_owner(client, "owner_house_guard")
    response = client.post(
        "/v1/agents",
        json={
            "name": "sneaky_agent",
            "model_name": "test",
            "model_family": "testfam",
            "open_weights": True,
            "is_house": True,  # not a real field on AgentCreateRequest — must be ignored
        },
        headers={"Authorization": f"Bearer {owner_key}"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["agent"]["is_house"] is False


def test_house_agent_created_via_service_is_labeled(client, db_session):
    _, owner_key = signup_owner(client, "owner_house_a")
    owner_row = db_session.query(Owner).filter_by(handle="owner_house_a").one()

    agent, _api_key, _raw_key = create_agent_with_key(
        db_session,
        owner=owner_row,
        name="house_test_agent",
        description="A Kinfold house agent for testing.",
        model_name="Kinfold reference agent (scripted)",
        model_family="house",
        open_weights=True,
        is_house=True,
    )
    assert agent.is_house is True

    response = client.get(f"/v1/agents/{agent.name}")
    assert response.status_code == 200
    assert response.json()["is_house"] is True


def test_house_flag_shown_on_resolved_duel_entries(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_house_duel_a")
    _, owner_b_key = signup_owner(client, "owner_house_duel_b")
    owner_a_row = db_session.query(Owner).filter_by(handle="owner_house_duel_a").one()

    house_agent, _api_key, house_key = create_agent_with_key(
        db_session,
        owner=owner_a_row,
        name="house_duel_agent",
        description=None,
        model_name="Kinfold reference agent (scripted)",
        model_family="house",
        open_weights=True,
        is_house=True,
    )
    _, agent_b_key = create_agent(client, owner_b_key, "regular_duel_agent")

    duel = create_duel(client, house_key, category="debate", answer="House answer")
    submit_entry(client, agent_b_key, duel["id"], "Regular answer")

    blind = client.get(f"/v1/duels/{duel['id']}").json()
    entry_for_house = next(e for e in blind["entries"] if e["answer"] == "House answer")

    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_house_duel_voter_{i}")
        vote_response = client.post(
            f"/v1/duels/{duel['id']}/vote",
            json={"entry_id": entry_for_house["id"]},
            headers={"Authorization": f"Bearer {voter_key}"},
        )
        assert vote_response.status_code == 204, vote_response.text

    detail = client.get(f"/v1/duels/{duel['id']}").json()
    assert detail["status"] == "resolved"
    house_entry = next(e for e in detail["entries"] if e["agent_name"] == "house_duel_agent")
    regular_entry = next(e for e in detail["entries"] if e["agent_name"] == "regular_duel_agent")
    assert house_entry["agent_is_house"] is True
    assert regular_entry["agent_is_house"] is False
