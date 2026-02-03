"""
Tests for MediaMTX Authentication Router
=========================================
MediaMTX HTTP 인증 콜백 엔드포인트 테스트

Test Coverage:
- POST /api/auth/mediamtx: MediaMTX 인증 콜백
- RTMP publish (항상 허용)
- WebRTC publish (교사만 허용, JWT 검증)
- RTMP read (localhost만 허용)
- RTSP read (FFmpeg 프록시 허용)
- WebRTC read (JWT 검증 + path 검증)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

from routers.mediamtx_auth import router
from utils.jwt_auth import generate_stream_token


@pytest.fixture
def app():
    """FastAPI 앱 생성"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """TestClient 생성"""
    return TestClient(app)


# ==================== RTMP Publish Tests ====================


def test_rtmp_publish_always_allowed(client):
    """RTMP publish: 항상 허용 (Android 앱)"""
    request_data = {
        "action": "publish",
        "protocol": "rtmp",
        "path": "live/stream",
        "ip": "10.100.0.50",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rtmp_publish_from_any_ip(client):
    """RTMP publish: 모든 IP에서 허용"""
    request_data = {
        "action": "publish",
        "protocol": "rtmp",
        "path": "live/stream",
        "ip": "192.168.1.100",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ==================== WebRTC Publish Tests (Teacher Screen Share) ====================


def test_webrtc_publish_with_teacher_token(client):
    """WebRTC publish: 교사 토큰으로 허용"""
    token = generate_stream_token("teacher", "teacher1", "publish")

    request_data = {
        "action": "publish",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"jwt={token}",
        "ip": "10.100.0.10",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webrtc_publish_without_token(client):
    """WebRTC publish: 토큰 없으면 거부"""
    request_data = {
        "action": "publish",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": "",
        "ip": "10.100.0.10",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 401
    assert "Token required" in response.json()["detail"]


def test_webrtc_publish_with_invalid_token(client):
    """WebRTC publish: 잘못된 토큰 거부"""
    request_data = {
        "action": "publish",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": "jwt=invalid_token_12345",
        "ip": "10.100.0.10",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_webrtc_publish_with_student_token(client):
    """WebRTC publish: 학생 토큰으로 거부 (교사만 publish 가능)"""
    token = generate_stream_token("student", "student1", "read")

    request_data = {
        "action": "publish",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"jwt={token}",
        "ip": "10.100.0.10",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 403
    assert "Only teachers can publish" in response.json()["detail"]


def test_webrtc_publish_with_monitor_token(client):
    """WebRTC publish: 모니터 토큰으로 거부"""
    token = generate_stream_token("monitor", "monitor1", "read")

    request_data = {
        "action": "publish",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"jwt={token}",
        "ip": "10.100.0.10",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 403
    assert "Only teachers can publish" in response.json()["detail"]


def test_webrtc_publish_query_with_multiple_params(client):
    """WebRTC publish: 쿼리 파라미터가 여러 개일 때 jwt 추출"""
    token = generate_stream_token("teacher", "teacher1", "publish")

    request_data = {
        "action": "publish",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"other_param=value&jwt={token}&another=param",
        "ip": "10.100.0.10",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ==================== RTMP Read Tests ====================


def test_rtmp_read_from_localhost_ipv4(client):
    """RTMP read: localhost (IPv4) 허용"""
    request_data = {
        "action": "read",
        "protocol": "rtmp",
        "path": "live/stream",
        "ip": "127.0.0.1",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rtmp_read_from_localhost_ipv6(client):
    """RTMP read: localhost (IPv6) 허용"""
    request_data = {
        "action": "read",
        "protocol": "rtmp",
        "path": "live/stream",
        "ip": "::1",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rtmp_read_from_localhost_hostname(client):
    """RTMP read: localhost (호스트명) 허용"""
    request_data = {
        "action": "read",
        "protocol": "rtmp",
        "path": "live/stream",
        "ip": "localhost",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rtmp_read_from_external_ip(client):
    """RTMP read: 외부 IP에서 거부"""
    request_data = {
        "action": "read",
        "protocol": "rtmp",
        "path": "live/stream",
        "ip": "192.168.1.100",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 403
    assert "RTMP read not allowed" in response.json()["detail"]


# ==================== RTSP Read Tests (FFmpeg Proxy) ====================


def test_rtsp_read_always_allowed(client):
    """RTSP read: 항상 허용 (FFmpeg 프록시)"""
    request_data = {
        "action": "read",
        "protocol": "rtsp",
        "path": "live/stream",
        "ip": "127.0.0.1",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rtsp_read_from_any_ip(client):
    """RTSP read: 모든 IP 허용 (로그상 localhost만 접근하지만 검증은 하지 않음)"""
    request_data = {
        "action": "read",
        "protocol": "rtsp",
        "path": "live/stream",
        "ip": "10.100.0.50",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ==================== WebRTC Read Tests ====================


def test_webrtc_read_with_valid_token(client):
    """WebRTC read: 유효한 토큰으로 허용"""
    token = generate_stream_token("student", "student1", "read")

    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"jwt={token}",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webrtc_read_teacher_token(client):
    """WebRTC read: 교사 토큰도 허용"""
    token = generate_stream_token("teacher", "teacher1", "read")

    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"jwt={token}",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webrtc_read_monitor_token(client):
    """WebRTC read: 모니터 토큰 허용"""
    token = generate_stream_token("monitor", "monitor1", "read")

    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"jwt={token}",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webrtc_read_without_token(client):
    """WebRTC read: 토큰 없으면 거부"""
    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": "",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 401
    assert "Token required" in response.json()["detail"]


def test_webrtc_read_with_invalid_token(client):
    """WebRTC read: 잘못된 토큰 거부"""
    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": "jwt=invalid_token_xyz",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


def test_webrtc_read_path_mismatch(client):
    """WebRTC read: Path 불일치 거부"""
    # live/stream용 토큰 생성
    token = generate_stream_token("student", "student1", "read")

    # 다른 path로 접근 시도
    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "other/path",  # 토큰의 path와 다름
        "query": f"jwt={token}",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 403
    assert "Path mismatch" in response.json()["detail"]


def test_webrtc_read_query_with_multiple_params(client):
    """WebRTC read: 쿼리 파라미터 여러 개일 때 jwt 추출"""
    token = generate_stream_token("student", "student1", "read")

    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"param1=value1&jwt={token}&param2=value2",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ==================== Unknown Protocol/Action Tests ====================


def test_unknown_protocol_denied(client):
    """알 수 없는 프로토콜 거부"""
    request_data = {
        "action": "read",
        "protocol": "hls",  # 지원하지 않는 프로토콜
        "path": "live/stream",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


def test_unknown_action_denied(client):
    """알 수 없는 액션 거부"""
    request_data = {
        "action": "modify",  # 지원하지 않는 액션
        "protocol": "webrtc",
        "path": "live/stream",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]


# ==================== Edge Case Tests ====================


def test_empty_query_string(client):
    """빈 쿼리 스트링 처리"""
    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": "",
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    assert response.status_code == 401  # 토큰 필수


def test_missing_ip_field(client):
    """IP 필드 누락 시 기본값 처리"""
    request_data = {
        "action": "publish",
        "protocol": "rtmp",
        "path": "live/stream",
        # ip 필드 누락
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    # RTMP publish는 항상 허용
    assert response.status_code == 200


def test_jwt_token_extraction_duplicate_jwt_params(client):
    """jwt 파라미터 중복 시 첫 번째 값만 사용"""
    token1 = generate_stream_token("student", "student1", "read")
    token2 = "fake_token_xyz"

    request_data = {
        "action": "read",
        "protocol": "webrtc",
        "path": "live/stream",
        "query": f"jwt={token1}&jwt={token2}",  # 중복
        "ip": "10.100.0.20",
    }

    response = client.post("/api/auth/mediamtx", json=request_data)

    # 첫 번째 유효한 토큰으로 인증 성공
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
