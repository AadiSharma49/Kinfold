from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def require_docker() -> None:
    """Skip the calling test if the Docker daemon isn't reachable — code
    duels run submissions in real containers, so these tests need Docker."""
    import docker
    from docker.errors import DockerException

    try:
        docker.from_env().ping()
    except DockerException:
        pytest.skip("Docker daemon not reachable; skipping code-duel sandbox test")


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


def create_duel(
    client: TestClient,
    agent_key: str,
    *,
    category: str,
    prompt: str = "Write a function that adds two numbers.",
    answer: str = "print('placeholder')",
    tests: list[dict] | None = None,
) -> dict:
    payload: dict = {"category": category, "prompt": prompt, "answer": answer}
    if tests is not None:
        payload["tests"] = tests
    response = client.post(
        "/v1/duels",
        json=payload,
        headers={"Authorization": f"Bearer {agent_key}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def submit_entry(client: TestClient, agent_key: str, duel_id: str, answer: str):
    return client.post(
        f"/v1/duels/{duel_id}/entries",
        json={"answer": answer},
        headers={"Authorization": f"Bearer {agent_key}"},
    )
