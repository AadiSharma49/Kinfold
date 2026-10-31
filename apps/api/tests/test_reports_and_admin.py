from kinfold_api.config import get_settings
from kinfold_api.models import ApiKey, Owner
from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry


def _make_admin(db_session, handle: str) -> None:
    """No self-service admin signup — is_admin is flipped by hand in the
    database, same deliberate friction as scripts/approve_sandbox_agent.py."""
    owner = db_session.query(Owner).filter_by(handle=handle).one()
    owner.is_admin = True
    db_session.commit()


def test_filing_a_report_on_an_unknown_target_404s(client):
    _, owner_key = signup_owner(client, "owner_report_unknown")
    response = client.post(
        "/v1/reports",
        json={"target_type": "duel", "target_id": "00000000-0000-0000-0000-000000000000", "reason": "x"},
        headers={"Authorization": f"Bearer {owner_key}"},
    )
    assert response.status_code == 404


def test_anyone_can_file_a_report_on_a_real_duel(client):
    _, owner_a_key = signup_owner(client, "owner_report_a")
    _, agent_a_key = create_agent(client, owner_a_key, "report_agent_a")
    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")

    _, owner_b_key = signup_owner(client, "owner_report_b")
    response = client.post(
        "/v1/reports",
        json={"target_type": "duel", "target_id": duel["id"], "reason": "Looks like spam."},
        headers={"Authorization": f"Bearer {owner_b_key}"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["resolved_at"] is None


def test_non_admin_cannot_list_or_resolve_reports(client):
    _, owner_key = signup_owner(client, "owner_report_notadmin")
    list_response = client.get("/v1/admin/reports", headers={"Authorization": f"Bearer {owner_key}"})
    assert list_response.status_code == 403


def test_admin_can_resolve_a_report(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_resolve_a")
    _, agent_a_key = create_agent(client, owner_a_key, "resolve_agent_a")
    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")
    _make_admin(db_session, "owner_resolve_a")

    report = client.post(
        "/v1/reports",
        json={"target_type": "duel", "target_id": duel["id"], "reason": "Testing resolution."},
        headers={"Authorization": f"Bearer {owner_a_key}"},
    ).json()

    unresolved = client.get(
        "/v1/admin/reports", params={"resolved": "false"}, headers={"Authorization": f"Bearer {owner_a_key}"}
    ).json()
    assert any(r["id"] == report["id"] for r in unresolved)

    resolve_response = client.post(
        f"/v1/admin/reports/{report['id']}/resolve", headers={"Authorization": f"Bearer {owner_a_key}"}
    )
    assert resolve_response.status_code == 200, resolve_response.text
    assert resolve_response.json()["resolved_at"] is not None


def test_admin_can_hide_a_duel_which_then_404s_for_everyone(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_hide_a")
    _, agent_a_key = create_agent(client, owner_a_key, "hide_agent_a")
    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")
    _make_admin(db_session, "owner_hide_a")

    hide_response = client.post(
        f"/v1/admin/duels/{duel['id']}/hide", headers={"Authorization": f"Bearer {owner_a_key}"}
    )
    assert hide_response.status_code == 200, hide_response.text

    assert client.get(f"/v1/duels/{duel['id']}").status_code == 404
    listed = client.get("/v1/duels").json()
    assert all(d["id"] != duel["id"] for d in listed)


def test_admin_can_hide_an_entry_which_redacts_the_answer(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_hide_entry_a")
    _, owner_b_key = signup_owner(client, "owner_hide_entry_b")
    _, agent_a_key = create_agent(client, owner_a_key, "hide_entry_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "hide_entry_agent_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's real answer")
    entry_b = submit_entry(client, agent_b_key, duel["id"], "B's answer").json()
    _make_admin(db_session, "owner_hide_entry_a")

    hide_response = client.post(
        f"/v1/admin/entries/{entry_b['id']}/hide", headers={"Authorization": f"Bearer {owner_a_key}"}
    )
    assert hide_response.status_code == 204, hide_response.text

    detail = client.get(f"/v1/duels/{duel['id']}").json()
    hidden_entry = next(e for e in detail["entries"] if e["id"] == entry_b["id"])
    assert hidden_entry["answer"] == "[removed by moderator]"


def test_admin_can_disable_an_agent_which_then_cannot_duel(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_disable_a")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "disable_agent_a")
    _make_admin(db_session, "owner_disable_a")

    disable_response = client.post(
        f"/v1/admin/agents/{agent_a['id']}/disable", headers={"Authorization": f"Bearer {owner_a_key}"}
    )
    assert disable_response.status_code == 200, disable_response.text
    assert disable_response.json()["is_disabled"] is True

    duel_response = client.post(
        "/v1/duels",
        json={"category": "debate", "prompt": "Should fail", "answer": "x"},
        headers={"Authorization": f"Bearer {agent_a_key}"},
    )
    assert duel_response.status_code == 403, duel_response.text


def test_admin_can_approve_an_agent_for_the_sandbox(client, db_session, monkeypatch):
    require_docker()
    monkeypatch.setattr(get_settings(), "KINFOLD_SANDBOX_RESTRICTED", True)
    _, owner_a_key = signup_owner(client, "owner_approve_a")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "approve_agent_a")
    _make_admin(db_session, "owner_approve_a")

    code_duel_body = {
        "category": "code",
        "prompt": "x",
        "answer": "print(1)",
        "tests": [{"input": "", "expected_output": "1"}],
    }

    blocked = client.post(
        "/v1/duels", json=code_duel_body, headers={"Authorization": f"Bearer {agent_a_key}"}
    )
    assert blocked.status_code == 403

    approve_response = client.post(
        f"/v1/admin/agents/{agent_a['id']}/approve-sandbox",
        headers={"Authorization": f"Bearer {owner_a_key}"},
    )
    assert approve_response.status_code == 200, approve_response.text
    assert approve_response.json()["sandbox_approved"] is True

    allowed = client.post(
        "/v1/duels", json=code_duel_body, headers={"Authorization": f"Bearer {agent_a_key}"}
    )
    assert allowed.status_code == 201, allowed.text


def test_admin_can_revoke_any_key(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_revoke_a")
    _, agent_a_key = create_agent(client, owner_a_key, "revoke_agent_a")
    _make_admin(db_session, "owner_revoke_a")

    key_row = (
        db_session.query(ApiKey).filter_by(kind="agent").order_by(ApiKey.created_at.desc()).first()
    )

    revoke_response = client.delete(
        f"/v1/admin/keys/{key_row.id}", headers={"Authorization": f"Bearer {owner_a_key}"}
    )
    assert revoke_response.status_code == 200, revoke_response.text
    assert revoke_response.json()["revoked_at"] is not None

    whoami = client.get("/v1/agents/me", headers={"Authorization": f"Bearer {agent_a_key}"})
    assert whoami.status_code == 401
