"""A simple load test against a running API — concurrent requests on a mix
of public read endpoints (what real traffic mostly is), reporting
throughput and latency percentiles. Not a substitute for a real load-
testing tool (k6, Locust) for a pre-launch capacity decision — this is a
quick, honest sanity check, with real numbers written up in
docs/progress.md, not a claim of rigorous benchmarking.

Run with:
    uv run python scripts/load_test.py [--concurrency 20] [--requests 200]

Needs a running API (and some seeded data helps — run scripts/seed.py
first — but it works against an empty database too, just with smaller
response bodies).
"""

from __future__ import annotations

import argparse
import asyncio
import time

import httpx

BASE = "http://localhost:8000"
# /v1/agents already returns agents sorted by rating — it's the
# leaderboard data, there's no separate /v1/leaderboard endpoint.
READ_PATHS = ["/v1/health", "/v1/duels", "/v1/agents", "/v1/data/stats"]


async def _one_request(client: httpx.AsyncClient, path: str) -> tuple[int, float]:
    start = time.perf_counter()
    try:
        response = await client.get(path)
        return response.status_code, (time.perf_counter() - start) * 1000
    except httpx.HTTPError:
        return 0, (time.perf_counter() - start) * 1000


async def run(concurrency: int, total_requests: int) -> None:
    results: list[tuple[int, float]] = []
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded(path: str):
            async with semaphore:
                results.append(await _one_request(client, path))

        start = time.perf_counter()
        await asyncio.gather(
            *(bounded(READ_PATHS[i % len(READ_PATHS)]) for i in range(total_requests))
        )
        wall_seconds = time.perf_counter() - start

    latencies = sorted(ms for _, ms in results)
    statuses = [code for code, _ in results]
    errors = sum(1 for code in statuses if code != 200)

    def pct(p: float) -> float:
        idx = min(len(latencies) - 1, int(len(latencies) * p))
        return latencies[idx]

    print(f"Requests: {total_requests}, concurrency: {concurrency}")
    print(f"Wall time: {wall_seconds:.2f}s — {total_requests / wall_seconds:.1f} req/s")
    print(f"Errors (non-200): {errors}/{total_requests}")
    print(
        f"Latency — p50: {pct(0.50):.0f}ms  p95: {pct(0.95):.0f}ms  "
        f"p99: {pct(0.99):.0f}ms  max: {latencies[-1]:.0f}ms"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests", type=int, default=200)
    args = parser.parse_args()

    asyncio.run(run(args.concurrency, args.requests))
