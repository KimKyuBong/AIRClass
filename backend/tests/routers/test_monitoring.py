"""
Tests for Monitoring Router
============================
시스템 모니터링 및 메트릭 엔드포인트 테스트

Test Coverage:
- GET /metrics: Prometheus 메트릭 노출
- GET /api/viewers: LiveKit 참가자 수 조회
- 클러스터 모드별 메트릭 수집

Note: MediaMTX → LiveKit 마이그레이션 완료
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from routers.monitoring import router


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


# ==================== Prometheus Metrics Tests ====================


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.manager")
@patch("routers.monitoring.generate_latest")
def test_metrics_endpoint_basic(mock_generate_latest, mock_manager, client):
    """Prometheus 메트릭 엔드포인트 기본 동작"""
    mock_manager.teacher = MagicMock()
    mock_manager.students = {"student1": MagicMock(), "student2": MagicMock()}
    mock_manager.monitors = {}

    mock_generate_latest.return_value = b'# HELP connections Active connections\n# TYPE connections gauge\nconnections{type="teacher"} 1.0\n'

    response = client.get("/metrics")

    assert response.status_code == 200
    # Prometheus content type (버전은 구현에 따라 다를 수 있음)
    assert "text/plain" in response.headers["content-type"]
    assert b"connections" in response.content

    # generate_latest 호출 확인
    mock_generate_latest.assert_called_once()


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.manager")
@patch("routers.monitoring.active_connections")
@patch("routers.monitoring.generate_latest")
def test_metrics_updates_active_connections(
    mock_generate_latest, mock_active_connections, mock_manager, client
):
    """메트릭이 현재 연결 수를 업데이트하는지 확인"""
    mock_manager.teacher = MagicMock()
    mock_manager.students = {
        "student1": MagicMock(),
        "student2": MagicMock(),
        "student3": MagicMock(),
    }
    mock_manager.monitors = {"monitor1": MagicMock()}

    mock_generate_latest.return_value = b""

    response = client.get("/metrics")

    assert response.status_code == 200

    # active_connections 메트릭이 업데이트되었는지 확인
    assert mock_active_connections.labels.call_count >= 3  # teacher, student, monitor
    mock_active_connections.labels.assert_any_call(type="teacher")
    mock_active_connections.labels.assert_any_call(type="student")
    mock_active_connections.labels.assert_any_call(type="monitor")


@patch.dict("os.environ", {"MODE": "main"})
@patch("routers.monitoring.manager")
@patch("routers.monitoring.cluster_manager")
@patch("routers.monitoring.cluster_nodes_total")
@patch("routers.monitoring.generate_latest")
def test_metrics_main_mode_cluster_metrics(
    mock_generate_latest,
    mock_cluster_nodes_total,
    mock_cluster_manager,
    mock_manager,
    client,
):
    """Main 모드에서 클러스터 메트릭 업데이트"""
    mock_manager.teacher = None
    mock_manager.students = {}
    mock_manager.monitors = {}

    # Mock cluster nodes
    mock_node1 = MagicMock()
    mock_node1.node_id = "sub-001"
    mock_node1.status = "active"
    mock_node1.load_percentage = 45.5
    mock_node1.current_connections = 20

    mock_node2 = MagicMock()
    mock_node2.node_id = "sub-002"
    mock_node2.status = "offline"
    mock_node2.load_percentage = 0.0
    mock_node2.current_connections = 0

    mock_cluster_manager.nodes = {"sub-001": mock_node1, "sub-002": mock_node2}
    mock_generate_latest.return_value = b""

    response = client.get("/metrics")

    assert response.status_code == 200

    # 클러스터 노드 상태 메트릭 업데이트 확인
    mock_cluster_nodes_total.labels.assert_any_call(status="active")
    mock_cluster_nodes_total.labels.assert_any_call(status="offline")


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.manager")
@patch("routers.monitoring.generate_latest")
def test_metrics_no_connections(mock_generate_latest, mock_manager, client):
    """연결 없을 때 메트릭"""
    mock_manager.teacher = None
    mock_manager.students = {}
    mock_manager.monitors = {}

    mock_generate_latest.return_value = b"# No connections\n"

    response = client.get("/metrics")

    assert response.status_code == 200


# ==================== MediaMTX Viewers Tests ====================


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_stream_active(mock_httpx_client, client):
    """뷰어 조회: 활성 스트림"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": True,
                "readers": [
                    {"id": "reader1", "created": "2025-01-01T12:00:00Z"},
                    {"id": "reader2", "created": "2025-01-01T12:05:00Z"},
                    {"id": "reader3", "created": "2025-01-01T12:10:00Z"},
                ],
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["total_viewers"] == 3
    assert data["stream_ready"] is True
    assert data["cluster_mode"] == "standalone"
    assert len(data["viewers"]) == 3

    # 뷰어 정보 확인
    assert data["viewers"][0]["id"] == "reader1"
    assert data["viewers"][0]["type"] == "webrtc"
    assert data["viewers"][0]["node"] == "main"

    # Main node stats 확인
    assert "main" in data["node_stats"]
    assert data["node_stats"]["main"]["viewers"] == 3
    assert data["node_stats"]["main"]["status"] == "active"


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_no_stream(mock_httpx_client, client):
    """뷰어 조회: 스트림 없음"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": False,
                "readers": [],
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["total_viewers"] == 0
    assert data["stream_ready"] is False
    assert data["viewers"] == []


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_no_live_stream_path(mock_httpx_client, client):
    """뷰어 조회: live/stream 경로 없음"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "other/path",
                "ready": True,
                "readers": [{"id": "reader1"}],
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["total_viewers"] == 0
    assert data["stream_ready"] is False


