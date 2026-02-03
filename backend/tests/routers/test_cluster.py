"""
Tests for Cluster Management Router
====================================
클러스터 노드 등록/해제 및 통계 엔드포인트 테스트

Test Coverage:
- POST /cluster/register: Sub 노드 등록 (HMAC 인증)
- POST /cluster/unregister: Sub 노드 등록 해제
- POST /cluster/stats: 노드 통계 업데이트 (HMAC 인증)
- GET /cluster/nodes: 클러스터 노드 목록 조회
- Main-only 엔드포인트 보호 검증
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime
import hashlib
import hmac
import time

from routers.cluster import router
from core.cluster import NodeInfo


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
def mock_node_data():
    """Mock Sub Node 등록 데이터"""
    return {
        "node_id": "sub-test-001",
        "node_name": "Test Sub Node 1",
        "host": "10.100.0.10",
        "port": 8001,
        "rtmp_port": 1936,
        "webrtc_port": 8890,
        "max_connections": 150,
        "current_connections": 5,
        "cpu_usage": 20.0,
        "memory_usage": 35.5,
        "status": "healthy",
        "last_heartbeat": datetime.now().isoformat(),
    }


def generate_hmac_token(secret: str, timestamp: str) -> str:
    """HMAC 토큰 생성 (실제 구현과 동일)"""
    message = f"{timestamp}:{secret}"
    return hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()


# ==================== Node Registration Tests ====================


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
@patch("routers.cluster.cluster_manager")
def test_register_node_success(mock_cluster_manager, client, mock_node_data):
    """노드 등록 성공 (정상 HMAC 인증)"""
    timestamp = str(int(time.time()))
    auth_token = generate_hmac_token("test_secret_key", timestamp)

    payload = {
        **mock_node_data,
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "registered"
    assert data["node_id"] == "sub-test-001"

    # cluster_manager.register_node 호출 확인
    mock_cluster_manager.register_node.assert_called_once()
    called_node = mock_cluster_manager.register_node.call_args[0][0]
    assert isinstance(called_node, NodeInfo)
    assert called_node.node_id == "sub-test-001"
    assert called_node.node_name == "Test Sub Node 1"


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
def test_register_node_invalid_hmac(client, mock_node_data):
    """노드 등록 실패: 잘못된 HMAC 토큰"""
    timestamp = str(int(time.time()))
    invalid_token = "wrong_hmac_token_12345"

    payload = {
        **mock_node_data,
        "auth_token": invalid_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 403
    assert "Authentication failed" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
def test_register_node_missing_auth_token(client, mock_node_data):
    """노드 등록 실패: auth_token 누락"""
    timestamp = str(int(time.time()))

    payload = {
        **mock_node_data,
        "timestamp": timestamp,
        # auth_token 누락
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 403
    assert "Authentication required" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
def test_register_node_missing_timestamp(client, mock_node_data):
    """노드 등록 실패: timestamp 누락"""
    auth_token = generate_hmac_token("test_secret_key", str(int(time.time())))

    payload = {
        **mock_node_data,
        "auth_token": auth_token,
        # timestamp 누락
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 403
    assert "Authentication required" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": ""})
def test_register_node_no_cluster_secret(client, mock_node_data):
    """노드 등록 실패: CLUSTER_SECRET 미설정"""
    timestamp = str(int(time.time()))
    auth_token = "any_token"

    payload = {
        **mock_node_data,
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 500
    assert "Server configuration error" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "standalone"})
def test_register_node_standalone_mode_forbidden(client, mock_node_data):
    """Standalone 모드에서 노드 등록 금지"""
    timestamp = str(int(time.time()))
    auth_token = generate_hmac_token("test_secret", timestamp)

    payload = {
        **mock_node_data,
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 403
    assert "Only main can register nodes" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "sub"})
def test_register_node_sub_mode_forbidden(client, mock_node_data):
    """Sub 모드에서 노드 등록 금지"""
    timestamp = str(int(time.time()))
    auth_token = generate_hmac_token("test_secret", timestamp)

    payload = {
        **mock_node_data,
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 403
    assert "Only main can register nodes" in response.json()["detail"]


# ==================== Node Unregistration Tests ====================


@patch.dict("os.environ", {"MODE": "main"})
@patch("routers.cluster.cluster_manager")
def test_unregister_node_success(mock_cluster_manager, client):
    """노드 등록 해제 성공"""
    mock_cluster_manager.unregister_node.return_value = True

    response = client.post("/cluster/unregister", json={"node_id": "sub-test-001"})

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "unregistered"
    assert data["node_id"] == "sub-test-001"

    mock_cluster_manager.unregister_node.assert_called_once_with("sub-test-001")


@patch.dict("os.environ", {"MODE": "main"})
@patch("routers.cluster.cluster_manager")
def test_unregister_node_not_found(mock_cluster_manager, client):
    """노드 등록 해제 실패: 존재하지 않는 노드"""
    mock_cluster_manager.unregister_node.return_value = False

    response = client.post("/cluster/unregister", json={"node_id": "nonexistent"})

    assert response.status_code == 404
    assert "Node not found" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "standalone"})
def test_unregister_node_standalone_mode_forbidden(client):
    """Standalone 모드에서 노드 해제 금지"""
    response = client.post("/cluster/unregister", json={"node_id": "sub-test-001"})

    assert response.status_code == 403
    assert "Only main can unregister nodes" in response.json()["detail"]


# ==================== Stats Update Tests ====================


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
@patch("routers.cluster.cluster_manager")
def test_update_node_stats_success(mock_cluster_manager, client):
    """노드 통계 업데이트 성공"""
    mock_cluster_manager.update_node_stats.return_value = True

    timestamp = str(int(time.time()))
    auth_token = generate_hmac_token("test_secret_key", timestamp)

    payload = {
        "node_id": "sub-test-001",
        "stats": {
            "current_connections": 25,
            "cpu_usage": 45.5,
            "memory_usage": 60.2,
        },
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/stats", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "updated"

    # update_node_stats 호출 확인
    mock_cluster_manager.update_node_stats.assert_called_once_with(
        "sub-test-001",
        {
            "current_connections": 25,
            "cpu_usage": 45.5,
            "memory_usage": 60.2,
        },
    )


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
def test_update_node_stats_invalid_hmac(client):
    """통계 업데이트 실패: 잘못된 HMAC"""
    timestamp = str(int(time.time()))
    invalid_token = "wrong_token"

    payload = {
        "node_id": "sub-test-001",
        "stats": {"current_connections": 25},
        "auth_token": invalid_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/stats", json=payload)

    assert response.status_code == 403
    assert "Authentication failed" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
def test_update_node_stats_missing_auth(client):
    """통계 업데이트 실패: 인증 정보 누락"""
    payload = {
        "node_id": "sub-test-001",
        "stats": {"current_connections": 25},
        # auth_token, timestamp 누락
    }

    response = client.post("/cluster/stats", json=payload)

    assert response.status_code == 403
    assert "Authentication required" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
@patch("routers.cluster.cluster_manager")
def test_update_node_stats_node_not_found(mock_cluster_manager, client):
    """통계 업데이트 실패: 노드 없음"""
    mock_cluster_manager.update_node_stats.return_value = False

    timestamp = str(int(time.time()))
    auth_token = generate_hmac_token("test_secret_key", timestamp)

    payload = {
        "node_id": "nonexistent",
        "stats": {"current_connections": 25},
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/stats", json=payload)

    assert response.status_code == 404
    assert "Node not found" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": ""})
def test_update_node_stats_no_cluster_secret(client):
    """통계 업데이트 실패: CLUSTER_SECRET 미설정"""
    timestamp = str(int(time.time()))
    auth_token = "any_token"

    payload = {
        "node_id": "sub-test-001",
        "stats": {},
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/stats", json=payload)

    assert response.status_code == 500
    assert "Server configuration error" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "standalone"})
def test_update_node_stats_standalone_mode_forbidden(client):
    """Standalone 모드에서 통계 업데이트 금지"""
    timestamp = str(int(time.time()))
    auth_token = generate_hmac_token("test_secret", timestamp)

    payload = {
        "node_id": "sub-test-001",
        "stats": {},
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/stats", json=payload)

    assert response.status_code == 403
    assert "Only main can receive stats" in response.json()["detail"]


# ==================== Cluster Nodes List Tests ====================


@patch.dict("os.environ", {"MODE": "main"})
@patch("routers.cluster.cluster_manager")
def test_get_cluster_nodes_success(mock_cluster_manager, client):
    """클러스터 노드 목록 조회 성공"""
    mock_cluster_stats = {
        "total_nodes": 3,
        "healthy_nodes": 2,
        "total_connections": 45,
        "total_capacity": 450,
        "nodes": [
            {
                "node_id": "main",
                "node_name": "Main Node",
                "status": "healthy",
                "current_connections": 10,
                "max_connections": 150,
            },
            {
                "node_id": "sub-001",
                "node_name": "Sub Node 1",
                "status": "healthy",
                "current_connections": 25,
                "max_connections": 150,
            },
            {
                "node_id": "sub-002",
                "node_name": "Sub Node 2",
                "status": "degraded",
                "current_connections": 10,
                "max_connections": 150,
            },
        ],
    }

    mock_cluster_manager.get_cluster_stats.return_value = mock_cluster_stats

    response = client.get("/cluster/nodes")

    assert response.status_code == 200
    data = response.json()

    assert data["total_nodes"] == 3
    assert data["healthy_nodes"] == 2
    assert data["total_connections"] == 45
    assert len(data["nodes"]) == 3

    mock_cluster_manager.get_cluster_stats.assert_called_once()


@patch.dict("os.environ", {"MODE": "main"})
@patch("routers.cluster.cluster_manager")
def test_get_cluster_nodes_empty(mock_cluster_manager, client):
    """클러스터 노드 목록 조회: 노드 없음"""
    mock_cluster_stats = {
        "total_nodes": 0,
        "healthy_nodes": 0,
        "total_connections": 0,
        "total_capacity": 0,
        "nodes": [],
    }

    mock_cluster_manager.get_cluster_stats.return_value = mock_cluster_stats

    response = client.get("/cluster/nodes")

    assert response.status_code == 200
    data = response.json()

    assert data["total_nodes"] == 0
    assert data["nodes"] == []


@patch.dict("os.environ", {"MODE": "standalone"})
def test_get_cluster_nodes_standalone_mode_forbidden(client):
    """Standalone 모드에서 노드 목록 조회 금지"""
    response = client.get("/cluster/nodes")

    assert response.status_code == 403
    assert "Only main has cluster info" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "sub"})
def test_get_cluster_nodes_sub_mode_forbidden(client):
    """Sub 모드에서 노드 목록 조회 금지"""
    response = client.get("/cluster/nodes")

    assert response.status_code == 403
    assert "Only main has cluster info" in response.json()["detail"]


# ==================== HMAC Security Tests ====================


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
def test_hmac_secret_mismatch(client, mock_node_data):
    """HMAC 검증: CLUSTER_SECRET 불일치"""
    timestamp = str(int(time.time()))
    # 다른 secret으로 생성한 토큰
    auth_token = generate_hmac_token("wrong_secret_key", timestamp)

    payload = {
        **mock_node_data,
        "auth_token": auth_token,
        "timestamp": timestamp,
    }

    response = client.post("/cluster/register", json=payload)

    assert response.status_code == 403
    assert "Authentication failed" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "CLUSTER_SECRET": "test_secret_key"})
@patch("routers.cluster.cluster_manager")
def test_hmac_timestamp_integrity(mock_cluster_manager, client, mock_node_data):
    """HMAC 검증: 타임스탬프 위변조 방지"""
    # 정상 타임스탬프로 토큰 생성
    original_timestamp = str(int(time.time()))
    auth_token = generate_hmac_token("test_secret_key", original_timestamp)

    # 타임스탬프 변조 시도
    tampered_timestamp = str(int(time.time()) + 1000)

    payload = {
        **mock_node_data,
        "auth_token": auth_token,
        "timestamp": tampered_timestamp,  # 변조된 타임스탬프
    }

    response = client.post("/cluster/register", json=payload)

    # 타임스탬프 변조로 HMAC 검증 실패
    assert response.status_code == 403
    assert "Authentication failed" in response.json()["detail"]
