"""Per-category ratings for agents and humans — see docs/decisions.md,
2026-11-02. Each category's rating is elo-updated independently of the
overall rating, using the same math and the same K-factor."""

from __future__ import annotations

from kinfold_api.config import get_settings
from tests.helpers import (
    create_agent,
    create_duel,
    require_docker,
    signup_owner,
    submit_entry,
    submit_human_entry,
)


def _resolve_with_human_votes(client, duel_id, winning_entry_id):
    min_votes = get_settings().KINFOLD_MIN_VOTES_TO_RESOLVE
    for i in range(min_votes):
        _, voter_key = signup_owner(client, f"owner_catrating_voter_{duel_id[:8]}_{i}")
        client.post(
            f"/v1/duels/{duel_id}/vote",
            json={"entry_id": winning_entry_id},
            headers={"Authorization": f"Bearer {voter_key}"},
        )


def test_agent_gains_both_overall_and_category_rating_on_a_win(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_catrating_a")
    _, owner_b_key = signup_owner(client, "owner_catrating_b")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "catrating_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "catrating_agent_b")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        answer="n=int(input())\nprint(n*2)",
        tests=[{"input": "3", "expected_output": "6"}],
    )
    submit_entry(client, agent_b_key, duel["id"], "print(0)")

    profile = client.get(f"/v1/agents/{agent_a['name']}/profile").json()
    assert profile["agent"]["rating"] > 1200
    assert profile["category_record"]["code"]["rating"] > 1200
    assert profile["category_record"]["code"]["wins"] == 1
    # This agent has never played a bugfix duel — no fabricated row.
    assert "bugfix" not in profile["category_record"]


def test_category_rating_is_separate_from_overall_rating(client):
    """An agent that wins a code duel, then loses a debate duel, should
    see its overall rating reflect both results but its two category
    ratings move independently — a code win doesn't inflate the debate
    number or vice versa."""
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_catrating_sep_a")
    _, owner_b_key = signup_owner(client, "owner_catrating_sep_b")
    _, owner_c_key = signup_owner(client, "owner_catrating_sep_c")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "catrating_sep_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "catrating_sep_agent_b")
    _, agent_c_key = create_agent(client, owner_c_key, "catrating_sep_agent_c")

    code_duel = create_duel(
        client,
        agent_a_key,
        category="code",
        answer="n=int(input())\nprint(n*2)",
        tests=[{"input": "3", "expected_output": "6"}],
    )
    submit_entry(client, agent_b_key, code_duel["id"], "print(0)")  # agent_a wins

    debate_duel = create_duel(client, agent_c_key, category="debate", answer="C's answer")
    submit_entry(client, agent_a_key, debate_duel["id"], "A's answer")
    detail = client.get(f"/v1/duels/{debate_duel['id']}").json()
    agent_c_entry_id = next(e["id"] for e in detail["entries"] if e["slot"] == 1)
    _resolve_with_human_votes(client, debate_duel["id"], agent_c_entry_id)  # agent_a loses

    profile = client.get(f"/v1/agents/{agent_a['name']}/profile").json()
    code_rating = profile["category_record"]["code"]["rating"]
    debate_rating = profile["category_record"]["debate"]["rating"]
    assert code_rating > 1200  # won its only code duel
    assert debate_rating < 1200  # lost its only debate duel
    assert profile["category_record"]["code"]["wins"] == 1
    assert profile["category_record"]["debate"]["losses"] == 1


def test_human_gets_an_overall_and_category_rating(client):
    _, owner_a_key = signup_owner(client, "owner_catrating_human_a")
    _, owner_human_key = signup_owner(client, "owner_catrating_human_b")
    _, agent_a_key = create_agent(client, owner_a_key, "catrating_human_agent_a")

    duel = create_duel(client, agent_a_key, category="hinglish", answer="AI's answer")
    entry = submit_human_entry(client, owner_human_key, duel["id"], "Human's answer").json()
    _resolve_with_human_votes(client, duel["id"], entry["id"])

    profile = client.get("/v1/owners/owner_catrating_human_b/profile").json()
    assert profile["owner"]["rating"] > 1200
    assert profile["owner"]["wins"] == 1
    assert profile["category_record"]["hinglish"]["rating"] > 1200
    assert profile["category_record"]["hinglish"]["wins"] == 1


def test_leaderboard_category_filter_only_lists_agents_with_that_category(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_catrating_lb_a")
    _, owner_b_key = signup_owner(client, "owner_catrating_lb_b")
    _, owner_c_key = signup_owner(client, "owner_catrating_lb_c")
    agent_a, agent_a_key = create_agent(client, owner_a_key, "catrating_lb_agent_a")
    _, agent_b_key = create_agent(client, owner_b_key, "catrating_lb_agent_b")
    agent_c, agent_c_key = create_agent(client, owner_c_key, "catrating_lb_agent_c")

    duel = create_duel(
        client,
        agent_a_key,
        category="code",
        answer="n=int(input())\nprint(n*2)",
        tests=[{"input": "3", "expected_output": "6"}],
    )
    submit_entry(client, agent_b_key, duel["id"], "print(0)")

    response = client.get("/v1/agents", params={"category": "code"})
    assert response.status_code == 200, response.text
    names = {a["name"] for a in response.json()}
    assert agent_a["name"] in names
    assert agent_c["name"] not in names  # never played a code duel

    for agent in response.json():
        assert agent["category_rating"] is not None

    bad_category = client.get("/v1/agents", params={"category": "not-a-real-category"})
    assert bad_category.status_code == 400
