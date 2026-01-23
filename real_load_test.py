#!/usr/bin/env python3
"""
AIRClass Real WebRTC Load Test
실제 WebRTC WHEP 연결을 생성하여 부하 테스트
"""

import asyncio
import aiohttp
import time
from datetime import datetime


class RealWebRTCLoadTest:
    def __init__(self, base_url="http://localhost:8000", num_viewers=30):
        self.base_url = base_url
        self.num_viewers = num_viewers
        self.connections = []
        self.stats = {
            "token_success": 0,
            "token_failed": 0,
            "whep_success": 0,
            "whep_failed": 0,
            "total_time": 0,
        }

    async def create_whep_connection(self, session, viewer_id):
        """Create a real WebRTC WHEP connection"""
        try:
            start = time.time()

            # Step 1: Get authentication token
            async with session.post(
                f"{self.base_url}/api/token",
                params={"user_type": "student", "user_id": f"LoadTest-{viewer_id}"},
            ) as response:
                if response.status != 200:
                    self.stats["token_failed"] += 1
                    print(f"[시청자 #{viewer_id}] ❌ 토큰 발급 실패: {response.status}")
                    return None

                data = await response.json()
                webrtc_url = data.get("webrtc_url")
                self.stats["token_success"] += 1
                print(f"[시청자 #{viewer_id}] ✅ 토큰 발급 성공")

            # Step 2: Create SDP offer (simplified WHEP client)
            # This is a minimal SDP offer for receiving video/audio
            sdp_offer = """v=0
o=- 0 0 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0 1
a=msid-semantic: WMS
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:XXXX
a=ice-pwd:XXXXXXXXXXXXXXXXXXXXXXXX
a=ice-options:trickle
a=fingerprint:sha-256 XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX
a=setup:actpass
a=mid:0
a=recvonly
a=rtcp-mux
a=rtpmap:96 VP8/90000
a=rtcp-fb:96 nack
a=rtcp-fb:96 nack pli
m=audio 9 UDP/TLS/RTP/SAVPF 111
c=IN IP4 0.0.0.0
a=rtcp:9 IN IP4 0.0.0.0
a=ice-ufrag:XXXX
a=ice-pwd:XXXXXXXXXXXXXXXXXXXXXXXX
a=ice-options:trickle
a=fingerprint:sha-256 XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX:XX
a=setup:actpass
a=mid:1
a=recvonly
a=rtcp-mux
a=rtpmap:111 opus/48000/2
"""

            # Step 3: Send WHEP request
            async with session.post(
                webrtc_url, headers={"Content-Type": "application/sdp"}, data=sdp_offer
            ) as whep_response:
                if whep_response.status in [200, 201]:
                    answer_sdp = await whep_response.text()
                    elapsed = time.time() - start
                    self.stats["whep_success"] += 1
                    self.stats["total_time"] += elapsed
                    print(
                        f"[시청자 #{viewer_id}] ✅ WebRTC 연결 성공 ({elapsed * 1000:.0f}ms)"
                    )

                    # Extract session URL from Location header (for cleanup)
                    location = whep_response.headers.get("Location", "")

                    return {
                        "viewer_id": viewer_id,
                        "status": "connected",
                        "elapsed": elapsed,
                        "session_url": location,
                    }
                else:
                    self.stats["whep_failed"] += 1
                    error_text = await whep_response.text()
                    print(
                        f"[시청자 #{viewer_id}] ❌ WHEP 연결 실패: {whep_response.status}"
                    )
                    return None

        except Exception as e:
            print(f"[시청자 #{viewer_id}] ❌ 오류: {str(e)}")
            return None

    async def run_test(self):
        """Run the load test"""
        print("=" * 70)
        print(f"🔥 AIRClass Real WebRTC Load Test - {self.num_viewers} 시청자")
        print("=" * 70)
        print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"대상 서버: {self.base_url}")
        print(f"시청자 수: {self.num_viewers}")
        print("-" * 70)

        test_start = time.time()

        # Create all connections
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.create_whep_connection(session, i)
                for i in range(1, self.num_viewers + 1)
            ]

            # Execute with slight delay between requests to avoid overwhelming
            results = []
            for i in range(0, len(tasks), 5):  # 5 concurrent connections at a time
                batch = tasks[i : i + 5]
                batch_results = await asyncio.gather(*batch)
                results.extend(batch_results)
                await asyncio.sleep(0.5)  # Small delay between batches

        test_duration = time.time() - test_start

        # Print results
        print("\n" + "=" * 70)
        print("📊 테스트 결과")
        print("=" * 70)
        print(f"✅ 토큰 발급 성공: {self.stats['token_success']}")
        print(f"❌ 토큰 발급 실패: {self.stats['token_failed']}")
        print(f"✅ WebRTC 연결 성공: {self.stats['whep_success']}")
        print(f"❌ WebRTC 연결 실패: {self.stats['whep_failed']}")
        print(f"⏱️  총 소요 시간: {test_duration:.2f}초")

        if self.stats["whep_success"] > 0:
            avg_time = self.stats["total_time"] / self.stats["whep_success"]
            print(f"📈 평균 연결 시간: {avg_time * 1000:.0f}ms")
            success_rate = (self.stats["whep_success"] / self.num_viewers) * 100
            print(f"📊 성공률: {success_rate:.1f}%")

        print("\n" + "-" * 70)
        print("📡 현재 서버 상태 확인 중...")
        print("-" * 70)

        # Check server status
        await self.check_server_status()

        print("\n" + "=" * 70)
        print("⚠️  연결 유지 중... (30초 대기)")
        print("   Teacher 페이지에서 시청자 수를 확인하세요!")
        print("   http://localhost:5173/#/teacher")
        print("=" * 70)

        # Keep connections alive for 30 seconds
        await asyncio.sleep(30)

        print("\n" + "=" * 70)
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        return results

    async def check_server_status(self):
        """Check current viewer count on server"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/viewers") as response:
                    if response.status == 200:
                        data = await response.json()
                        print(
                            f"\n현재 서버 시청자 수: {data.get('total_viewers', 0)}명"
                        )
                        print(
                            f"스트림 상태: {'✅ 활성' if data.get('stream_ready') else '❌ 비활성'}"
                        )

                        node_stats = data.get("node_stats", {})
                        if node_stats:
                            print("\n노드별 부하:")
                            for name, stats in node_stats.items():
                                load = stats.get("load_percent", 0)
                                viewers = stats.get("viewers", 0)
                                capacity = stats.get("capacity", 150)
                                bar = "█" * int(load / 2)
                                print(
                                    f"  {name:10s}: {viewers:3d}/{capacity} ({load:5.1f}%) {bar}"
                                )
        except Exception as e:
            print(f"❌ 서버 상태 확인 실패: {e}")


async def main():
    import sys

    num_viewers = 30
    if len(sys.argv) > 1:
        try:
            num_viewers = int(sys.argv[1])
        except:
            print("사용법: python3 real_load_test.py [시청자수]")
            print("예: python3 real_load_test.py 50")
            sys.exit(1)

    if num_viewers < 1 or num_viewers > 100:
        print("❌ 시청자 수는 1~100 사이로 설정하세요.")
        sys.exit(1)

    test = RealWebRTCLoadTest(num_viewers=num_viewers)
    await test.run_test()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
