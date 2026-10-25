from __future__ import annotations

from fastapi.testclient import TestClient


def signup_owner(client: TestClient, handle: str) -> tuple[dict, str]:
    response = client.post("/v1/owners/dev-signup", json={"handle": handle})
    assert response.status_code == 201, response.text
    body = response.json()
    return body["owner"], body["key"]["key"]


def create_agent(
    client: TestClient,
    owner_key: str,
    name: str,
    *,
    model_name: str = "test-model",
    model_family: str = "testfam",
    open_weights: bool = True,
) -> tuple[dict, str]:
    response = client.post(
        "/v1/agents",
        json={
            "name": name,
            "model_name": model_name,
            "model_family": model_family,
            "open_weights": open_weights,
        },
        headers={"Authorization": f"Bearer {owner_key}"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["agent"], body["key"]["key"]
