#!/usr/bin/env python3
"""
AIRClass Load Test - Simulate Multiple Concurrent WebRTC Viewers
대규모 시청자 부하 테스트 (30-100명)
"""

import asyncio
import aiohttp
import time
from datetime import datetime


class ViewerLoadTest:
    def __init__(self, base_url="http://localhost:8000", num_viewers=50):
        self.base_url = base_url
        self.num_viewers = num_viewers
        self.active_sessions = []
        self.results = {
            "success": 0,
            "failed": 0,
            "total_time": 0,
            "node_distribution": {},
        }

    async def create_viewer_session(self, session, viewer_id):
        """Create a single viewer session (get token)"""
        try:
            start_time = time.time()

            # Get authentication token
            async with session.post(
                f"{self.base_url}/api/token",
                params={
                    "user_type": "student",
                    "user_id": f"LoadTest-Viewer-{viewer_id}",
                },
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time

                    self.results["success"] += 1
                    self.results["total_time"] += elapsed

                    # Track which node this viewer got
                    webrtc_url = data.get("webrtc_url", "")
                    node = self.extract_node_from_url(webrtc_url)
                    if node:
                        self.results["node_distribution"][node] = (
                            self.results["node_distribution"].get(node, 0) + 1
                        )

                    return {
                        "viewer_id": viewer_id,
                        "status": "success",
                        "token": data.get("token"),
                        "webrtc_url": webrtc_url,
                        "node": node,
                        "response_time": elapsed,
                    }
                else:
                    self.results["failed"] += 1
                    return {
                        "viewer_id": viewer_id,
                        "status": "failed",
                        "error": f"HTTP {response.status}",
                    }
        except Exception as e:
            self.results["failed"] += 1
            return {"viewer_id": viewer_id, "status": "failed", "error": str(e)}

    def extract_node_from_url(self, url):
        """Extract node name from WebRTC URL"""
        # URL format: http://172.18.0.2:8889/live/stream/whep or http://host.docker.internal:58584/...
        if "host.docker.internal" in url:
            # Sub node (contains port mapping)
            port = url.split(":")[-1].split("/")[0]
            return f"sub-{port}"
        elif ":8889" in url:
            return "main"
        return "unknown"

    async def run_load_test(self):
        """Run the load test"""
        print("=" * 70)
        print(f"🔥 AIRClass Load Test - {self.num_viewers} Concurrent Viewers")
        print("=" * 70)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target: {self.base_url}")
        print(f"Viewers: {self.num_viewers}")
        print("-" * 70)

        start_time = time.time()

        # Create all viewer sessions concurrently
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.create_viewer_session(session, i)
                for i in range(1, self.num_viewers + 1)
            ]

            # Wait for all to complete
            results = await asyncio.gather(*tasks)

        total_elapsed = time.time() - start_time

        # Print results
        print("\n" + "=" * 70)
        print("📊 Load Test Results")
        print("=" * 70)
        print(f"✅ Successful: {self.results['success']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"⏱️  Total Time: {total_elapsed:.2f}s")

        if self.results["success"] > 0:
            avg_time = self.results["total_time"] / self.results["success"]
            print(f"📈 Avg Response Time: {avg_time * 1000:.2f}ms")
            print(f"🚀 Requests/Second: {self.results['success'] / total_elapsed:.2f}")

        print("\n" + "-" * 70)
        print("🖥️  Node Distribution:")
        print("-" * 70)
        for node, count in sorted(self.results["node_distribution"].items()):
            percentage = (
                (count / self.results["success"]) * 100
                if self.results["success"] > 0
                else 0
            )
            bar = "█" * int(percentage / 2)
            print(f"{node:15s}: {count:3d} viewers ({percentage:5.1f}%) {bar}")

        print("\n" + "=" * 70)
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="AIRClass Viewer Load Test")
    parser.add_argument(
        "-n",
        "--num-viewers",
        type=int,
        default=50,
        help="Number of concurrent viewers to simulate (default: 50)",
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Backend URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    test = ViewerLoadTest(base_url=args.url, num_viewers=args.num_viewers)
    await test.run_load_test()


if __name__ == "__main__":
    asyncio.run(main())
