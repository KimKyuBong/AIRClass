"""
E2E Browser Tests for LiveKit Streaming
========================================
Playwright를 사용한 실제 브라우저 WebRTC 테스트

Test Coverage:
- Teacher: 화면 공유 송출
- Student: 영상 수신
- 실시간 연결 상태 확인
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, Page, expect


@pytest.fixture
async def browser_context():
    """Playwright 브라우저 컨텍스트 생성"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",  # 권한 자동 승인
                "--use-fake-device-for-media-stream",  # 가짜 미디어 디바이스
                "--allow-insecure-localhost",  # localhost HTTPS 허용
            ],
        )
        context = await browser.new_context(
            permissions=["camera", "microphone"], viewport={"width": 1280, "height": 720}
        )
        yield context
        await context.close()
        await browser.close()


@pytest.mark.asyncio
async def test_teacher_screen_share(browser_context):
    """Teacher: 화면 공유 송출 테스트"""
    page = await browser_context.new_page()

    try:
        # 1. Teacher 페이지 접속
        await page.goto("http://localhost:5173/#/teacher", wait_until="networkidle")
        await asyncio.sleep(2)

        # 2. 방 이름 입력
        room_input = page.locator('input[placeholder*="방"]')
        await room_input.fill("e2e-test-room")

        # 3. "🖥️ PC 화면" 버튼 클릭
        screen_button = page.locator('button:has-text("PC 화면")')
        await screen_button.click()

        # 4. 연결 대기 (최대 10초)
        await asyncio.sleep(5)

        # 5. 연결 상태 확인
        # LiveKit Room 객체가 생성되었는지 확인
        is_connected = await page.evaluate("""
            () => {
                return window.room && window.room.state === 'connected';
            }
        """)

        assert is_connected, "Teacher가 LiveKit Room에 연결되지 않았습니다"

        # 6. 로컬 트랙 송출 확인
        has_local_track = await page.evaluate("""
            () => {
                if (!window.room) return false;
                const tracks = Array.from(window.room.localParticipant.trackPublications.values());
                return tracks.some(pub => pub.kind === 'video' && pub.track);
            }
        """)

        assert has_local_track, "비디오 트랙이 송출되지 않았습니다"

        print("✅ Teacher 화면 공유 성공")

    finally:
        await page.close()


@pytest.mark.asyncio
async def test_student_video_subscribe(browser_context):
    """Student: 영상 수신 테스트 (Teacher가 이미 송출 중이어야 함)"""
    # Teacher 페이지 먼저 시작
    teacher_page = await browser_context.new_page()
    await teacher_page.goto("http://localhost:5173/#/teacher", wait_until="networkidle")
    await asyncio.sleep(2)

    room_input = teacher_page.locator('input[placeholder*="방"]')
    await room_input.fill("e2e-test-room-2")

    screen_button = teacher_page.locator('button:has-text("PC 화면")')
    await screen_button.click()
    await asyncio.sleep(3)

    # Student 페이지 시작
    student_page = await browser_context.new_page()

    try:
        # 1. Student 페이지 접속
        await student_page.goto("http://localhost:5173/#/student", wait_until="networkidle")
        await asyncio.sleep(2)

        # 2. 같은 방 이름 입력
        room_input_student = student_page.locator('input[placeholder*="방"]')
        await room_input_student.fill("e2e-test-room-2")

        # 3. "수업 참여" 버튼 클릭
        join_button = student_page.locator('button:has-text("참여")')
        await join_button.click()

        # 4. 연결 대기
        await asyncio.sleep(5)

        # 5. 원격 트랙 수신 확인
        has_remote_track = await student_page.evaluate("""
            () => {
                if (!window.room) return false;
                const participants = Array.from(window.room.remoteParticipants.values());
                if (participants.length === 0) return false;
                
                const remoteTracks = participants[0].trackPublications;
                return Array.from(remoteTracks.values()).some(pub => 
                    pub.kind === 'video' && pub.isSubscribed
                );
            }
        """)

        assert has_remote_track, "Student가 Teacher 영상을 수신하지 못했습니다"

        # 6. 비디오 엘리먼트 확인
        video_element = student_page.locator("video")
        await expect(video_element).to_be_visible()

        print("✅ Student 영상 수신 성공")

    finally:
        await student_page.close()
        await teacher_page.close()


@pytest.mark.asyncio
async def test_multiple_students(browser_context):
    """다중 Student 동시 수신 테스트"""
    # Teacher 시작
    teacher_page = await browser_context.new_page()
    await teacher_page.goto("http://localhost:5173/#/teacher", wait_until="networkidle")
    await asyncio.sleep(2)

    room_input = teacher_page.locator('input[placeholder*="방"]')
    await room_input.fill("e2e-multi-test")

    screen_button = teacher_page.locator('button:has-text("PC 화면")')
    await screen_button.click()
    await asyncio.sleep(3)

    # 3명의 Student 동시 접속
    student_pages = []

    try:
        for i in range(3):
            student_page = await browser_context.new_page()
            await student_page.goto("http://localhost:5173/#/student", wait_until="networkidle")
            await asyncio.sleep(1)

            room_input_student = student_page.locator('input[placeholder*="방"]')
            await room_input_student.fill("e2e-multi-test")

            join_button = student_page.locator('button:has-text("참여")')
            await join_button.click()

            student_pages.append(student_page)

        # 모든 Student 연결 대기
        await asyncio.sleep(5)

        # 각 Student가 영상을 수신하는지 확인
        for idx, student_page in enumerate(student_pages):
            has_video = await student_page.evaluate("""
                () => {
                    const video = document.querySelector('video');
                    return video && video.srcObject && video.srcObject.active;
                }
            """)
            assert has_video, f"Student {idx + 1}이 영상을 수신하지 못했습니다"

        print(f"✅ {len(student_pages)}명의 Student 동시 수신 성공")

    finally:
        for page in student_pages:
            await page.close()
        await teacher_page.close()


@pytest.mark.asyncio
async def test_reconnection(browser_context):
    """네트워크 끊김 후 재연결 테스트"""
    page = await browser_context.new_page()

    try:
        # 1. 초기 연결
        await page.goto("http://localhost:5173/#/teacher", wait_until="networkidle")
        await asyncio.sleep(2)

        room_input = page.locator('input[placeholder*="방"]')
        await room_input.fill("reconnect-test")

        screen_button = page.locator('button:has-text("PC 화면")')
        await screen_button.click()
        await asyncio.sleep(3)

        # 2. 네트워크 오프라인 시뮬레이션
        await page.context.set_offline(True)
        await asyncio.sleep(2)

        # 3. 네트워크 복구
        await page.context.set_offline(False)
        await asyncio.sleep(5)

        # 4. 재연결 확인
        is_reconnected = await page.evaluate("""
            () => {
                return window.room && window.room.state === 'connected';
            }
        """)

        assert is_reconnected, "재연결에 실패했습니다"

        print("✅ 재연결 성공")

    finally:
        await page.close()


if __name__ == "__main__":
    # 단독 실행 시
    pytest.main([__file__, "-v", "-s"])
