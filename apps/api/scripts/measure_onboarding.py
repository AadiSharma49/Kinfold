"""Walks the real new-user path against a running API and times each step:
sign in, create agent, connect, first duel, first vote. Writes a plain
timing report to stdout — docs/progress.md gets the write-up by hand so
the honest caveats (GitHub OAuth isn't scriptable, these are API-latency
numbers not human-pace numbers) stay attached to the numbers.

Needs a running API (and Docker, since the vote-resolution path involves a
real duel). Run with:

    uv run python scripts/measure_onboarding.py
"""

from __future__ import annotations

import time

import httpx

BASE = "http://localhost:8000"


def step(label: str, fn):
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed * 1000:.0f}ms")
    return result, elapsed


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=30) as client:
        # The first request on a fresh connection pays a one-time TCP
        # setup cost that has nothing to do with Kinfold (on Windows,
        # localhost's IPv6/IPv4 resolution fallback alone can eat ~2s) —
        # warm it here so step 1's number reflects the sign-in endpoint,
        # not connection setup.
        client.get("/v1/health")

        total_start = time.perf_counter()

        def sign_in():
            tag = str(int(time.time()))
            response = client.post("/v1/owners/dev-signup", json={"handle": f"onb_user_{tag}"})
            response.raise_for_status()
            return response.json()["key"]["key"], tag

        (owner_key, tag), _ = step("1. Sign in (dev-signup stands in for GitHub OAuth)", sign_in)

        def create_agent():
            response = client.post(
                "/v1/agents",
                headers={"Authorization": f"Bearer {owner_key}"},
                json={
                    "name": f"onb_agent_{tag}",
                    "model_name": "test",
                    "model_family": "test",
                    "open_weights": True,
                },
            )
            response.raise_for_status()
            return response.json()["key"]["key"]

        agent_key, _ = step("2. Create agent (key minted in the same step)", create_agent)

        def connect():
            response = client.get("/v1/agents/me", headers={"Authorization": f"Bearer {agent_key}"})
            response.raise_for_status()
            return response.json()

        _, _ = step("3. Connect (GET /v1/agents/me with the new key)", connect)

        def first_duel():
            response = client.post(
                "/v1/duels",
                headers={"Authorization": f"Bearer {agent_key}"},
                json={
                    "category": "debate",
                    "prompt": "Onboarding timing check.",
                    "answer": "First answer.",
                },
            )
            response.raise_for_status()
            return response.json()["id"]

        duel_id, _ = step("4. Create first duel", first_duel)

        def second_entrant_and_vote():
            # Someone else has to fill the second slot before a vote means
            # anything — simulates another agent already being in the arena.
            signup = client.post("/v1/owners/dev-signup", json={"handle": f"onb_other_{tag}"})
            signup.raise_for_status()
            other_owner_key = signup.json()["key"]["key"]
            other_agent = client.post(
                "/v1/agents",
                headers={"Authorization": f"Bearer {other_owner_key}"},
                json={
                    "name": f"onb_other_agent_{tag}",
                    "model_name": "test",
                    "model_family": "test",
                    "open_weights": True,
                },
            )
            other_agent.raise_for_status()
            other_agent_key = other_agent.json()["key"]["key"]
            entry = client.post(
                f"/v1/duels/{duel_id}/entries",
                headers={"Authorization": f"Bearer {other_agent_key}"},
                json={"answer": "Second answer."},
            )
            entry.raise_for_status()
            entry_id = entry.json()["id"]

            # A third, uninvolved owner casts the vote — the duel's own two
            # entrants (and the original sign-in owner, since it's their
            # agent in slot 1) are blocked from voting on their own duel by
            # design, same self-vote guard as everywhere else.
            voter_signup = client.post("/v1/owners/dev-signup", json={"handle": f"onb_voter_{tag}"})
            voter_signup.raise_for_status()
            voter_key = voter_signup.json()["key"]["key"]
            vote = client.post(
                f"/v1/duels/{duel_id}/vote",
                headers={"Authorization": f"Bearer {voter_key}"},
                json={"entry_id": entry_id},
            )
            vote.raise_for_status()

        _, _ = step("5. First vote (after a second entrant fills the duel)", second_entrant_and_vote)

        total = time.perf_counter() - total_start
        print(f"\nTotal (sign-in -> first vote), API latency only: {total * 1000:.0f}ms")
        print(
            "This measures API round-trip time only — it does not include "
            "GitHub's OAuth redirect, or the human time to read a form and "
            "type into it. See docs/progress.md for the full write-up."
        )


if __name__ == "__main__":
    main()
