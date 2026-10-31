from kinfold_api.config import get_settings
from kinfold_api.constants import TRAP_PRAISE_SCORE_THRESHOLD
from kinfold_api.models import Agent, Duel
from kinfold_api.services.duels import submit_entry
from tests.helpers import create_agent, create_duel, signup_owner, submit_human_entry


def _judge(client, agent_key, duel_id, entry_id, **overrides):
    body = {
        "entry_id": entry_id,
        "strengths": "Clear and concrete.",
        "weaknesses": "A bit short.",
        "verdict": "Entry A is more convincing.",
        "score": 7,
        **overrides,
    }
    return client.post(
        f"/v1/duels/{duel_id}/judgments",
        json=body,
        headers={"Authorization": f"Bearer {agent_key}"},
    )


_voter_counter = 0


def _resolve_with_human_votes(client, duel_id, winning_entry_id):
    global _voter_counter
    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for _ in range(min_votes):
        _voter_counter += 1
        _, voter_key = signup_owner(client, f"owner_integrity_voter_{_voter_counter}")
        client.post(
            f"/v1/duels/{duel_id}/vote",
            json={"entry_id": winning_entry_id},
            headers={"Authorization": f"Bearer {voter_key}"},
        )


def test_judgment_with_personal_comment_is_rejected(client):
    _, owner_a_key = signup_owner(client, "owner_mod_a")
    _, owner_b_key = signup_owner(client, "owner_mod_b")
    _, owner_c_key = signup_owner(client, "owner_mod_c")
    _, agent_a_key = create_agent(client, owner_a_key, "mod_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "mod_agent_b")
    _, agent_c_key = create_agent(client, owner_c_key, "mod_agent_c")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")
    submit_entry_response = client.post(
        f"/v1/duels/{duel['id']}/entries",
        json={"answer": "B's answer"},
        headers={"Authorization": f"Bearer {agent_b_key}"},
    )
    entry_id = submit_entry_response.json()["id"]

    response = _judge(
        client,
        agent_c_key,
        duel["id"],
        entry_id,
        weaknesses="This probably grew up poor and it shows in the writing.",
    )
    assert response.status_code == 400, response.text
    assert "person" in response.json()["detail"]


def test_trap_entry_is_never_exposed_in_any_response(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_trap_expose_a")
    _, owner_b_key = signup_owner(client, "owner_trap_expose_b")
    _, agent_a_key = create_agent(client, owner_a_key, "trap_expose_a")
    agent_b, agent_b_key = create_agent(client, owner_b_key, "trap_expose_b")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")

    duel_row = db_session.get(Duel, duel["id"])
    agent_row = db_session.get(Agent, agent_b["id"])
    submit_entry(
        db_session, duel=duel_row, agent=agent_row, answer="Deliberately bad answer.", is_trap=True
    )

    detail = client.get(f"/v1/duels/{duel['id']}").json()
    assert "is_trap" not in str(detail)  # crude but effective: field never serialized at all
    for entry in detail["entries"]:
        assert "is_trap" not in entry

    trap_entry_id = next(e["id"] for e in detail["entries"] if e["answer"] == "Deliberately bad answer.")
    _resolve_with_human_votes(client, duel["id"], trap_entry_id)

    resolved_detail = client.get(f"/v1/duels/{duel['id']}").json()
    assert "is_trap" not in str(resolved_detail)
    for entry in resolved_detail["entries"]:
        assert "is_trap" not in entry


def test_judge_rating_drops_for_praising_a_trap_even_if_it_wins(client, db_session):
    _, owner_a_key = signup_owner(client, "owner_trap_praise_a")
    _, owner_trap_key = signup_owner(client, "owner_trap_praise_trap")
    _, owner_judge_key = signup_owner(client, "owner_trap_praise_j")
    _, agent_a_key = create_agent(client, owner_a_key, "trap_praise_a")
    trap_agent, trap_agent_key = create_agent(client, owner_trap_key, "trap_praise_trap")
    judge_agent, judge_key = create_agent(client, owner_judge_key, "trap_praise_judge")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's real answer")

    duel_row = db_session.get(Duel, duel["id"])
    trap_row = db_session.get(Agent, trap_agent["id"])
    trap_entry = submit_entry(
        db_session, duel=duel_row, agent=trap_row, answer="Deliberately bad answer.", is_trap=True
    )
    trap_entry_id = str(trap_entry.id)

    judge_response = _judge(
        client,
        judge_key,
        duel["id"],
        trap_entry_id,
        score=TRAP_PRAISE_SCORE_THRESHOLD,
        verdict="This is actually the stronger answer.",
    )
    assert judge_response.status_code == 201, judge_response.text

    # Humans also pick the trap (it fooled everyone) — agreement-based
    # scoring alone would have rewarded the judge; the trap check must
    # still penalize it.
    _resolve_with_human_votes(client, duel["id"], trap_entry_id)

    judge_profile = client.get(f"/v1/agents/{judge_agent['name']}").json()
    assert judge_profile["judge_rating"] == 1200 - get_settings().KINFOLD_JUDGE_RATING_K_FACTOR


def test_entrant_can_rate_a_judgment_useful(client):
    _, owner_a_key = signup_owner(client, "owner_useful_a")
    _, owner_b_key = signup_owner(client, "owner_useful_b")
    _, owner_judge_key = signup_owner(client, "owner_useful_j")
    _, owner_bystander_key = signup_owner(client, "owner_useful_bystander")
    _, agent_a_key = create_agent(client, owner_a_key, "useful_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "useful_agent_b")
    _, judge_key = create_agent(client, owner_judge_key, "useful_judge")
    _, bystander_agent_key = create_agent(client, owner_bystander_key, "useful_bystander_agent")

    duel = create_duel(client, agent_a_key, category="explain", answer="A's answer")
    entry_response = client.post(
        f"/v1/duels/{duel['id']}/entries",
        json={"answer": "B's answer"},
        headers={"Authorization": f"Bearer {agent_b_key}"},
    )
    entry_a_id = client.get(f"/v1/duels/{duel['id']}").json()["entries"][0]["id"]

    judgment = _judge(client, judge_key, duel["id"], entry_a_id).json()
    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    # A bystander (not the entrant this judgment critiqued) can't rate it.
    forbidden = client.post(
        f"/v1/judgments/{judgment['id']}/useful",
        json={"useful": True},
        headers={"Authorization": f"Bearer {bystander_agent_key}"},
    )
    assert forbidden.status_code == 403, forbidden.text

    # The actual entrant (agent A, whose entry was critiqued) can.
    allowed = client.post(
        f"/v1/judgments/{judgment['id']}/useful",
        json={"useful": True},
        headers={"Authorization": f"Bearer {agent_a_key}"},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["entrant_rated_useful"] is True

    after = client.get(f"/v1/duels/{duel['id']}/judgments").json()
    assert after[0]["entrant_rated_useful"] is True
    assert entry_response.status_code == 201


def test_a_human_entrant_can_rate_a_judgment_on_their_own_entry_useful(client):
    _, owner_a_key = signup_owner(client, "owner_useful_human_a")
    _, owner_human_key = signup_owner(client, "owner_useful_human_entrant")
    _, owner_judge_key = signup_owner(client, "owner_useful_human_j")
    _, agent_a_key = create_agent(client, owner_a_key, "useful_human_agent_a")
    _, judge_key = create_agent(client, owner_judge_key, "useful_human_judge")

    duel = create_duel(client, agent_a_key, category="hinglish", answer="A's answer")
    human_entry = submit_human_entry(client, owner_human_key, duel["id"], "Human's answer").json()

    judgment = _judge(client, judge_key, duel["id"], human_entry["id"]).json()
    _resolve_with_human_votes(client, duel["id"], human_entry["id"])

    response = client.post(
        f"/v1/judgments/{judgment['id']}/useful",
        json={"useful": False},
        headers={"Authorization": f"Bearer {owner_human_key}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["entrant_rated_useful"] is False


def test_agreement_only_critiques_are_collapsed_to_the_bottom(client):
    _, owner_a_key = signup_owner(client, "owner_collapse_a")
    _, owner_b_key = signup_owner(client, "owner_collapse_b")
    _, owner_judge1_key = signup_owner(client, "owner_collapse_j1")
    _, owner_judge2_key = signup_owner(client, "owner_collapse_j2")
    _, agent_a_key = create_agent(client, owner_a_key, "collapse_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "collapse_agent_b")
    _, judge1_key = create_agent(client, owner_judge1_key, "collapse_judge1")
    _, judge2_key = create_agent(client, owner_judge2_key, "collapse_judge2")

    duel = create_duel(client, agent_a_key, category="debate", answer="A's answer")
    client.post(
        f"/v1/duels/{duel['id']}/entries",
        json={"answer": "B's answer"},
        headers={"Authorization": f"Bearer {agent_b_key}"},
    )
    entry_a_id = client.get(f"/v1/duels/{duel['id']}").json()["entries"][0]["id"]

    # judge1: agreement-only, barely any text.
    _judge(
        client,
        judge1_key,
        duel["id"],
        entry_a_id,
        strengths="ok",
        weaknesses="na",
        verdict="agree",
    )
    # judge2: substantive critique.
    _judge(
        client,
        judge2_key,
        duel["id"],
        entry_a_id,
        strengths="Cites a concrete example and addresses the counterargument directly.",
        weaknesses="Could use a source for the statistic in paragraph two.",
        verdict="Entry A is more convincing because it engages with the opposing view.",
    )

    _resolve_with_human_votes(client, duel["id"], entry_a_id)

    judgments = client.get(f"/v1/duels/{duel['id']}/judgments").json()
    assert len(judgments) == 2
    assert judgments[0]["agent_name"] == "collapse_judge2"
    assert judgments[0]["is_substantive"] is True
    assert judgments[1]["agent_name"] == "collapse_judge1"
    assert judgments[1]["is_substantive"] is False
