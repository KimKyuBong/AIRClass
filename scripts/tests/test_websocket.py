#!/usr/bin/env python3
"""
WebSocket 연결 테스트 스크립트
"""

import asyncio
import websockets
import json


async def test_student_connection():
    """학생 WebSocket 연결 테스트"""
    uri = "ws://localhost:8000/ws/student?name=TestStudent"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Student WebSocket connected!")

            # 채팅 메시지 전송
            await websocket.send(
                json.dumps({"type": "chat", "message": "Hello from test student!"})
            )
            print("📤 Sent chat message")

            # 응답 대기 (타임아웃 설정)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"📥 Received: {response}")
            except asyncio.TimeoutError:
                print("⏱️  No response received (this is OK)")

    except Exception as e:
        print(f"❌ Error: {e}")


async def test_teacher_connection():
    """교사 WebSocket 연결 테스트"""
    uri = "ws://localhost:8000/ws/teacher"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Teacher WebSocket connected!")

            # 학생 목록 수신 대기
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(response)
                print(f"📥 Received: {data}")

                if data.get("type") == "student_list":
                    print(f"👨‍🎓 Students: {data.get('students')}")
            except asyncio.TimeoutError:
                print("⏱️  No student list received")

    except Exception as e:
        print(f"❌ Error: {e}")


async def main():
    print("=" * 60)
    print("🧪 Testing WebSocket Connections")
    print("=" * 60)

    print("\n1️⃣  Testing Student Connection...")
    await test_student_connection()

    print("\n2️⃣  Testing Teacher Connection...")
    await test_teacher_connection()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
