import json

import pytest

from kinfold_api.config import get_settings
from kinfold_api.models import Agent, Duel, Owner
from kinfold_api.services.data_export import write_export
from tests.helpers import create_agent, create_duel, signup_owner, submit_entry


def _make_admin(db_session, handle: str) -> None:
    owner = db_session.query(Owner).filter_by(handle=handle).one()
    owner.is_admin = True
    db_session.commit()


def _entry_ids(client, duel_id: str) -> tuple[str, str]:
    entries = client.get(f"/v1/duels/{duel_id}").json()["entries"]
    by_slot = {e["slot"]: e["id"] for e in entries}
    return by_slot[1], by_slot[2]


def _resolve_with_human_votes(client, duel_id: str, winning_entry_id: str) -> None:
    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_di_voter_{duel_id[:8]}_{i}")
        response = client.post(
            f"/v1/duels/{duel_id}/vote",
            json={"entry_id": winning_entry_id},
            headers={"Authorization": f"Bearer {voter_key}"},
        )
        assert response.status_code == 204, response.text


def _exported_duel_ids(db_session, tmp_path) -> list[str]:
    out = tmp_path / "pairs.jsonl"
    write_export(db_session, out)
    return [json.loads(line)["duel_id"] for line in out.read_text().splitlines()]


CLOSED_OR_UNKNOWN_FAMILIES = [
    "gpt-4o",
    "openai-gpt",
    "claude-3",
    "gemini-pro",
    "grok-1",
    "o1",
    "o3",
    "o4",
]


@pytest.mark.parametrize("family", CLOSED_OR_UNKNOWN_FAMILIES)
def test_export_excludes_closed_or_unknown_families(client, db_session, tmp_path, family):
    """Default-deny: registration leaves open_weights=True for a family it
    doesn't recognize ("gpt-4o", "o1", ...), so only the export allowlist
    can keep these answers out of training data."""
    _, owner_a_key = signup_owner(client, f"owner_di_closed_{family.replace('-', '')}_a")
    _, owner_b_key = signup_owner(client, f"owner_di_closed_{family.replace('-', '')}_b")
    agent_a, agent_a_key = create_agent(
        client, owner_a_key, f"di_closed_{family.replace('-', '')}_a", model_family=family
    )
    _, agent_b_key = create_agent(
        client, owner_b_key, f"di_closed_{family.replace('-', '')}_b", model_family="llama"
    )

    # The registration bug this test is about: an unrecognized family is
    # still marked open_weights=True by the API.
    assert agent_a["open_weights"] is True

    duel = create_duel(client, agent_a_key, category="debate", answer="A answer")
    submit_entry(client, agent_b_key, duel["id"], "B answer")
    entry_a_id, _ = _entry_ids(client, duel["id"])
    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    assert duel["id"] not in _exported_duel_ids(db_session, tmp_path)


def test_export_includes_an_explicitly_allowed_open_family(client, db_session, tmp_path):
    _, owner_a_key = signup_owner(client, "owner_di_open_a")
    _, owner_b_key = signup_owner(client, "owner_di_open_b")
    _, agent_a_key = create_agent(client, owner_a_key, "di_open_agent_a", model_family="llama")
    _, agent_b_key = create_agent(client, owner_b_key, "di_open_agent_b", model_family="llama")

    duel = create_duel(client, agent_a_key, category="debate", answer="A answer")
    submit_entry(client, agent_b_key, duel["id"], "B answer")
    entry_a_id, _ = _entry_ids(client, duel["id"])
    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    assert duel["id"] in _exported_duel_ids(db_session, tmp_path)


