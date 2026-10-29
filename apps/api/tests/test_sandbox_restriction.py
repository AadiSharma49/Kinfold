from kinfold_api.config import get_settings
from kinfold_api.models import Agent
from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry


def _code_duel_body():
    return {
        "category": "code",
        "prompt": "Return the input unchanged.",
        "answer": "import sys\nprint(sys.stdin.read(), end='')",
        "tests": [{"input": "hi", "expected_output": "hi"}],
    }


def test_restriction_off_by_default_lets_any_agent_run_code_duels(client):
    require_docker()
    _, owner_key = signup_owner(client, "owner_sbx_default")
    _, agent_key = create_agent(client, owner_key, "sbx_default_agent")

    response = client.post(
        "/v1/duels", json=_code_duel_body(), headers={"Authorization": f"Bearer {agent_key}"}
    )
    assert response.status_code == 201, response.text


def test_restricted_mode_blocks_unapproved_agent_from_creating(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "KINFOLD_SANDBOX_RESTRICTED", True)
    _, owner_key = signup_owner(client, "owner_sbx_blocked")
    _, agent_key = create_agent(client, owner_key, "sbx_blocked_agent")

    response = client.post(
        "/v1/duels", json=_code_duel_body(), headers={"Authorization": f"Bearer {agent_key}"}
    )
    assert response.status_code == 403, response.text


def test_restricted_mode_blocks_unapproved_agent_from_joining(client, monkeypatch):
    _, owner_a_key = signup_owner(client, "owner_sbx_join_a")
    _, owner_b_key = signup_owner(client, "owner_sbx_join_b")
    _, agent_a_key = create_agent(client, owner_a_key, "sbx_join_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "sbx_join_agent_b")

    # Created before the restriction turns on, so creation itself succeeds —
    # this isolates the check to the joining agent.
    duel = create_duel(client, agent_a_key, **_code_duel_body())

    monkeypatch.setattr(get_settings(), "KINFOLD_SANDBOX_RESTRICTED", True)
    response = submit_entry(client, agent_b_key, duel["id"], "print('x')")
    assert response.status_code == 403, response.text


def test_restricted_mode_allows_an_approved_agent(client, monkeypatch, db_session):
    require_docker()
    monkeypatch.setattr(get_settings(), "KINFOLD_SANDBOX_RESTRICTED", True)
    _, owner_key = signup_owner(client, "owner_sbx_approved")
    agent, agent_key = create_agent(client, owner_key, "sbx_approved_agent")

    row = db_session.query(Agent).filter_by(name="sbx_approved_agent").one()
    row.sandbox_approved = True
    db_session.commit()

    response = client.post(
        "/v1/duels", json=_code_duel_body(), headers={"Authorization": f"Bearer {agent_key}"}
    )
    assert response.status_code == 201, response.text
    assert agent["name"] == "sbx_approved_agent"


def test_restricted_mode_allows_a_house_agent(client, monkeypatch, db_session):
    from kinfold_api.models import Owner
    from kinfold_api.services.agents import create_agent_with_key

    monkeypatch.setattr(get_settings(), "KINFOLD_SANDBOX_RESTRICTED", True)
    signup_owner(client, "owner_sbx_house")
    owner_row = db_session.query(Owner).filter_by(handle="owner_sbx_house").one()

    _agent, _api_key, house_key = create_agent_with_key(
        db_session,
        owner=owner_row,
        name="sbx_house_agent",
        description=None,
        model_name="Kinfold reference agent (scripted)",
        model_family="house",
        open_weights=True,
        is_house=True,
    )

    response = client.post(
        "/v1/duels", json=_code_duel_body(), headers={"Authorization": f"Bearer {house_key}"}
    )
    assert response.status_code == 201, response.text
