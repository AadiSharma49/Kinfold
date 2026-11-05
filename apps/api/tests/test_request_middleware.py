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


def test_security_headers_are_on_every_response(client):
    response = client.get("/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in response.headers["permissions-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    # TestClient speaks plain HTTP, so HSTS must not be sent.
    assert "strict-transport-security" not in response.headers


def test_hsts_is_sent_when_the_request_arrived_over_https(client):
    response = client.get("/v1/health", headers={"X-Forwarded-Proto": "https"})
    assert "max-age=31536000" in response.headers["strict-transport-security"]


def test_rate_limited_responses_also_carry_security_headers(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE", 1)
    client.get("/v1/duels")
    limited = client.get("/v1/duels")
    assert limited.status_code == 429
    assert limited.headers["x-content-type-options"] == "nosniff"
    assert limited.headers["x-frame-options"] == "DENY"


def test_cors_allows_the_configured_web_origin(client):
    origin = get_settings().KINFOLD_WEB_URL.rstrip("/")
    preflight = client.options(
        "/v1/duels",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert preflight.status_code == 200, preflight.text
    assert preflight.headers["access-control-allow-origin"] == origin
    assert "GET" in preflight.headers["access-control-allow-methods"]

    simple = client.get("/v1/health", headers={"Origin": origin})
    assert simple.headers["access-control-allow-origin"] == origin


def test_cors_rejects_an_unknown_origin(client):
    preflight = client.options(
        "/v1/duels",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
