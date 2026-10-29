import json

from kinfold_api.config import get_settings
from scripts.export_preference_pairs import export_pairs
from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_entry


def _resolve_code_duel(client, creator_key, joiner_key, *, creator_answer, joiner_answer):
    duel = create_duel(
        client,
        creator_key,
        category="code",
        prompt="Double the input.",
        answer=creator_answer,
        tests=[{"input": "3", "expected_output": "6"}],
    )
    submit_entry(client, joiner_key, duel["id"], joiner_answer)
    return duel


def test_export_includes_an_open_weight_vs_open_weight_pair(client, db_session, tmp_path):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_export_ow_a")
    _, owner_b_key = signup_owner(client, "owner_export_ow_b")
    _, agent_a_key = create_agent(client, owner_a_key, "export_ow_agent_a", open_weights=True)
    _, agent_b_key = create_agent(client, owner_b_key, "export_ow_agent_b", open_weights=True)

    duel = _resolve_code_duel(
        client,
        agent_a_key,
        agent_b_key,
        creator_answer="print(int(input()) * 2)",
        joiner_answer="print(0)",
    )

    out = tmp_path / "pairs.jsonl"
    export_pairs(db_session, out)
    pairs = [json.loads(line) for line in out.read_text().splitlines()]
    match = next((p for p in pairs if p["duel_id"] == duel["id"]), None)
    assert match is not None
    assert match["chosen"] == "print(int(input()) * 2)"
    assert match["rejected"] == "print(0)"


def test_export_skips_a_pair_with_a_closed_weight_entrant(client, db_session, tmp_path):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_export_cw_a")
    _, owner_b_key = signup_owner(client, "owner_export_cw_b")
    _, agent_a_key = create_agent(client, owner_a_key, "export_cw_agent_a", open_weights=True)
    # model_family "gpt" forces open_weights=False server-side regardless of what's sent.
    _, agent_b_key = create_agent(
        client, owner_b_key, "export_cw_agent_b", model_family="gpt", open_weights=True
    )

    duel = _resolve_code_duel(
        client,
        agent_a_key,
        agent_b_key,
        creator_answer="print(int(input()) * 2)",
        joiner_answer="print(0)",
    )

    out = tmp_path / "pairs.jsonl"
    export_pairs(db_session, out)
    pairs = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(p["duel_id"] != duel["id"] for p in pairs)


def test_export_skips_a_draw(client, db_session, tmp_path):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_export_draw_a")
    _, owner_b_key = signup_owner(client, "owner_export_draw_b")
    _, agent_a_key = create_agent(client, owner_a_key, "export_draw_agent_a", open_weights=True)
    _, agent_b_key = create_agent(client, owner_b_key, "export_draw_agent_b", open_weights=True)

    duel = _resolve_code_duel(
        client,
        agent_a_key,
        agent_b_key,
        creator_answer="print(0)",
        joiner_answer="print(0)",
    )

    out = tmp_path / "pairs.jsonl"
    export_pairs(db_session, out)
    pairs = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(p["duel_id"] != duel["id"] for p in pairs)
    assert get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE >= 1
