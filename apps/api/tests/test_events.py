import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from kinfold_api.services.events import verify_chain
from tests.helpers import create_agent, signup_owner


def test_chain_verifies_after_several_actions(client, db_session):
    _, owner_key = signup_owner(client, "owner_events")
    create_agent(client, owner_key, "agent_events")
    client.post(
        "/v1/owners/keys",
        json={"label": "second key"},
        headers={"Authorization": f"Bearer {owner_key}"},
    )

    ok, broken_at_seq = verify_chain(db_session)
    assert ok is True
    assert broken_at_seq is None

    response = client.get("/v1/events/verify")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "broken_at_seq": None}


def test_direct_sql_update_and_delete_on_events_fail(client, db_session):
    signup_owner(client, "owner_events_2")
    event_id = db_session.execute(text("SELECT id FROM events LIMIT 1")).scalar_one()

    with pytest.raises(DBAPIError):
        db_session.execute(text("UPDATE events SET type = 'tampered' WHERE id = :id"), {"id": event_id})
    db_session.rollback()

    with pytest.raises(DBAPIError):
        db_session.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
    db_session.rollback()
