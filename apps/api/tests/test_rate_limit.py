import redis as redis_lib

from kinfold_api.config import get_settings
from kinfold_api.services.rate_limit import enforce_rate_limit
from tests.helpers import signup_owner


def test_rate_limit_returns_429(client):
    _, owner_key = signup_owner(client, "owner_rl")
    limit = get_settings().KINFOLD_RATE_LIMIT_PER_MINUTE

    last_response = None
    for _ in range(limit + 1):
        last_response = client.get("/v1/owners/me", headers={"Authorization": f"Bearer {owner_key}"})

    assert last_response is not None
    assert last_response.status_code == 429


def test_counter_gets_a_ttl_even_when_the_key_already_exists(test_redis, monkeypatch):
    # Simulate a crashed old INCR that left a counter with no expiry: the
    # next request must repair the TTL instead of leaving the identifier
    # limited forever.
    fixed_time = 1_700_000_000
    monkeypatch.setattr("kinfold_api.services.rate_limit.time.time", lambda: fixed_time)
    bucket = f"ratelimit:ttl-check:{int(fixed_time // 60)}"
    test_redis.set(bucket, 5)

    enforce_rate_limit(test_redis, "ttl-check", 10)

    assert test_redis.ttl(bucket) > 0
    assert int(test_redis.get(bucket)) == 6


class _BrokenRedis:
    def register_script(self, script):
        def _raise(*args, **kwargs):
            raise redis_lib.ConnectionError("redis down")

        return _raise


def test_rate_limit_fails_open_when_redis_is_down():
    # Availability choice: a Redis outage must not take the whole API
    # down. The explicit tradeoff is documented in docs/security.md.
    enforce_rate_limit(_BrokenRedis(), "some-owner", 1)
