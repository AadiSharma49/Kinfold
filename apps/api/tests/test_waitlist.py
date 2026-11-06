from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kinfold_api.models import WaitlistEntry

VALID = {"email": "ada@example.com", "role": "researcher", "bring": "datasets"}


def _count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(WaitlistEntry)) or 0


def test_waitlist_stores_normalized_entry(client, db_session: Session) -> None:
    response = client.post(
        "/v1/waitlist",
        json={"email": "  ADA@Example.COM ", "role": "researcher", "bring": "  datasets  "},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    entry = db_session.scalar(select(WaitlistEntry))
    assert entry is not None
    assert entry.email == "ada@example.com"
    assert entry.role == "researcher"
    assert entry.bring == "datasets"
    assert entry.created_at is not None


def test_waitlist_blank_bring_is_stored_as_null(client, db_session: Session) -> None:
    response = client.post("/v1/waitlist", json={**VALID, "bring": "   "})

    assert response.status_code == 200
    entry = db_session.scalar(select(WaitlistEntry))
    assert entry is not None
    assert entry.bring is None


def test_waitlist_duplicate_is_idempotent(client, db_session: Session) -> None:
    first = client.post("/v1/waitlist", json=VALID)
    second = client.post("/v1/waitlist", json={**VALID, "email": "ADA@EXAMPLE.COM"})

    assert first.json()["status"] == "ok"
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert second.json()["message"] == "You're already on the list."
    assert _count(db_session) == 1


def test_waitlist_honeypot_is_silent_and_not_stored(client, db_session: Session) -> None:
    response = client.post("/v1/waitlist", json={**VALID, "company": "Spam Inc"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert _count(db_session) == 0


def test_waitlist_rejects_bad_input(client, db_session: Session) -> None:
    payloads = [
        {**VALID, "email": "not-an-email"},
        {**VALID, "email": "a@" + ("b" * 320) + ".com"},
        {**VALID, "role": "unknown role"},
        {**VALID, "bring": "x" * 281},
    ]

    for payload in payloads:
        response = client.post("/v1/waitlist", json=payload)
        assert response.status_code == 422, payload

    assert _count(db_session) == 0
