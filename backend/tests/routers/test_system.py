"""
Tests for System Status Router
================================
시스템 상태 및 헬스 체크 엔드포인트 테스트

Test Coverage:
- GET /: Root status endpoint
- GET /health: Health check with LiveKit API
- GET /api/status: WebSocket connection status

Note: MediaMTX → LiveKit 마이그레이션 완료
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from routers.system import router


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


@pytest.fixture
def mock_connection_manager():
    """Mock ConnectionManager"""
    mock_manager = MagicMock()
    mock_manager.teacher = None
    mock_manager.students = {}
    mock_manager.monitors = {}
    return mock_manager


# ==================== Root Status Tests ====================


def test_root_status(client):
    """루트 엔드포인트: 서비스 정보 반환"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "running"
    assert data["service"] == "AIRClass Backend Server"
    assert data["version"] == "2.0.0"
    assert data["mediamtx_running"] is True
    assert "rtmp_url" in data
    assert "webrtc_url" in data
    assert "frontend_url" in data
    assert "security" in data
    assert "JWT token required" in data["security"]


def test_root_status_urls(client):
    """루트 엔드포인트: URL 형식 검증"""
    response = client.get("/")
    data = response.json()

    assert data["rtmp_url"] == "rtmp://localhost:1935/live/stream"
    assert data["webrtc_url"] == "http://localhost:8889/live/stream/whep"
    assert data["frontend_url"] == "http://localhost:5173"


# ==================== Health Check Tests ====================


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_stream_active(mock_httpx_client, client):
    """Health check: 스트림 활성 상태"""
    # MediaMTX API 응답 모의 (활성 스트림)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": True,
                "readers": [{"id": "reader1"}, {"id": "reader2"}],
                "source": {"type": "rtmpConn"},
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["mode"] == "standalone"
    assert data["stream_active"] is True
    assert "timestamp" in data


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_stream_inactive(mock_httpx_client, client):
    """Health check: 스트림 비활성 상태"""
    # MediaMTX API 응답 모의 (비활성 스트림 - source 없음)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": False,
                "readers": [],
                "source": None,
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["mode"] == "standalone"
    assert data["stream_active"] is False


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_stream_ready_but_no_source(mock_httpx_client, client):
    """Health check: ready=True이지만 source 없음 (비활성 처리)"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": True,
                "readers": [{"id": "reader1"}],
                "source": None,  # source 없음
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # source가 없으므로 stream_active는 False
    assert data["stream_active"] is False


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_no_stream_path(mock_httpx_client, client):
    """Health check: live/stream 경로 없음"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "other/path",
                "ready": True,
                "readers": [],
                "source": {"type": "rtmpConn"},
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["stream_active"] is False


@patch.dict("os.environ", {"MODE": "main"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_main_mode(mock_httpx_client, client):
    """Health check: Main 모드"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "main"
    assert data["status"] == "healthy"


@patch.dict("os.environ", {"MODE": "sub"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_sub_mode(mock_httpx_client, client):
    """Health check: Sub 모드"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "sub"


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_mediamtx_api_failure(mock_httpx_client, client):
    """Health check: MediaMTX API 실패 (서버는 여전히 healthy)"""
    # API 호출 실패 모의
    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = Exception("Connection refused")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # MediaMTX API 실패해도 서버 자체는 healthy
    assert data["status"] == "healthy"
    assert data["stream_active"] is False  # 스트림 상태 확인 불가 -> False


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_mediamtx_api_timeout(mock_httpx_client, client):
    """Health check: MediaMTX API 타임아웃"""
    import httpx

    mock_client_instance = AsyncMock()
    mock_client_instance.get.side_effect = httpx.TimeoutException("Request timeout")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["stream_active"] is False


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_mediamtx_api_404(mock_httpx_client, client):
    """Health check: MediaMTX API 404 응답"""
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["stream_active"] is False


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
def test_health_check_timestamp_format(mock_httpx_client, client):
    """Health check: timestamp 형식 검증"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/health")
    data = response.json()

    # ISO 형식 타임스탬프 검증
    timestamp = data["timestamp"]
    datetime.fromisoformat(timestamp)  # ValueError 발생 안 하면 성공


# ==================== Connection Status Tests ====================


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.manager")
def test_status_no_connections(mock_manager, client):
    """연결 상태: 연결 없음"""
    mock_manager.teacher = None
    mock_manager.students = {}
    mock_manager.monitors = {}

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()

    assert data["teacher_connected"] is False
    assert data["students_count"] == 0
    assert data["students"] == []
    assert data["monitors_count"] == 0


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.manager")
def test_status_teacher_connected(mock_manager, client):
    """연결 상태: 교사 연결됨"""
    mock_teacher_ws = MagicMock()
    mock_manager.teacher = mock_teacher_ws
    mock_manager.students = {}
    mock_manager.monitors = {}

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()

    assert data["teacher_connected"] is True
    assert data["students_count"] == 0
    assert data["monitors_count"] == 0


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.manager")
def test_status_students_connected(mock_manager, client):
    """연결 상태: 학생들 연결됨"""
    mock_manager.teacher = None
    mock_manager.students = {
        "student1": MagicMock(),
        "student2": MagicMock(),
        "student3": MagicMock(),
    }
    mock_manager.monitors = {}

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()

    assert data["teacher_connected"] is False
    assert data["students_count"] == 3
    assert set(data["students"]) == {"student1", "student2", "student3"}
    assert data["monitors_count"] == 0


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.manager")
def test_status_monitors_connected(mock_manager, client):
    """연결 상태: 모니터 연결됨"""
    mock_manager.teacher = None
    mock_manager.students = {}
    mock_manager.monitors = {
        "monitor1": MagicMock(),
        "monitor2": MagicMock(),
    }

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()

    assert data["monitors_count"] == 2


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.manager")
def test_status_all_connected(mock_manager, client):
    """연결 상태: 모든 유형 연결됨"""
    mock_manager.teacher = MagicMock()
    mock_manager.students = {
        "student1": MagicMock(),
        "student2": MagicMock(),
    }
    mock_manager.monitors = {
        "monitor1": MagicMock(),
    }

    response = client.get("/api/status")

    assert response.status_code == 200
    data = response.json()

    assert data["teacher_connected"] is True
    assert data["students_count"] == 2
    assert len(data["students"]) == 2
    assert data["monitors_count"] == 1


# ==================== Integration Tests ====================


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.system.httpx.AsyncClient")
@patch("routers.system.manager")
def test_health_and_status_consistency(mock_manager, mock_httpx_client, client):
    """Health check와 status 엔드포인트 일관성 검증"""
    # Setup
    mock_manager.teacher = MagicMock()
    mock_manager.students = {"student1": MagicMock()}
    mock_manager.monitors = {}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": True,
                "readers": [{"id": "reader1"}],
                "source": {"type": "rtmpConn"},
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    # Health check
    health_response = client.get("/health")
    health_data = health_response.json()

    # Status check
    status_response = client.get("/api/status")
    status_data = status_response.json()

    # Both should be successful and show mode
    assert health_data["mode"] == "standalone"
    assert health_data["stream_active"] is True
    assert status_data["teacher_connected"] is True
    assert status_data["students_count"] == 1