@patch.dict("os.environ", {"MODE": "main"})
@patch("routers.monitoring.httpx.AsyncClient")
@patch("routers.monitoring.cluster_manager")
def test_get_viewers_main_mode_with_sub_nodes(mock_cluster_manager, mock_httpx_client, client):
    """Main 모드: Sub 노드 정보 포함"""
    # Main node MediaMTX 응답
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": True,
                "readers": [{"id": "reader1", "created": "2025-01-01T12:00:00Z"}],
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    # Mock cluster manager - sub nodes
    mock_cluster_manager.get_all_nodes.return_value = [
        {"node_name": "sub-001", "webrtc_port": 8890},
        {"node_name": "sub-002", "webrtc_port": 8891},
    ]

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["cluster_mode"] == "main"
    assert data["total_viewers"] == 1

    # Node stats에 main + sub nodes 포함되어야 함
    assert "main" in data["node_stats"]
    assert "sub-001" in data["node_stats"]
    assert "sub-002" in data["node_stats"]

    # Sub node 정보 확인
    assert data["node_stats"]["sub-001"]["viewers"] == 0  # 현재는 placeholder
    assert data["node_stats"]["sub-001"]["status"] == "standby"
    assert data["node_stats"]["sub-001"]["webrtc_port"] == 8890


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_mediamtx_api_error(mock_httpx_client, client):
    """뷰어 조회: MediaMTX API 오류"""
    mock_client_instance = MagicMock()
    mock_client_instance.get.side_effect = Exception("Connection refused")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    # 오류 시에도 정상 응답 (빈 데이터)
    assert data["total_viewers"] == 0
    assert data["stream_ready"] is False
    assert "error" in data


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_mediamtx_timeout(mock_httpx_client, client):
    """뷰어 조회: MediaMTX API 타임아웃"""
    import httpx

    mock_client_instance = MagicMock()
    mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["total_viewers"] == 0
    assert "error" in data


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_mediamtx_404(mock_httpx_client, client):
    """뷰어 조회: MediaMTX API 404"""
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["stream_ready"] is False


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_load_percentage_calculation(mock_httpx_client, client):
    """뷰어 조회: 로드 퍼센트 계산 검증"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "name": "live/stream",
                "ready": True,
                "readers": [{"id": f"reader{i}", "created": ""} for i in range(75)],
            }
        ]
    }

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["total_viewers"] == 75

    # Load percentage: 75 / 150 * 100 = 50.0%
    assert data["node_stats"]["main"]["load_percent"] == 50.0


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.monitoring.httpx.AsyncClient")
def test_get_viewers_empty_items_list(mock_httpx_client, client):
    """뷰어 조회: items 리스트가 비어있는 경우"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}

    mock_client_instance = MagicMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.get("/api/viewers")

    assert response.status_code == 200
    data = response.json()

    assert data["total_viewers"] == 0
    assert data["stream_ready"] is False
