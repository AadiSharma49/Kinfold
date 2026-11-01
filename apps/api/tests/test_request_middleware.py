from kinfold_api.config import get_settings


def test_every_response_carries_a_request_id(client):
    response = client.get("/v1/health")
    assert "x-request-id" in response.headers


def test_passed_in_request_id_is_echoed_back(client):
    response = client.get("/v1/health", headers={"X-Request-Id": "test-fixed-id-123"})
    assert response.headers["x-request-id"] == "test-fixed-id-123"


def test_public_route_rate_limit_eventually_kicks_in(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE", 3)

    statuses = [client.get("/v1/duels").status_code for _ in range(4)]
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 429


def test_health_route_is_exempt_from_the_public_rate_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE", 1)

    # Limit set to 1, but /v1/health is excluded from the limiter entirely
    # (monitoring/orchestration shouldn't ever get 429'd) — calling it more
    # than the limit should never trip it.
    statuses = [client.get("/v1/health").status_code for _ in range(5)]
    assert all(s == 200 for s in statuses)
