from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from kinfold_api.config import get_settings
from kinfold_api.models import Duel, DuelEntry, Owner
from kinfold_api.services.duels import apply_resolution
from tests.helpers import (
    create_agent,
    create_bug_listing,
    create_duel,
    signup_owner,
    submit_entry,
)


def _make_admin(db_session, handle: str) -> None:
    owner = db_session.query(Owner).filter_by(handle=handle).one()
    owner.is_admin = True
    db_session.commit()


def _entries(detail: dict) -> tuple[dict, dict]:
    return detail["entries"][0], detail["entries"][1]


def _judge(client, agent_key: str, duel_id: str, entry_id: str):
    return client.post(
        f"/v1/duels/{duel_id}/judgments",
        json={
            "entry_id": entry_id,
            "strengths": "Clear and direct.",
            "weaknesses": "Could be longer.",
            "verdict": "Reasonable answer.",
            "score": 7,
        },
        headers={"Authorization": f"Bearer {agent_key}"},
    )


def test_second_resolution_is_a_no_op_and_late_votes_are_rejected(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_race_a")
    _, owner_b_key = signup_owner(client, "owner_race_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "race_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "race_agent_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="Answer A")
    submit_entry(client, agent_b_key, duel["id"], "Answer B")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_a, entry_b = _entries(detail)

    for i in range(get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE):
        _, voter_key = signup_owner(client, f"owner_race_voter_{i}")
        response = client.post(
            f"/v1/duels/{duel['id']}/vote",
            json={"entry_id": entry_a["id"]},
            headers={"Authorization": f"Bearer {voter_key}"},
        )
        assert response.status_code == 204, response.text

    rating_after_first = client.get(f"/v1/agents/{agent_a['name']}").json()["rating"]

    duel_row = db_session.get(Duel, uuid.UUID(duel["id"]))
    entry_a_row = db_session.get(DuelEntry, uuid.UUID(entry_a["id"]))
    entry_b_row = db_session.get(DuelEntry, uuid.UUID(entry_b["id"]))
    assert duel_row.status == "resolved"

    # A second resolution attempt (the losing half of a concurrent vote
    # race) must see the duel is no longer judging and change nothing.
    apply_resolution(db_session, duel_row, entry_a_row, entry_b_row, winner_entry=entry_a_row)
    db_session.commit()

    assert client.get(f"/v1/agents/{agent_a['name']}").json()["rating"] == rating_after_first

    _, late_voter_key = signup_owner(client, "owner_race_late_voter")
    late_vote = client.post(
        f"/v1/duels/{duel['id']}/vote",
        json={"entry_id": entry_b["id"]},
        headers={"Authorization": f"Bearer {late_voter_key}"},
    )
    assert late_vote.status_code == 409


def test_stale_judging_duel_expires_without_moving_ratings(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_expire_a")
    _, owner_b_key = signup_owner(client, "owner_expire_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "expire_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "expire_agent_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="Answer A")
    submit_entry(client, agent_b_key, duel["id"], "Answer B")
    rating_before = client.get(f"/v1/agents/{agent_a['name']}").json()["rating"]

    duel_row = db_session.get(Duel, uuid.UUID(duel["id"]))
    duel_row.judging_started_at = datetime.now(UTC) - timedelta(
        minutes=get_settings().KINFOLD_DUEL_EXPIRY_MINUTES + 5
    )
    db_session.commit()

    detail = client.get(f"/v1/duels/{duel['id']}").json()
    assert detail["status"] == "expired"
    assert detail["resolved_at"] is None
    assert detail["winner_agent_id"] is None
    assert client.get(f"/v1/agents/{agent_a['name']}").json()["rating"] == rating_before

    duel_row = db_session.get(Duel, uuid.UUID(duel["id"]))
    assert duel_row.expired_at is not None


def test_open_duel_is_never_expired_for_waiting(client, db_session):
    _, owner_key = signup_owner(client, "owner_expire_open")
    _, agent_key = create_agent(client, owner_key, "expire_open_agent")
    duel = create_duel(client, agent_key, category="debate", answer="Answer A")

    duel_row = db_session.get(Duel, uuid.UUID(duel["id"]))
    duel_row.created_at = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()

    assert client.get(f"/v1/duels/{duel['id']}").json()["status"] == "open"


def test_admin_can_retry_an_expired_crowd_duel(client, db_session, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "KINFOLD_MIN_VOTES_TO_RESOLVE", 99)

    _, owner_a_key = signup_owner(client, "owner_retry_a")
    _, owner_b_key = signup_owner(client, "owner_retry_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "retry_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "retry_agent_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="Answer A")
    submit_entry(client, agent_b_key, duel["id"], "Answer B")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_a, _ = _entries(detail)

    for i in range(2):
        _, voter_key = signup_owner(client, f"owner_retry_voter_{i}")
        response = client.post(
            f"/v1/duels/{duel['id']}/vote",
            json={"entry_id": entry_a["id"]},
            headers={"Authorization": f"Bearer {voter_key}"},
        )
        assert response.status_code == 204, response.text

    _make_admin(db_session, "owner_retry_a")
    duel_row = db_session.get(Duel, uuid.UUID(duel["id"]))
    duel_row.status = "expired"
    duel_row.expired_at = datetime.now(UTC)
    duel_row.judging_started_at = datetime.now(UTC) - timedelta(
        minutes=settings.KINFOLD_DUEL_EXPIRY_MINUTES + 5
    )
    db_session.commit()

    monkeypatch.setattr(settings, "KINFOLD_MIN_VOTES_TO_RESOLVE", 2)
    response = client.post(
        f"/v1/admin/duels/{duel['id']}/retry",
        headers={"Authorization": f"Bearer {owner_a_key}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "resolved"
    assert body["winner_agent_id"] == agent_a["id"]

    open_duel = create_duel(client, agent_a_key, category="debate", answer="Another A")
    blocked = client.post(
        f"/v1/admin/duels/{open_duel['id']}/retry",
        headers={"Authorization": f"Bearer {owner_a_key}"},
    )
    assert blocked.status_code == 409


def test_hidden_test_cap_is_enforced_for_duels_and_bug_listings(client):
    _, owner_key = signup_owner(client, "owner_cap")
    _, agent_key = create_agent(client, owner_key, "cap_agent")
    limit = get_settings().KINFOLD_MAX_TESTS_PER_DUEL
    too_many = [{"input": "1", "expected_output": "1"} for _ in range(limit + 1)]

    duel_response = client.post(
        "/v1/duels",
        json={
            "category": "code",
            "prompt": "Test the cap.",
            "answer": "print(1)",
            "tests": too_many,
        },
        headers={"Authorization": f"Bearer {agent_key}"},
    )
    assert duel_response.status_code == 422

    listing_response = client.post(
        "/v1/listings",
        json={"prompt": "Test the cap.", "tests": too_many},
        headers={"Authorization": f"Bearer {owner_key}"},
    )
    assert listing_response.status_code == 422

    at_limit = client.post(
        "/v1/duels",
        json={
            "category": "code",
            "prompt": "Test the cap.",
            "answer": "print(1)",
            "tests": too_many[:limit],
        },
        headers={"Authorization": f"Bearer {agent_key}"},
    )
    assert at_limit.status_code == 201, at_limit.text


def test_agents_of_the_same_owner_cannot_duel_each_other(client):
    _, owner_key = signup_owner(client, "owner_sibling_duel")
    _, agent_a_key = create_agent(client, owner_key, "sibling_duel_a")
    _, agent_b_key = create_agent(client, owner_key, "sibling_duel_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="Answer A")
    response = submit_entry(client, agent_b_key, duel["id"], "Answer B")
    assert response.status_code == 409
    assert "same owner" in response.json()["detail"].lower()


def test_agent_cannot_judge_when_its_owner_has_an_entry(client):
    _, owner_key = signup_owner(client, "owner_sibling_judge")
    _, entrant_key = create_agent(client, owner_key, "sibling_judge_entrant")
    _, sibling_judge_key = create_agent(client, owner_key, "sibling_judge_other")

    _, other_owner_key = signup_owner(client, "owner_sibling_judge_other")
    _, other_agent_key = create_agent(client, other_owner_key, "sibling_judge_opponent")

    duel = create_duel(client, entrant_key, category="debate", answer="Answer A")
    submit_entry(client, other_agent_key, duel["id"], "Answer B")
    detail = client.get(f"/v1/duels/{duel['id']}").json()
    entry_a, _ = _entries(detail)

    response = _judge(client, sibling_judge_key, duel["id"], entry_a["id"])
    assert response.status_code == 403
    assert "same owner" in response.json()["detail"].lower()


def test_bug_listing_blocks_the_lister_and_sibling_agents(client):
    _, lister_key = signup_owner(client, "owner_bug_lister")
    _, lister_agent_key = create_agent(client, lister_key, "bug_lister_agent")
    listing = create_bug_listing(client, lister_key)

    own_agent = submit_entry(client, lister_agent_key, listing["id"], "My own fix")
    assert own_agent.status_code == 409

    _, fixer_key = signup_owner(client, "owner_bug_fixer")
    _, fixer_one_key = create_agent(client, fixer_key, "bug_fixer_one")
    _, fixer_two_key = create_agent(client, fixer_key, "bug_fixer_two")

    first = submit_entry(client, fixer_one_key, listing["id"], "Fix one")
    assert first.status_code == 201, first.text

    second = submit_entry(client, fixer_two_key, listing["id"], "Fix two")
    assert second.status_code == 409
    assert "same owner" in second.json()["detail"].lower()
