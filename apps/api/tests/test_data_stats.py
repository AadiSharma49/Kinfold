from kinfold_api.config import get_settings
from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry


def test_data_stats_is_public_and_real(client):
    response = client.get("/v1/data/stats")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["target_for_first_training_run"] == get_settings().KINFOLD_FIRST_TRAINING_RUN_TARGET_PAIRS
    assert isinstance(body["open_weight_preference_pairs"], int)
    assert body["open_weight_preference_pairs"] >= 0


def test_data_stats_count_increases_after_a_real_resolved_duel(client):
    require_docker()
    before = client.get("/v1/data/stats").json()["open_weight_preference_pairs"]

    _, owner_a_key = signup_owner(client, "owner_stats_a")
    _, owner_b_key = signup_owner(client, "owner_stats_b")
    _, agent_a_key = create_agent(client, owner_a_key, "stats_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "stats_agent_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        prompt="Stats check — triple the input.",
        answer="n=int(input())\nprint(n*3)",
        tests=[{"input": "3", "expected_output": "9"}],
    )
    submit_entry(client, agent_b_key, duel["id"], "print(0)")

    after = client.get("/v1/data/stats").json()["open_weight_preference_pairs"]
    assert after == before + 1
