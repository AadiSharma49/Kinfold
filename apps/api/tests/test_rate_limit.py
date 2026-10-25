from kinfold_api.config import get_settings
from tests.helpers import signup_owner


def test_rate_limit_returns_429(client):
    _, owner_key = signup_owner(client, "owner_rl")
    limit = get_settings().KINFOLD_RATE_LIMIT_PER_MINUTE

    last_response = None
    for _ in range(limit + 1):
        last_response = client.get("/v1/owners/me", headers={"Authorization": f"Bearer {owner_key}"})

    assert last_response is not None
    assert last_response.status_code == 429
