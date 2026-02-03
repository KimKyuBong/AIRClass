import argparse
import asyncio
import os
import time

import httpx


async def worker(
    client: httpx.AsyncClient, base_url: str, worker_id: int, n: int
) -> int:
    ok = 0
    for i in range(n):
        r = await client.get(f"{base_url}/api/ai/health")
        if r.status_code == 200:
            ok += 1
    return ok


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url", default=os.getenv("BASE_URL", "http://localhost:8000")
    )
    parser.add_argument(
        "--concurrency", type=int, default=int(os.getenv("CONCURRENCY", "20"))
    )
    parser.add_argument(
        "--requests", type=int, default=int(os.getenv("REQUESTS", "200"))
    )
    args = parser.parse_args()

    per_worker = max(args.requests // args.concurrency, 1)
    total = per_worker * args.concurrency

    async with httpx.AsyncClient(timeout=5.0) as client:
        start = time.time()
        results = await asyncio.gather(
            *[
                worker(client, args.base_url, i, per_worker)
                for i in range(args.concurrency)
            ]
        )
        elapsed = time.time() - start

    ok = sum(results)
    rps = ok / elapsed if elapsed > 0 else 0
    print(f"total={total} ok={ok} elapsed={elapsed:.2f}s rps={rps:.1f}")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
