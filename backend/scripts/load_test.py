"""A small, dependency-light load test (locust doesn't run in this sandbox
— see TROUBLESHOOTING.md). Hits a running instance of the API with real
concurrent requests via httpx.AsyncClient and reports real latency
percentiles. Not a substitute for a proper load-testing setup (no ramp-up,
no sustained-duration testing, no distributed load generation) but gives a
genuine, reproducible signal for a single-machine smoke test.

Usage:
    ./venv/bin/python scripts/load_test.py --base-url http://localhost:8000 \
        --email admin@example.com --password StrongPass123 \
        --concurrency 20 --requests 500
"""

import argparse
import asyncio
import statistics
import time

import httpx


async def worker(
    client: httpx.AsyncClient, path: str, headers: dict, latencies: list[float], errors: list[str]
) -> None:
    started = time.perf_counter()
    try:
        resp = await client.get(path, headers=headers)
        latencies.append((time.perf_counter() - started) * 1000)
        if resp.status_code >= 400:
            errors.append(f"{resp.status_code} on {path}")
    except httpx.RequestError as exc:
        errors.append(str(exc))


def percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    data_sorted = sorted(data)
    idx = min(int(len(data_sorted) * pct), len(data_sorted) - 1)
    return data_sorted[idx]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--path", default="/api/v1/products?page=1&page_size=25")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"email": args.email, "password": args.password}
        )
        if login.status_code != 200:
            print(f"Login failed ({login.status_code}): {login.text}")
            return
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        latencies: list[float] = []
        errors: list[str] = []
        semaphore = asyncio.Semaphore(args.concurrency)

        async def bounded_worker():
            async with semaphore:
                await worker(client, args.path, headers, latencies, errors)

        started = time.perf_counter()
        await asyncio.gather(*[bounded_worker() for _ in range(args.requests)])
        total_time = time.perf_counter() - started

    print(f"\n{args.requests} requests, concurrency={args.concurrency}, path={args.path}")
    print(f"Total wall time: {total_time:.2f}s  ({args.requests / total_time:.1f} req/s)")
    print(f"Errors: {len(errors)} / {args.requests}")
    if latencies:
        print(f"Latency ms  — min: {min(latencies):.1f}  mean: {statistics.mean(latencies):.1f}  "
              f"p50: {percentile(latencies, 0.50):.1f}  p95: {percentile(latencies, 0.95):.1f}  "
              f"p99: {percentile(latencies, 0.99):.1f}  max: {max(latencies):.1f}")
    if errors[:5]:
        print("Sample errors:", errors[:5])


if __name__ == "__main__":
    asyncio.run(main())
