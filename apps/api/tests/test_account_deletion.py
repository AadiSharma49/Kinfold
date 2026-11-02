"""Self-service account deletion ("right to erasure") — see
docs/decisions.md, 2026-11-02. Anonymizes identity, disables agents,
revokes keys; does not touch duel content or the event log."""

from __future__ import annotations

from tests.helpers import create_agent, signup_owner


def test_request_deletion_anonymizes_handle_and_revokes_keys(client):
    owner, owner_key = signup_owner(client, "owner_delete_a")
    agent, agent_key = create_agent(client, owner_key, "delete_agent_a")

    response = client.post(
        "/v1/owners/me/request-deletion", headers={"Authorization": f"Bearer {owner_key}"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["handle"] != "owner_delete_a"
    assert body["handle"].startswith("deleted-")
    assert body["deleted_at"] is not None

    # The key that just made this request is now revoked.
    reuse = client.get("/v1/owners/me", headers={"Authorization": f"Bearer {owner_key}"})
    assert reuse.status_code == 401

    # The owner's agent is disabled and can't be used either.
    agent_check = client.get("/v1/agents/me", headers={"Authorization": f"Bearer {agent_key}"})
    assert agent_check.status_code == 401


def test_deleted_account_cannot_request_deletion_twice(client):
    _, owner_key = signup_owner(client, "owner_delete_twice")
    first = client.post(
        "/v1/owners/me/request-deletion", headers={"Authorization": f"Bearer {owner_key}"}
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/owners/me/request-deletion", headers={"Authorization": f"Bearer {owner_key}"}
    )
    assert second.status_code == 401  # the key was already revoked by the first request


def test_old_handle_404s_after_deletion(client):
    signup_owner(client, "owner_delete_profile")
    _, owner_key = signup_owner(client, "owner_delete_profile_b")
    create_agent(client, owner_key, "delete_profile_agent")

    client.post("/v1/owners/me/request-deletion", headers={"Authorization": f"Bearer {owner_key}"})

    response = client.get("/v1/owners/owner_delete_profile_b/profile")
    assert response.status_code == 404
