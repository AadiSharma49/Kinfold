import json

from kinfold_api.config import get_settings
from kinfold_api.models import Agent, Duel
from kinfold_api.services.data_export import write_export
from kinfold_api.services.duels import submit_entry
from kinfold_api.services.pii_scrub import scrub_pii
from tests.helpers import create_agent, create_duel, require_docker, signup_owner, submit_human_entry


def _resolve_with_human_votes(client, duel_id, winning_entry_id):
    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_dataexport_voter_{duel_id[:8]}_{i}")
        client.post(
            f"/v1/duels/{duel_id}/vote",
            json={"entry_id": winning_entry_id},
            headers={"Authorization": f"Bearer {voter_key}"},
        )


def test_scrub_pii_redacts_email_phone_and_kinfold_key():
    text = "Contact me at a@example.com or 555-123-4567. Key: kf_live_abcdefghijklmnop"
    scrubbed = scrub_pii(text)
    assert "a@example.com" not in scrubbed
    assert "555-123-4567" not in scrubbed
    assert "kf_live_abcdefghijklmnop" not in scrubbed
    assert "[redacted-email]" in scrubbed
    assert "[redacted-phone]" in scrubbed
    assert "[redacted-kinfold-key]" in scrubbed


def test_export_tags_human_vs_agent_and_scrubs_pii(client, db_session, tmp_path):
    _, owner_a_key = signup_owner(client, "owner_dataexport_a")
    _, owner_human_key = signup_owner(client, "owner_dataexport_human")
    _, agent_a_key = create_agent(client, owner_a_key, "dataexport_agent_a")

    duel = create_duel(
        client, agent_a_key, category="debate", answer="A real answer, email me at x@example.com"
    )
    human_entry = submit_human_entry(client, owner_human_key, duel["id"], "Human's answer").json()
    _resolve_with_human_votes(client, duel["id"], human_entry["id"])

    out = tmp_path / "pairs.jsonl"
    manifest = write_export(db_session, out)
    pairs = [json.loads(line) for line in out.read_text().splitlines()]
    match = next(p for p in pairs if p["duel_id"] == duel["id"])

    assert match["chosen_is_human"] is True
    assert match["rejected_is_human"] is False
    assert "x@example.com" not in match["rejected"]
    assert manifest.pair_count >= 1


def test_export_skips_duels_with_a_trap_entry(client, db_session, tmp_path):
    _, owner_a_key = signup_owner(client, "owner_dataexport_trap_a")
    _, owner_trap_key = signup_owner(client, "owner_dataexport_trap_t")
    _, agent_a_key = create_agent(client, owner_a_key, "dataexport_trap_a")
    trap_agent, _trap_agent_key = create_agent(client, owner_trap_key, "dataexport_trap_t")

    duel = create_duel(client, agent_a_key, category="debate", answer="A real answer")

    duel_row = db_session.get(Duel, duel["id"])
    trap_row = db_session.get(Agent, trap_agent["id"])
    trap_entry = submit_entry(
        db_session, duel=duel_row, agent=trap_row, answer="Trap answer", is_trap=True
    )

    _resolve_with_human_votes(client, duel["id"], str(trap_entry.id))

    out = tmp_path / "pairs.jsonl"
    manifest = write_export(db_session, out)
    pairs = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(p["duel_id"] != duel["id"] for p in pairs)
    assert manifest.duels_skipped_trap >= 1


def test_export_skips_duels_with_a_suspected_ai_human_entry(client, db_session, tmp_path):
    _, owner_a_key = signup_owner(client, "owner_dataexport_susp_a")
    _, owner_human_key = signup_owner(client, "owner_dataexport_susp_h")
    _, agent_a_key = create_agent(client, owner_a_key, "dataexport_susp_agent_a")

    duel = create_duel(client, agent_a_key, category="debate", answer="A real answer")
    submit_response = client.post(
        f"/v1/duels/{duel['id']}/human-entry",
        json={"answer": "short", "time_taken_seconds": 60, "large_paste_detected": True},
        headers={"Authorization": f"Bearer {owner_human_key}"},
    )
    human_entry = submit_response.json()
    _resolve_with_human_votes(client, duel["id"], human_entry["id"])

    out = tmp_path / "pairs.jsonl"
    manifest = write_export(db_session, out)
    pairs = [json.loads(line) for line in out.read_text().splitlines()]
    assert all(p["duel_id"] != duel["id"] for p in pairs)
    assert manifest.duels_skipped_suspected_ai >= 1


def test_export_deduplicates_identical_pairs(client, db_session, tmp_path):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_dataexport_dup_a")
    _, owner_b_key = signup_owner(client, "owner_dataexport_dup_b")
    _, owner_c_key = signup_owner(client, "owner_dataexport_dup_c")
    _, owner_d_key = signup_owner(client, "owner_dataexport_dup_d")
    _, agent_a_key = create_agent(client, owner_a_key, "dataexport_dup_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "dataexport_dup_agent_b")
    _, agent_c_key = create_agent(client, owner_c_key, "dataexport_dup_agent_c")
    _, agent_d_key = create_agent(client, owner_d_key, "dataexport_dup_agent_d")

    body = {
        "category": "code",
        "prompt": "Double the input.",
        "answer": "n=int(input())\nprint(n*2)",
        "tests": [{"input": "3", "expected_output": "6"}],
    }
    duel1 = client.post(
        "/v1/duels", json=body, headers={"Authorization": f"Bearer {agent_a_key}"}
    ).json()
    client.post(
        f"/v1/duels/{duel1['id']}/entries",
        json={"answer": "print(0)"},
        headers={"Authorization": f"Bearer {agent_b_key}"},
    )
    duel2 = client.post(
        "/v1/duels", json=body, headers={"Authorization": f"Bearer {agent_c_key}"}
    ).json()
    client.post(
        f"/v1/duels/{duel2['id']}/entries",
        json={"answer": "print(0)"},
        headers={"Authorization": f"Bearer {agent_d_key}"},
    )

    out = tmp_path / "pairs.jsonl"
    manifest = write_export(db_session, out)
    pairs = [json.loads(line) for line in out.read_text().splitlines()]
    matching = [p for p in pairs if p["duel_id"] in (duel1["id"], duel2["id"])]
    assert len(matching) == 1  # the second, identical pair was deduplicated
    assert manifest.duels_skipped_duplicate >= 1


def test_export_writes_manifest_and_dataset_card(client, db_session, tmp_path):
    _, owner_a_key = signup_owner(client, "owner_dataexport_card_a")
    _, agent_a_key = create_agent(client, owner_a_key, "dataexport_card_agent_a")
    create_duel(client, agent_a_key, category="debate", answer="x")

    out = tmp_path / "pairs.jsonl"
    write_export(db_session, out)

    manifest_path = out.with_suffix(".manifest.json")
    card_path = out.parent / "DATASET_CARD.md"
    assert manifest_path.exists()
    assert card_path.exists()

    manifest_data = json.loads(manifest_path.read_text())
    assert "pair_count" in manifest_data
    assert "version" in manifest_data
    assert "Kinfold preference pairs" in card_path.read_text()
