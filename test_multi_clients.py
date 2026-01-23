#!/usr/bin/env python3
"""
다수 클라이언트 WebRTC 동시 접속 테스트
"""

import asyncio
import aiohttp
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
WEBRTC_TEST_COUNT = 10  # 동시 접속할 클라이언트 수


async def test_single_client(session, client_id, user_type="student"):
    """단일 클라이언트 토큰 요청 테스트"""
    try:
        start_time = time.time()

        # 1. 토큰 요청
        async with session.post(
            f"{BASE_URL}/api/token",
            params={"user_type": user_type, "user_id": f"test_user_{client_id}"},
        ) as response:
            if response.status != 200:
                print(
                    f"❌ Client {client_id}: Token request failed - {response.status}"
                )
                return {
                    "client_id": client_id,
                    "success": False,
                    "error": f"HTTP {response.status}",
                }

            data = await response.json()
            webrtc_url = data.get("webrtc_url")
            token_time = time.time() - start_time

            if not webrtc_url:
                print(f"❌ Client {client_id}: No webrtc_url in response")
                return {
                    "client_id": client_id,
                    "success": False,
                    "error": "No webrtc_url",
                }

            # 2. WebRTC WHEP 엔드포인트 OPTIONS 요청 (연결 가능 여부 확인)
            whep_start = time.time()
            async with session.options(webrtc_url) as whep_response:
                whep_time = time.time() - whep_start

                total_time = time.time() - start_time

                result = {
                    "client_id": client_id,
                    "success": whep_response.status
                    in [200, 204, 401],  # 401 is expected (needs auth)
                    "token_time_ms": round(token_time * 1000, 2),
                    "whep_time_ms": round(whep_time * 1000, 2),
                    "total_time_ms": round(total_time * 1000, 2),
                    "webrtc_url": webrtc_url,
                    "status": whep_response.status,
                }

                if result["success"]:
                    print(
                        f"✅ Client {client_id}: OK (token: {result['token_time_ms']}ms, whep: {result['whep_time_ms']}ms)"
                    )
                else:
                    print(
                        f"❌ Client {client_id}: FAILED (HTTP {whep_response.status})"
                    )

                return result

    except Exception as e:
        print(f"❌ Client {client_id}: Exception - {str(e)}")
        return {"client_id": client_id, "success": False, "error": str(e)}


async def test_concurrent_clients(num_clients=10):
    """다수 클라이언트 동시 접속 테스트"""
    print("=" * 80)
    print(f"🧪 다수 클라이언트 동시 접속 테스트 시작")
    print(f"📊 테스트 클라이언트 수: {num_clients}")
    print(f"🕐 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    start_time = time.time()

    # 동시에 여러 클라이언트 생성
    async with aiohttp.ClientSession() as session:
        # Student 클라이언트 생성
        student_tasks = [
            test_single_client(session, i, "student") for i in range(num_clients)
        ]

        # Teacher 클라이언트 1명 추가
        teacher_task = test_single_client(session, 999, "teacher")

        # Monitor 클라이언트 1명 추가
        monitor_task = test_single_client(session, 998, "monitor")

        all_tasks = student_tasks + [teacher_task, monitor_task]

        # 모든 요청 동시 실행
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

    total_time = time.time() - start_time

    # 결과 분석
    print()
    print("=" * 80)
    print("📊 테스트 결과 분석")
    print("=" * 80)

    successful = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
    exceptions = [r for r in results if not isinstance(r, dict)]

    print(f"✅ 성공: {len(successful)}/{len(results)}")
    print(f"❌ 실패: {len(failed)}")
    print(f"⚠️  예외: {len(exceptions)}")
    print(f"⏱️  총 소요 시간: {total_time:.2f}초")
    print()

    if successful:
        token_times = [r["token_time_ms"] for r in successful]
        whep_times = [r["whep_time_ms"] for r in successful]
        total_times = [r["total_time_ms"] for r in successful]

        print("⚡ 응답 시간 통계:")
        print(
            f"   토큰 발급: 평균 {sum(token_times) / len(token_times):.2f}ms, 최대 {max(token_times):.2f}ms"
        )
        print(
            f"   WHEP 응답: 평균 {sum(whep_times) / len(whep_times):.2f}ms, 최대 {max(whep_times):.2f}ms"
        )
        print(
            f"   전체 시간: 평균 {sum(total_times) / len(total_times):.2f}ms, 최대 {max(total_times):.2f}ms"
        )

    if failed:
        print()
        print("❌ 실패한 요청:")
        for r in failed:
            print(f"   Client {r['client_id']}: {r.get('error', 'Unknown error')}")

    print()
    print("=" * 80)

    return {
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "exceptions": len(exceptions),
        "total_time": total_time,
    }


async def check_mediamtx_readers():
    """MediaMTX reader 수 확인"""
    print()
    print("📡 MediaMTX 스트림 상태 확인 중...")

    try:
        async with aiohttp.ClientSession() as session:
            # Main node의 MediaMTX API 호출 (Docker 내부에서)
            async with session.get("http://localhost:9997/v3/paths/list") as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get("items", [])

                    for item in items:
                        if item.get("name") == "live/stream":
                            readers_count = len(item.get("readers", []))
                            ready = item.get("ready", False)
                            tracks = item.get("tracks", [])
                            bytes_received = item.get("bytesReceived", 0)
                            bytes_sent = item.get("bytesSent", 0)

                            print(f"   Stream: live/stream")
                            print(f"   Ready: {ready}")
                            print(f"   Tracks: {', '.join(tracks)}")
                            print(f"   Active Readers: {readers_count}")
                            print(f"   Bytes Received: {bytes_received:,}")
                            print(f"   Bytes Sent: {bytes_sent:,}")
                            return readers_count

        print("   ⚠️  Stream not found")
        return 0
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 0


async def main():
    # 테스트 전 상태 확인
    await check_mediamtx_readers()

    print()
    input("Press Enter to start the test...")
    print()

    # 동시 접속 테스트
    result = await test_concurrent_clients(WEBRTC_TEST_COUNT)

    # 테스트 후 대기 (실제 WebRTC 연결 확립을 위해)
    print()
    print("⏳ WebRTC 연결 확립 대기 중 (10초)...")
    await asyncio.sleep(10)

    # 테스트 후 상태 확인
    readers = await check_mediamtx_readers()

    print()
    print("=" * 80)
    print("🎯 최종 결과")
    print("=" * 80)
    print(f"총 테스트 클라이언트: {result['total']}")
    print(f"성공한 토큰 발급: {result['successful']}")
    print(f"실패: {result['failed']}")
    print(f"MediaMTX Active Readers: {readers}")
    print()

    if result["successful"] > 0 and result["failed"] == 0:
        print("✅ 모든 클라이언트가 정상적으로 토큰을 받았습니다!")
    else:
        print("⚠️  일부 클라이언트에서 문제가 발생했습니다.")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
