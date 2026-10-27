"""Tests for the thin HTTP client, using httpx.MockTransport — no real
network, no Kinfold API process needed. This tests that the client builds
the right requests and handles responses/errors correctly; the business
logic it's calling is apps/api's own job and already has 32 tests there.
The real end-to-end path (this client against a live Kinfold API, through
every MCP tool) was verified manually and is described in the PR/commit
notes, not re-mocked here.
"""

from __future__ import annotations

import json

import httpx
import pytest

from kinfold_mcp.client import KinfoldClient, KinfoldClientError


def _transport(handler):
    return httpx.MockTransport(handler)


async def test_whoami_sends_bearer_token_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"name": "test-agent", "rating": 1200})

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    result = await client.whoami()

    assert captured["auth"] == "Bearer kf_live_test"
    assert captured["url"] == "http://api.test/v1/agents/me"
    assert result == {"name": "test-agent", "rating": 1200}


async def test_list_duels_passes_filters_as_query_params():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=[])

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    await client.list_duels(status="open", category="code")

    assert captured["params"] == {"status": "open", "category": "code"}


async def test_list_duels_omits_absent_filters():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json=[])

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    await client.list_duels()

    assert captured["params"] == {}


async def test_create_duel_omits_tests_when_not_given():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": "d1"})

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    await client.create_duel(category="debate", prompt="p", answer="a")

    assert "tests" not in captured["body"]


async def test_create_duel_includes_tests_when_given():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": "d1"})

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    tests = [{"input": "1", "expected_output": "1"}]
    await client.create_duel(category="code", prompt="p", answer="a", tests=tests)

    assert captured["body"]["tests"] == tests


async def test_submit_answer_posts_to_the_right_path():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": "e1"})

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    await client.submit_answer("duel-123", "my answer")

    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/duels/duel-123/entries"
    assert captured["body"] == {"answer": "my answer"}


async def test_leaderboard_truncates_to_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        agents = [{"name": f"agent-{i}", "rating": 1200 - i} for i in range(10)]
        return httpx.Response(200, json=agents)

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    top = await client.leaderboard(limit=3)

    assert len(top) == 3
    assert top[0]["name"] == "agent-0"


async def test_404_raises_kinfold_client_error_with_detail():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "not found"})

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))

    with pytest.raises(KinfoldClientError) as exc_info:
        await client.get_duel("missing-id")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "not found"


async def test_403_raises_with_detail_from_non_json_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="forbidden")

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))

    with pytest.raises(KinfoldClientError) as exc_info:
        await client.whoami()

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


async def test_204_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client = KinfoldClient("kf_live_test", base_url="http://api.test", transport=_transport(handler))
    result = await client._request("POST", "/v1/duels/d1/vote", json={"entry_id": "e1"})

    assert result is None
