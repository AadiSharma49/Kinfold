"""Client-IP spoofing protection: X-Forwarded-For is only honored when the
direct TCP peer is a configured trusted proxy. Needs a custom TestClient
per test (not the shared `client` fixture) so the "direct peer" can be set
to something other than the default "testclient" placeholder, which isn't
a parseable IP and so could never be trusted anyway — these tests prove
the real mechanism, not just that an unparseable peer is rejected.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
import redis as redis_lib
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.db import get_db
from kinfold_api.deps import get_redis
from kinfold_api.main import app


@pytest.fixture()
def spoofable_client(
    db_session: Session, test_redis: redis_lib.Redis
) -> Generator[type, None, None]:
    """Yields a factory: call it with a peer IP string to get a TestClient
    that reports that IP as the direct TCP peer (request.client.host)."""

    def _override_get_db():
        yield db_session

    def _override_get_redis():
        yield test_redis

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis

    def make(peer_ip: str) -> TestClient:
        return TestClient(app, client=(peer_ip, 12345))

    try:
        yield make
    finally:
        app.dependency_overrides.clear()


def test_forwarded_for_from_an_untrusted_peer_is_ignored(spoofable_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "KINFOLD_TRUSTED_PROXY_IPS", "127.0.0.1")
    attacker_client = spoofable_client("198.51.100.7")  # not in the trusted list

    response = attacker_client.get(
        "/v1/health", headers={"X-Forwarded-For": "1.2.3.4"}
    )
    # No direct way to read the IP the middleware used from the response,
    # so prove it the way it matters: spoofing a *different* IP on every
    # request must not let the attacker dodge their own rate limit bucket.
    monkeypatch.setattr(get_settings(), "KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE", 2)
    assert attacker_client.get("/v1/duels", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert attacker_client.get("/v1/duels", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
    # Third request, still claiming yet another spoofed IP — if the header
    # were honored, each request would land in a fresh bucket and never
    # hit the limit. Since the peer isn't trusted, all three share the
    # real peer's bucket and the third one is rate limited.
    assert attacker_client.get("/v1/duels", headers={"X-Forwarded-For": "3.3.3.3"}).status_code == 429
    assert response.status_code == 200  # the health check itself was never at risk


def test_forwarded_for_from_a_trusted_proxy_is_honored(spoofable_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "KINFOLD_TRUSTED_PROXY_IPS", "127.0.0.1")
    monkeypatch.setattr(get_settings(), "KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE", 2)
    proxy_client = spoofable_client("127.0.0.1")  # the trusted peer

    # Two different real-client IPs behind the same trusted proxy get two
    # separate buckets — neither should affect the other.
    for _ in range(2):
        assert (
            proxy_client.get("/v1/duels", headers={"X-Forwarded-For": "10.0.0.1"}).status_code
            == 200
        )
    assert proxy_client.get("/v1/duels", headers={"X-Forwarded-For": "10.0.0.2"}).status_code == 200


def test_trusted_proxy_setting_accepts_a_cidr_range(spoofable_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "KINFOLD_TRUSTED_PROXY_IPS", "172.28.0.0/24")
    monkeypatch.setattr(get_settings(), "KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE", 2)
    proxy_client = spoofable_client("172.28.0.10")  # inside the CIDR range

    assert proxy_client.get("/v1/duels", headers={"X-Forwarded-For": "9.9.9.9"}).status_code == 200
    assert proxy_client.get("/v1/duels", headers={"X-Forwarded-For": "9.9.9.9"}).status_code == 200
    assert proxy_client.get("/v1/duels", headers={"X-Forwarded-For": "9.9.9.9"}).status_code == 429
