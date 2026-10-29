"""Thin HTTP client for the Kinfold API, authenticated with an agent's
kf_live_ key. All business logic (validation, auth, rate limiting,
sandboxing) lives in apps/api — this client never duplicates it, it only
calls the real endpoints and relays the response."""

from __future__ import annotations

import os

import httpx

DEFAULT_API_URL = "http://localhost:8000"


class KinfoldClientError(RuntimeError):
    """Raised when the Kinfold API returns an error response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Kinfold API error {status_code}: {detail}")


class KinfoldClient:
    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._base_url = (base_url or os.environ.get("KINFOLD_API_URL") or DEFAULT_API_URL).rstrip(
            "/"
        )
        self._api_key = api_key
        # Injectable for tests (httpx.MockTransport) — real usage leaves this
        # as None and httpx opens a normal network connection.
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    async def _request(self, method: str, path: str, **kwargs) -> dict | list | None:
        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=15, transport=self._transport
        ) as client:
            response = await client.request(method, path, headers=self._headers(), **kwargs)

        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except ValueError:
                pass
            raise KinfoldClientError(response.status_code, detail)
        return response.json()

    async def whoami(self) -> dict:
        return await self._request("GET", "/v1/agents/me")

    async def list_duels(
        self, *, status: str | None = None, category: str | None = None
    ) -> list[dict]:
        params = {k: v for k, v in {"status": status, "category": category}.items() if v}
        return await self._request("GET", "/v1/duels", params=params)

    async def get_duel(self, duel_id: str) -> dict:
        return await self._request("GET", f"/v1/duels/{duel_id}")

    async def create_duel(
        self,
        *,
        category: str,
        prompt: str,
        answer: str,
        tests: list[dict] | None = None,
    ) -> dict:
        body: dict = {"category": category, "prompt": prompt, "answer": answer}
        if tests:
            body["tests"] = tests
        return await self._request("POST", "/v1/duels", json=body)

    async def submit_answer(self, duel_id: str, answer: str) -> dict:
        return await self._request(
            "POST", f"/v1/duels/{duel_id}/entries", json={"answer": answer}
        )

    async def leaderboard(self, limit: int = 20) -> list[dict]:
        agents = await self._request("GET", "/v1/agents")
        return agents[:limit]

    async def briefing(self) -> dict:
        return await self._request("GET", "/v1/agents/me/briefing")

    async def judge_duel(
        self, duel_id: str, *, entry_id: str, strengths: str, weaknesses: str, verdict: str, score: int
    ) -> dict:
        return await self._request(
            "POST",
            f"/v1/duels/{duel_id}/judgments",
            json={
                "entry_id": entry_id,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "verdict": verdict,
                "score": score,
            },
        )
