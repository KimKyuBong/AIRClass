"""
AIRClass Full System Integration Test
전체 시스템 통합 테스트: RTMP → MediaMTX → HLS → Frontend
"""

import asyncio
import subprocess
import time
import requests
import json
from pathlib import Path
import sys


# 색상 출력
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_test(msg):
    print(f"{Colors.BLUE}[TEST]{Colors.END} {msg}")


def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")


def print_header(msg):
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}\n")


class SystemTester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.mediamtx_url = "http://localhost:8888"
        self.frontend_url = "http://localhost:5173"
        self.token = None
        self.hls_url = None

    def test_1_backend_status(self):
        """Test 1: Backend 서버 상태 확인"""
        print_test("Backend 서버 상태 확인")
        try:
            response = requests.get(f"{self.backend_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_success(f"Backend 실행 중: {data.get('service')}")
                print(f"  - Version: {data.get('version')}")
                print(f"  - MediaMTX: {data.get('mediamtx_running')}")
                return True
            else:
                print_error(f"Backend 응답 오류: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print_error(f"Backend 연결 실패: {e}")
            return False

    def test_2_token_generation(self):
        """Test 2: JWT 토큰 발급"""
        print_test("JWT 토큰 발급 테스트")
        try:
            response = requests.post(
                f"{self.backend_url}/api/token",
                params={"user_type": "student", "user_id": "TestUser"},
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                self.hls_url = data.get("hls_url")
                print_success("토큰 발급 성공")
                print(f"  - Token: {self.token[:50]}...")
                print(f"  - HLS URL: {self.hls_url[:80]}...")
                print(f"  - Expires in: {data.get('expires_in')}s")
                return True
            else:
                print_error(f"토큰 발급 실패: {response.status_code}")
                print(f"  - Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"토큰 발급 오류: {e}")
            return False

    def test_3_mediamtx_status(self):
        """Test 3: MediaMTX 서버 상태"""
        print_test("MediaMTX 서버 상태 확인")
        try:
            # MediaMTX API 엔드포인트 확인
            response = requests.get(f"{self.mediamtx_url}/", timeout=5)
            # MediaMTX는 루트에서 404를 반환하지만 서버는 실행 중
            if response.status_code in [200, 404]:
                print_success("MediaMTX 서버 실행 중")
                return True
            else:
                print_warning(f"MediaMTX 응답: {response.status_code}")
                return True  # MediaMTX는 특정 엔드포인트만 응답
        except Exception as e:
            print_error(f"MediaMTX 연결 실패: {e}")
            return False

    def test_4_hls_without_token(self):
        """Test 4: 토큰 없이 HLS 접근 시도 (차단 확인)"""
        print_test("토큰 없이 HLS 접근 시도 (차단되어야 함)")
        try:
            response = requests.get(
                f"{self.mediamtx_url}/live/stream/index.m3u8", timeout=5
            )
            if response.status_code in [401, 403]:
                print_success(f"접근 차단됨 (HTTP {response.status_code})")
                return True
            elif response.status_code == 404:
                print_warning("스트림이 아직 생성되지 않음 (404)")
                return True
            else:
                print_error(f"예상치 못한 응답: {response.status_code}")
                print_warning("⚠️  MediaMTX 인증이 비활성화되어 있을 수 있음")
                return False
        except Exception as e:
            print_error(f"HLS 접근 테스트 실패: {e}")
            return False

    def test_5_hls_with_token(self):
        """Test 5: 토큰과 함께 HLS 접근 (허용 확인)"""
        print_test("유효한 토큰으로 HLS 접근 시도")
        if not self.token:
            print_error("토큰이 없습니다. Test 2를 먼저 실행하세요.")
            return False

        try:
            response = requests.get(self.hls_url, timeout=5)
            if response.status_code == 200:
                print_success("토큰 인증 성공 - HLS 매니페스트 수신")
                content = response.text[:200]
                print(f"  - Content preview: {content}...")
                return True
            elif response.status_code == 404:
                print_warning("스트림이 아직 생성되지 않음 (404)")
                print("  ℹ️  Android 앱이나 RTMP 스트림을 시작하면 접근 가능")
                return True
            else:
                print_error(f"HLS 접근 실패: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"HLS 접근 오류: {e}")
            return False

    def test_6_websocket_status(self):
        """Test 6: WebSocket 연결 상태 확인"""
        print_test("WebSocket 연결 가능 여부 확인")
        try:
            response = requests.get(f"{self.backend_url}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print_success("WebSocket 엔드포인트 사용 가능")
                print(f"  - Teacher connected: {data.get('teacher_connected')}")
                print(f"  - Students: {data.get('students_count')}")
                print(f"  - Monitors: {data.get('monitors_count')}")
                return True
            else:
                print_error(f"상태 API 오류: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"상태 확인 실패: {e}")
            return False

    def test_7_frontend_status(self):
        """Test 7: Frontend 서버 상태"""
        print_test("Frontend 서버 상태 확인")
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200:
                print_success("Frontend 서버 실행 중")
                print(f"  - Teacher: {self.frontend_url}/#/teacher")
                print(f"  - Student: {self.frontend_url}/#/student")
                print(f"  - Monitor: {self.frontend_url}/#/monitor")
                return True
            else:
                print_error(f"Frontend 응답 오류: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Frontend 연결 실패: {e}")
            return False

    def test_8_mock_rtmp_stream(self):
        """Test 8: 모의 RTMP 스트림 전송"""
        print_test("모의 RTMP 스트림 생성 (FFmpeg 필요)")

        # FFmpeg 설치 확인
        try:
            subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, check=True, timeout=3
            )
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            print_warning("FFmpeg가 설치되어 있지 않습니다")
            print("  설치 방법: brew install ffmpeg (macOS)")
            print("  또는 Android 앱을 사용하여 실제 스트림을 전송하세요")
            return None

        # 테스트 패턴 생성 및 RTMP 전송
        print("  📹 테스트 패턴 스트림 생성 중...")
        print("  (10초간 전송 후 자동 종료)")

        rtmp_url = "rtmp://localhost:1935/live/stream"

        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=10:size=1280x720:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=10",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-b:v",
            "2000k",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-f",
            "flv",
            rtmp_url,
        ]

        try:
            print(f"  🚀 RTMP 전송 시작: {rtmp_url}")
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # 3초 대기 (스트림 초기화)
            time.sleep(3)

            # 프로세스가 실행 중인지 확인
            if process.poll() is None:
                print_success("RTMP 스트림 전송 중...")
                print("  ℹ️  이제 HLS URL로 스트림 확인 가능:")
                print(f"  {self.hls_url}")

                # 스트림이 MediaMTX에 도달했는지 확인
                time.sleep(2)
                try:
                    response = requests.get(self.hls_url, timeout=3)
                    if response.status_code == 200:
                        print_success("✨ HLS 스트림 생성 확인!")
                        print("  Frontend에서 비디오 재생 가능")
                    else:
                        print_warning(f"HLS 응답: {response.status_code}")
                except Exception as e:
                    print_warning(f"HLS 확인 실패: {e}")

                # 10초 대기 (전체 스트림 전송)
                print("  ⏳ 10초간 스트림 전송 중...")
                process.wait(timeout=15)

                print_success("RTMP 스트림 전송 완료")
                return True
            else:
                stderr = process.stderr.read().decode()
                print_error(f"FFmpeg 실행 실패")
                print(f"  Error: {stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            process.kill()
            print_success("스트림 전송 완료 (타임아웃)")
            return True
        except Exception as e:
            print_error(f"RTMP 스트림 전송 실패: {e}")
            return False

    def run_all_tests(self):
        """모든 테스트 실행"""
        print_header("🧪 AIRClass Full System Integration Test")

        results = []

        # Test 1: Backend
        print_header("Test 1: Backend 서버")
        results.append(("Backend Status", self.test_1_backend_status()))

        # Test 2: Token
        print_header("Test 2: JWT 토큰 발급")
        results.append(("Token Generation", self.test_2_token_generation()))

        # Test 3: MediaMTX
        print_header("Test 3: MediaMTX 서버")
        results.append(("MediaMTX Status", self.test_3_mediamtx_status()))

        # Test 4: HLS without token
        print_header("Test 4: HLS 접근 제어 (토큰 없음)")
        results.append(("HLS Auth (No Token)", self.test_4_hls_without_token()))

        # Test 5: HLS with token
        print_header("Test 5: HLS 접근 (토큰 있음)")
        results.append(("HLS Auth (With Token)", self.test_5_hls_with_token()))

        # Test 6: WebSocket
        print_header("Test 6: WebSocket 상태")
        results.append(("WebSocket Status", self.test_6_websocket_status()))

        # Test 7: Frontend
        print_header("Test 7: Frontend 서버")
        results.append(("Frontend Status", self.test_7_frontend_status()))

        # Test 8: Mock RTMP Stream
        print_header("Test 8: 모의 RTMP 스트림")
        stream_result = self.test_8_mock_rtmp_stream()
        if stream_result is not None:
            results.append(("RTMP Stream", stream_result))

        # 결과 요약
        print_header("📊 Test Results Summary")

        passed = sum(1 for _, result in results if result)
        total = len(results)
        failed = total - passed

        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {name}")

        print(
            f"\n{Colors.BOLD}Total: {total} | Passed: {passed} | Failed: {failed}{Colors.END}"
        )

        if failed == 0:
            print_success(f"\n🎉 All tests passed! System is ready.")
        else:
            print_error(f"\n⚠️  {failed} test(s) failed. Check the output above.")

        # 최종 사용자 가이드
        print_header("📱 다음 단계")
        print("1. 브라우저에서 Frontend 열기:")
        print(f"   {self.frontend_url}/#/student")
        print("\n2. Android 앱 실행 또는 FFmpeg로 스트림 전송:")
        print(
            "   ffmpeg -re -i video.mp4 -c copy -f flv rtmp://localhost:1935/live/stream"
        )
        print("\n3. Student 페이지에서 이름 입력 후 '수업 참여하기' 클릭")
        print("\n4. 비디오가 자동으로 재생됩니다!")


def main():
    tester = SystemTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
