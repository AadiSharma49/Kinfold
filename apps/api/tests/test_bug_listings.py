from kinfold_api.constants import VERIFIED_CATEGORIES
from tests.helpers import create_agent, create_bug_listing, require_docker, signup_owner, submit_entry


def test_human_can_list_a_bug(client):
    _, owner_key = signup_owner(client, "owner_listing_a")
    listing = create_bug_listing(client, owner_key)

    assert listing["category"] == "bugfix"
    assert listing["status"] == "open"
    assert listing["created_by_human_owner_handle"] == "owner_listing_a"


def test_agent_cannot_create_a_bugfix_duel_directly(client):
    _, owner_key = signup_owner(client, "owner_listing_noagent")
    _, agent_key = create_agent(client, owner_key, "listing_noagent_agent")

    response = client.post(
        "/v1/duels",
        json={
            "category": "bugfix",
            "prompt": "trying to sneak a listing in",
            "answer": "n/a",
            "tests": [{"input": "", "expected_output": "1"}],
        },
        headers={"Authorization": f"Bearer {agent_key}"},
    )
    assert response.status_code == 422, response.text


def test_bugfix_category_is_verified_not_crowd():
    assert "bugfix" in VERIFIED_CATEGORIES


def test_lister_cannot_fix_their_own_listing(client):
    require_docker()
    _, owner_key = signup_owner(client, "owner_listing_self")
    _, agent_key = create_agent(client, owner_key, "listing_self_agent")
    listing = create_bug_listing(client, owner_key)

    response = submit_entry(client, agent_key, listing["id"], "print(0)")
    assert response.status_code == 409, response.text
    assert "own bug listing" in response.json()["detail"]


def test_same_agent_cannot_submit_two_fixes(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_listing_dup_a")
    _, owner_b_key = signup_owner(client, "owner_listing_dup_b")
    _, agent_b_key = create_agent(client, owner_b_key, "listing_dup_agent_b")
    listing = create_bug_listing(client, owner_a_key)

    first = submit_entry(client, agent_b_key, listing["id"], "n=int(input())\nprint(n*2)")
    assert first.status_code == 201, first.text

    second = submit_entry(client, agent_b_key, listing["id"], "n=int(input())\nprint(n*2)")
    assert second.status_code == 409, second.text
    assert "already submitted" in second.json()["detail"]


def test_two_agents_fix_a_listing_and_it_resolves(client):
    require_docker()
    _, owner_a_key = signup_owner(client, "owner_listing_resolve_a")
    _, owner_b_key = signup_owner(client, "owner_listing_resolve_b")
    _, owner_c_key = signup_owner(client, "owner_listing_resolve_c")
    _, agent_b_key = create_agent(client, owner_b_key, "listing_resolve_agent_b")
    _, agent_c_key = create_agent(client, owner_c_key, "listing_resolve_agent_c")

    listing = create_bug_listing(
        client,
        owner_a_key,
        prompt="Doubling function is broken.",
        tests=[{"input": "4", "expected_output": "8"}],
    )

    good_fix = submit_entry(client, agent_b_key, listing["id"], "n=int(input())\nprint(n*2)")
    assert good_fix.status_code == 201, good_fix.text
    assert good_fix.json()["slot"] == 1

    bad_fix = submit_entry(client, agent_c_key, listing["id"], "print(0)")
    assert bad_fix.status_code == 201, bad_fix.text
    assert bad_fix.json()["slot"] == 2

    resolved = client.get(f"/v1/duels/{listing['id']}").json()
    assert resolved["status"] == "resolved"
    assert resolved["winner_agent_id"] is not None
    assert resolved["created_by_human_owner_handle"] == "owner_listing_resolve_a"

    winning_entry = next(e for e in resolved["entries"] if e["id"] == good_fix.json()["id"])
    assert winning_entry["agent_name"] == "listing_resolve_agent_b"
