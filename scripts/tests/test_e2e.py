#!/usr/bin/env python3
"""
종합 End-to-End 테스트
- 학생 연결
- 교사 연결
- Android 화면 전송
- 채팅 메시지 교환
"""

import asyncio
import websockets
import requests
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io


def create_test_image(text: str) -> bytes:
    """테스트 이미지 생성"""
    img = Image.new("RGB", (800, 600), color=(50, 100, 150))
    d = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 60)
    except:
        font = ImageFont.load_default()

    bbox = d.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (800 - text_width) // 2
    y = (600 - text_height) // 2

    d.text((x, y), text, fill=(255, 255, 255), font=font)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


async def student_client(name: str):
    """학생 클라이언트 시뮬레이션"""
    uri = f"ws://localhost:8000/ws/student?name={name}"

    try:
        async with websockets.connect(uri) as ws:
            print(f"  ✅ Student '{name}' connected")

            # 화면 데이터 수신 대기
            screen_received = False

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(message)

                    if data.get("type") == "screen":
                        if not screen_received:
                            print(
                                f"  📺 Student '{name}' received screen data ({len(data.get('data', ''))} bytes base64)"
                            )
                            screen_received = True

                    elif data.get("type") == "chat":
                        print(
                            f"  💬 Student '{name}' received chat from {data.get('from')}: {data.get('message')}"
                        )

                except asyncio.TimeoutError:
                    # 연결 유지를 위한 ping
                    await ws.send(json.dumps({"type": "ping"}))

    except Exception as e:
        print(f"  ❌ Student '{name}' error: {e}")


async def teacher_client():
    """교사 클라이언트 시뮬레이션"""
    uri = "ws://localhost:8000/ws/teacher"

    try:
        async with websockets.connect(uri) as ws:
            print("  ✅ Teacher connected")

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(message)

                    if data.get("type") == "student_list":
                        students = data.get("students", [])
                        print(f"  👥 Teacher received student list: {students}")

                        # 학생이 있으면 채팅 메시지 전송
                        if students and len(students) > 0:
                            await asyncio.sleep(1)
                            await ws.send(
                                json.dumps(
                                    {
                                        "type": "chat",
                                        "message": "환영합니다! 수업을 시작합니다.",
                                    }
                                )
                            )
                            print("  📤 Teacher sent welcome message")

                    elif data.get("type") == "chat":
                        print(
                            f"  💬 Teacher received chat from {data.get('from')}: {data.get('message')}"
                        )

                except asyncio.TimeoutError:
                    continue

    except Exception as e:
        print(f"  ❌ Teacher error: {e}")


async def send_screen_frames():
    """화면 프레임 전송"""
    await asyncio.sleep(2)  # 연결 대기

    print("\n📸 Starting screen broadcast...")

    for i in range(5):
        image_data = create_test_image(f"Frame {i + 1}")

        try:
            response = requests.post(
                "http://localhost:8000/api/screen",
                data=image_data,
                headers={"Content-Type": "application/octet-stream"},
            )

            if response.status_code == 200:
                result = response.json()
                print(
                    f"  ✅ Frame {i + 1} sent ({result['data_size']} bytes) -> {result['broadcasted_to']['students']} students, {result['broadcasted_to']['monitors']} monitors"
                )
            else:
                print(f"  ❌ Frame {i + 1} failed: {response.status_code}")

        except Exception as e:
            print(f"  ❌ Frame {i + 1} error: {e}")

        await asyncio.sleep(1)

    print("  ✅ Screen broadcast completed")


async def main():
    print("=" * 70)
    print("🧪 End-to-End Integration Test")
    print("=" * 70)

    # 초기 상태 확인
    print("\n1️⃣  Checking initial status...")
    try:
        status = requests.get("http://localhost:8000/api/status").json()
        print(
            f"  📊 Initial: {status['students_count']} students, {status['monitors_count']} monitors"
        )
    except Exception as e:
        print(f"  ❌ Cannot connect to backend: {e}")
        return

    print("\n2️⃣  Starting clients...")

    # 모든 클라이언트를 동시에 실행
    tasks = [
        asyncio.create_task(student_client("Alice")),
        asyncio.create_task(student_client("Bob")),
        asyncio.create_task(teacher_client()),
        asyncio.create_task(send_screen_frames()),
    ]

    # 10초간 실행
    print("\n3️⃣  Running test for 10 seconds...\n")

    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True), timeout=10.0
        )
    except asyncio.TimeoutError:
        print("\n  ⏱️  Test timeout (expected)")
        for task in tasks:
            task.cancel()

    # 최종 상태 확인
    print("\n4️⃣  Checking final status...")
    try:
        status = requests.get("http://localhost:8000/api/status").json()
        print(
            f"  📊 Final: {status['students_count']} students, {status['monitors_count']} monitors"
        )
        print(f"  📺 Screen data: {'Yes' if status['has_screen_data'] else 'No'}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    print("\n" + "=" * 70)
    print("✅ Test completed!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Open http://localhost:5173/#/teacher in your browser")
    print("  2. Open http://localhost:5173/#/student in another tab")
    print("  3. Run 'python test_screen_send.py' to simulate Android")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