def test_hidden_duel_is_excluded_from_export_and_stats(client, db_session, tmp_path):
    _, owner_a_key = signup_owner(client, "owner_di_hidden_duel_a")
    _, owner_b_key = signup_owner(client, "owner_di_hidden_duel_b")
    _, admin_key = signup_owner(client, "owner_di_hidden_duel_admin")
    _make_admin(db_session, "owner_di_hidden_duel_admin")
    _, agent_a_key = create_agent(client, owner_a_key, "di_hidden_duel_a")
    _, agent_b_key = create_agent(client, owner_b_key, "di_hidden_duel_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="A answer")
    submit_entry(client, agent_b_key, duel["id"], "B answer")
    entry_a_id, _ = _entry_ids(client, duel["id"])
    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    before = client.get("/v1/data/stats").json()["open_weight_preference_pairs"]
    assert before >= 1

    hide = client.post(
        f"/v1/admin/duels/{duel['id']}/hide",
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    assert hide.status_code == 200, hide.text

    after = client.get("/v1/data/stats").json()["open_weight_preference_pairs"]
    assert after == before - 1
    assert duel["id"] not in _exported_duel_ids(db_session, tmp_path)


def test_hidden_entry_is_excluded_from_export_and_stats(client, db_session, tmp_path):
    _, owner_a_key = signup_owner(client, "owner_di_hidden_entry_a")
    _, owner_b_key = signup_owner(client, "owner_di_hidden_entry_b")
    _, admin_key = signup_owner(client, "owner_di_hidden_entry_admin")
    _make_admin(db_session, "owner_di_hidden_entry_admin")
    _, agent_a_key = create_agent(client, owner_a_key, "di_hidden_entry_a")
    _, agent_b_key = create_agent(client, owner_b_key, "di_hidden_entry_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="A answer")
    submit_entry(client, agent_b_key, duel["id"], "B answer")
    entry_a_id, entry_b_id = _entry_ids(client, duel["id"])
    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    before = client.get("/v1/data/stats").json()["open_weight_preference_pairs"]
    assert before >= 1

    hide = client.post(
        f"/v1/admin/entries/{entry_b_id}/hide",
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    assert hide.status_code == 204, hide.text

    after = client.get("/v1/data/stats").json()["open_weight_preference_pairs"]
    assert after == before - 1
    assert duel["id"] not in _exported_duel_ids(db_session, tmp_path)


def test_hiding_an_entry_reverses_elo_and_removes_profile_stats(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_di_revert_a")
    _, owner_b_key = signup_owner(client, "owner_di_revert_b")
    _, admin_key = signup_owner(client, "owner_di_revert_admin")
    _make_admin(db_session, "owner_di_revert_admin")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "di_revert_agent_a")
    agent_b, agent_b_key = create_agent(client, owner_b_key, "di_revert_agent_b")

    rating_a_before = agent_a["rating"]
    rating_b_before = agent_b["rating"]

    duel = create_duel(client, agent_a_key, category="debate", answer="A answer")
    submit_entry(client, agent_b_key, duel["id"], "B answer")
    entry_a_id, entry_b_id = _entry_ids(client, duel["id"])
    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    db_session.expire_all()
    a_after_win = db_session.get(Agent, agent_a["id"])
    b_after_loss = db_session.get(Agent, agent_b["id"])
    assert a_after_win.rating > rating_a_before
    assert a_after_win.wins == 1
    assert b_after_loss.rating < rating_b_before
    assert b_after_loss.losses == 1

    hide = client.post(
        f"/v1/admin/entries/{entry_b_id}/hide",
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    assert hide.status_code == 204, hide.text

    db_session.expire_all()
    a_reverted = db_session.get(Agent, agent_a["id"])
    b_reverted = db_session.get(Agent, agent_b["id"])
    duel_row = db_session.get(Duel, duel["id"])

    assert duel_row.ratings_voided_at is not None
    assert a_reverted.rating == rating_a_before
    assert b_reverted.rating == rating_b_before
    assert a_reverted.wins == 0
    assert b_reverted.losses == 0

    profile_a = client.get(f"/v1/agents/{agent_a['name']}/profile").json()
    profile_b = client.get(f"/v1/agents/{agent_b['name']}/profile").json()
    assert profile_a["recent_duels"] == []
    assert profile_b["recent_duels"] == []
    # The reversal puts the record back at its 1200 / 0-0-0 starting
    # point; no win or loss from the voided duel remains.
    assert profile_a["category_record"]["debate"] == {
        "rating": 1200,
        "wins": 0,
        "losses": 0,
        "draws": 0,
    }
    assert profile_b["category_record"]["debate"] == {
        "rating": 1200,
        "wins": 0,
        "losses": 0,
        "draws": 0,
    }


def test_hiding_an_entry_before_resolution_blocks_elo_changes(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_di_prehide_a")
    _, owner_b_key = signup_owner(client, "owner_di_prehide_b")
    _, admin_key = signup_owner(client, "owner_di_prehide_admin")
    _make_admin(db_session, "owner_di_prehide_admin")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "di_prehide_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "di_prehide_agent_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="A answer")
    submit_entry(client, agent_b_key, duel["id"], "B answer")
    entry_a_id, entry_b_id = _entry_ids(client, duel["id"])

    hide = client.post(
        f"/v1/admin/entries/{entry_b_id}/hide",
        headers={"Authorization": f"Bearer {admin_key}"},
    )
    assert hide.status_code == 204, hide.text

    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    db_session.expire_all()
    duel_row = db_session.get(Duel, duel["id"])
    a_row = db_session.get(Agent, agent_a["id"])
    assert duel_row.status == "judging"  # no result invented from hidden content
    assert a_row.rating == agent_a["rating"]
    assert a_row.wins == 0


def test_suspected_ai_human_entry_is_excluded_from_export_and_stats(
    client, db_session, tmp_path
):
    """Regression guard: this rule already worked before the Stage 1
    change; the audit item said to test it explicitly."""
    _, owner_a_key = signup_owner(client, "owner_di_susp_ai_a")
    _, owner_human_key = signup_owner(client, "owner_di_susp_ai_h")
    _, agent_a_key = create_agent(client, owner_a_key, "di_susp_ai_agent_a")

    duel = create_duel(client, agent_a_key, category="debate", answer="A answer")
    human_entry = client.post(
        f"/v1/duels/{duel['id']}/human-entry",
        json={"answer": "short", "time_taken_seconds": 60, "large_paste_detected": True},
        headers={"Authorization": f"Bearer {owner_human_key}"},
    ).json()
    _resolve_with_human_votes(client, duel["id"], human_entry["id"])

    assert client.get("/v1/data/stats").json()["open_weight_preference_pairs"] == 0
    assert duel["id"] not in _exported_duel_ids(db_session, tmp_path)
