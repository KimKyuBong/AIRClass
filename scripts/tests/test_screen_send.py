#!/usr/bin/env python3
"""
Android 화면 전송 시뮬레이션 테스트
"""

import requests
import time
from PIL import Image
import io


def create_test_image(text: str) -> bytes:
    """테스트용 이미지 생성"""
    from PIL import ImageDraw, ImageFont

    # 1280x720 이미지 생성
    img = Image.new("RGB", (1280, 720), color=(73, 109, 137))
    d = ImageDraw.Draw(img)

    # 텍스트 추가
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 80)
    except:
        font = ImageFont.load_default()

    # 텍스트 중앙 정렬
    bbox = d.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (1280 - text_width) // 2
    y = (720 - text_height) // 2

    d.text((x, y), text, fill=(255, 255, 255), font=font)

    # JPEG로 변환
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def send_screen_data(image_data: bytes):
    """화면 데이터를 서버로 전송"""
    url = "http://localhost:8000/api/screen"

    try:
        response = requests.post(
            url, data=image_data, headers={"Content-Type": "application/octet-stream"}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Sent {result['data_size']} bytes")
            print(
                f"   📤 Broadcasted to: {result['broadcasted_to']['students']} students, {result['broadcasted_to']['monitors']} monitors"
            )
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def main():
    print("=" * 60)
    print("📱 Android Screen Capture Simulation")
    print("=" * 60)
    print("Sending test images to backend...")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    frame_count = 0

    try:
        while True:
            frame_count += 1

            # 프레임 번호가 있는 이미지 생성
            text = f"Frame #{frame_count}"
            image_data = create_test_image(text)

            print(f"\n📸 Frame {frame_count}:")
            success = send_screen_data(image_data)

            if not success:
                print("⚠️  Failed to send frame, retrying...")

            # 30 FPS (33ms 간격)
            time.sleep(0.033)

            # 매 30프레임마다 상태 확인
            if frame_count % 30 == 0:
                try:
                    status = requests.get("http://localhost:8000/api/status").json()
                    print(
                        f"\n📊 Status: {status['students_count']} students, {status['monitors_count']} monitors connected"
                    )
                except:
                    pass

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print(f"✅ Stopped after {frame_count} frames")
        print("=" * 60)


if __name__ == "__main__":
    main()
