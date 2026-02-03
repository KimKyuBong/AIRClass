"""
Tests for Authentication & Token Router
========================================
스트림 접근 토큰 발급 엔드포인트 테스트 (클러스터 지원)

Test Coverage:
- Standalone mode token generation
- Main mode load balancing (student)
- Main mode direct serving (teacher, monitor)
- Sub mode token generation
- Docker port mapping & URL rewriting
- Token validation
- Error handling
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, UTC
import jwt

from routers.auth import router
from utils.jwt_auth import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
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
def mock_node():
    """Mock Sub Node 정보"""
    return NodeInfo(
        node_id="sub-test-001",
        node_name="Sub Node Test 1",
        host="10.100.0.10",
        port=8001,
        rtmp_port=1936,
        webrtc_port=8890,
        max_connections=150,
        current_connections=10,
        cpu_usage=25.5,
        memory_usage=45.2,
        status="healthy",
        last_heartbeat=datetime.now(),
    )


@pytest.fixture
def mock_main_node():
    """Mock Main Node 정보"""
    return NodeInfo(
        node_id="main",
        node_name="Main Node",
        host="10.100.0.146",
        port=8000,
        rtmp_port=1935,
        webrtc_port=8889,
        max_connections=150,
        current_connections=5,
        cpu_usage=15.0,
        memory_usage=30.0,
        status="healthy",
        last_heartbeat=datetime.now(),
    )


# ==================== Standalone Mode Tests ====================


@patch.dict(
    "os.environ",
    {"MODE": "standalone", "NODE_HOST": "localhost", "WEBRTC_PORT": "8889"},
)
@patch("routers.auth.generate_stream_token")
@patch("routers.auth.tokens_issued_total")
def test_standalone_token_for_teacher(mock_metrics, mock_generate_token, client):
    """Standalone: 교사 토큰 발급 (publish)"""
    mock_generate_token.return_value = "test_teacher_token_123"

    response = client.post(
        "/api/token",
        params={"user_type": "teacher", "user_id": "teacher1", "action": "publish"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["token"] == "test_teacher_token_123"
    assert data["user_type"] == "teacher"
    assert data["user_id"] == "teacher1"
    assert data["action"] == "publish"
    assert data["mode"] == "standalone"
    assert data["expires_in"] == JWT_EXPIRATION_MINUTES * 60
    assert "whip" in data["webrtc_url"]  # WHIP for publishing

    # Token 발급 함수 호출 확인
    mock_generate_token.assert_called_once_with("teacher", "teacher1", "publish")
    mock_metrics.labels.assert_called_with(user_type="teacher")


@patch.dict(
    "os.environ",
    {"MODE": "standalone", "NODE_HOST": "localhost", "WEBRTC_PORT": "8889"},
)
@patch("routers.auth.generate_stream_token")
def test_standalone_token_for_student(mock_generate_token, client):
    """Standalone: 학생 토큰 발급 (read)"""
    mock_generate_token.return_value = "test_student_token_456"

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student1", "action": "read"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["token"] == "test_student_token_456"
    assert data["user_type"] == "student"
    assert data["user_id"] == "student1"
    assert data["action"] == "read"
    assert "whep" in data["webrtc_url"]  # WHEP for reading

    mock_generate_token.assert_called_once_with("student", "student1", "read")


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.auth.generate_stream_token")
def test_standalone_token_for_monitor(mock_generate_token, client):
    """Standalone: 모니터 토큰 발급 (read)"""
    mock_generate_token.return_value = "test_monitor_token_789"

    response = client.post(
        "/api/token",
        params={"user_type": "monitor", "user_id": "monitor1"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["token"] == "test_monitor_token_789"
    assert data["user_type"] == "monitor"
    assert data["user_id"] == "monitor1"
    assert data["action"] == "read"  # Default action


# ==================== Main Mode Tests (Load Balancing) ====================


@patch.dict("os.environ", {"MODE": "main", "USE_MAIN_WEBRTC": "false"})
@patch("routers.auth.SERVER_IP", "10.100.0.146")
@patch("routers.auth.cluster_manager")
@patch("routers.auth.httpx.AsyncClient")
@patch("routers.auth.subprocess.run")
def test_main_mode_student_load_balancing(
    mock_subprocess, mock_httpx_client, mock_cluster, client, mock_node
):
    """Main Mode: 학생 요청 시 Sub 노드로 로드 밸런싱"""
    # Cluster manager가 sub 노드 반환
    mock_cluster.get_node_for_stream.return_value = mock_node
    mock_cluster.main_node_id = "main"

    # Sub 노드 응답 모의
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "token": "sub_node_token_123",
        "webrtc_url": "http://10.100.0.10:8890/live/stream/whep?jwt=sub_node_token_123",
        "expires_in": 3600,
        "user_type": "student",
        "user_id": "student1",
        "mode": "sub",
        "action": "read",
    }

    # AsyncClient mock
    mock_client_instance = AsyncMock()
    mock_client_instance.post.return_value = mock_response
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    # Docker port mapping mock
    mock_subprocess.return_value = MagicMock(
        returncode=0,
        stdout="airclass-sub-1\t0.0.0.0:8001->8000/tcp, 0.0.0.0:18890->8889/tcp\n",
    )

    # Hostname check mock
    with patch("routers.auth.subprocess.run") as mock_hostname:
        mock_hostname.side_effect = [
            # First call: docker ps
            MagicMock(
                returncode=0,
                stdout="airclass-sub-1\t0.0.0.0:8001->8000/tcp, 0.0.0.0:18890->8889/tcp\n",
            ),
            # Second call: hostname check
            MagicMock(returncode=0, stdout="test-001\n"),
        ]

        response = client.post(
            "/api/token",
            params={"user_type": "student", "user_id": "student1", "action": "read"},
        )

    assert response.status_code == 200
    data = response.json()

    # Sub 노드에서 받은 토큰 반환 확인
    assert data["token"] == "sub_node_token_123"
    assert data["routed_by"] == "main"
    assert data["node_id"] == "sub-test-001"
    assert data["node_name"] == "Sub Node Test 1"

    # WebRTC URL이 Docker 외부 포트로 rewrite되었는지 확인
    assert "10.100.0.146:18890" in data["webrtc_url"]  # SERVER_IP + external port

    # Cluster manager 호출 확인
    mock_cluster.get_node_for_stream.assert_called_once_with(
        "student1", use_sticky=True
    )


@patch.dict(
    "os.environ",
    {"MODE": "main", "SERVER_IP": "10.100.0.146", "USE_MAIN_WEBRTC": "false"},
)
@patch("routers.auth.cluster_manager")
@patch("routers.auth.generate_stream_token")
def test_main_mode_teacher_direct_serving(
    mock_generate_token, mock_cluster, client, mock_main_node
):
    """Main Mode: 교사는 항상 Main 노드에서 직접 서빙"""
    mock_generate_token.return_value = "main_teacher_token_456"
    mock_cluster.main_node_id = "main"

    response = client.post(
        "/api/token",
        params={"user_type": "teacher", "user_id": "teacher1", "action": "publish"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["token"] == "main_teacher_token_456"
    assert data["mode"] == "main"
    assert data["user_type"] == "teacher"
    assert data["action"] == "publish"

    # Teacher는 로드 밸런싱하지 않음
    mock_cluster.get_node_for_stream.assert_not_called()
    mock_generate_token.assert_called_once_with("teacher", "teacher1", "publish")


@patch.dict(
    "os.environ",
    {
        "MODE": "main",
        "USE_MAIN_WEBRTC": "false",
        "NODE_NAME": "Main Node",
        "NODE_ID": "main",
    },
)
@patch("routers.auth.cluster_manager")
@patch("routers.auth.generate_stream_token")
def test_main_mode_main_node_selected(
    mock_generate_token, mock_cluster, client, mock_main_node
):
    """Main Mode: Rendezvous hashing 결과 Main 노드 자신이 선택된 경우"""
    # Cluster manager가 Main 노드 자신을 반환
    mock_cluster.get_node_for_stream.return_value = mock_main_node
    mock_cluster.main_node_id = "main"
    mock_generate_token.return_value = "main_node_token_789"

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student2", "action": "read"},
    )

    assert response.status_code == 200
    data = response.json()

    # Main 노드에서 직접 토큰 발급 (리다이렉트 없음)
    assert data["token"] == "main_node_token_789"
    assert data["mode"] == "main"
    assert data["node_name"] == "Main Node"  # NODE_NAME env var
    assert data["node_id"] == "main"

    mock_generate_token.assert_called_once_with("student", "student2", "read")


@patch.dict("os.environ", {"MODE": "main", "USE_MAIN_WEBRTC": "false"})
@patch("routers.auth.cluster_manager")
def test_main_mode_no_healthy_nodes(mock_cluster, client):
    """Main Mode: Healthy 노드 없음 (503 에러)"""
    mock_cluster.get_node_for_stream.return_value = None

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student1", "action": "read"},
    )

    assert response.status_code == 503
    assert "No healthy nodes available" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "USE_MAIN_WEBRTC": "false"})
@patch("routers.auth.cluster_manager")
@patch("routers.auth.httpx.AsyncClient")
def test_main_mode_sub_node_communication_error(
    mock_httpx_client, mock_cluster, client, mock_node
):
    """Main Mode: Sub 노드 통신 실패 (503 에러)"""
    mock_cluster.get_node_for_stream.return_value = mock_node
    mock_cluster.main_node_id = "main"

    # AsyncClient 통신 실패 모의
    mock_client_instance = AsyncMock()
    mock_client_instance.post.side_effect = Exception("Connection timeout")
    mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student1", "action": "read"},
    )

    assert response.status_code == 503
    assert "Node communication error" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "main", "USE_MAIN_WEBRTC": "true"})
@patch("routers.auth.generate_stream_token")
def test_main_mode_bypass_load_balancing(mock_generate_token, client):
    """Main Mode: USE_MAIN_WEBRTC=true로 로드 밸런싱 우회 (개발 모드)"""
    mock_generate_token.return_value = "main_direct_token_999"

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student1", "action": "read"},
    )

    assert response.status_code == 200
    data = response.json()

    # 로드 밸런싱 없이 Main에서 직접 발급
    assert data["token"] == "main_direct_token_999"
    assert data["mode"] == "main"


# ==================== Sub Mode Tests ====================


@patch.dict(
    "os.environ", {"MODE": "sub", "NODE_HOST": "10.100.0.10", "WEBRTC_PORT": "8890"}
)
@patch("routers.auth.generate_stream_token")
def test_sub_mode_token_generation(mock_generate_token, client):
    """Sub Mode: 직접 토큰 발급"""
    mock_generate_token.return_value = "sub_token_111"

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student3", "action": "read"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["token"] == "sub_token_111"
    assert data["mode"] == "sub"
    assert data["user_type"] == "student"
    assert "10.100.0.10:8890" in data["webrtc_url"]  # Sub의 host:port

    mock_generate_token.assert_called_once_with("student", "student3", "read")


# ==================== Validation Tests ====================


@patch.dict("os.environ", {"MODE": "standalone"})
def test_invalid_user_type(client):
    """Invalid user_type 검증"""
    response = client.post(
        "/api/token",
        params={"user_type": "hacker", "user_id": "bad_user"},
    )

    assert response.status_code == 400
    assert "Invalid user_type" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "standalone"})
def test_empty_user_id(client):
    """Empty user_id 검증"""
    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": ""},
    )

    assert response.status_code == 400
    assert "user_id required" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "standalone"})
def test_student_cannot_publish(client):
    """학생은 publish 불가능"""
    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student1", "action": "publish"},
    )

    assert response.status_code == 403
    assert "Only teachers can publish" in response.json()["detail"]


@patch.dict("os.environ", {"MODE": "standalone"})
def test_monitor_cannot_publish(client):
    """모니터도 publish 불가능"""
    response = client.post(
        "/api/token",
        params={"user_type": "monitor", "user_id": "monitor1", "action": "publish"},
    )

    assert response.status_code == 403
    assert "Only teachers can publish" in response.json()["detail"]


# ==================== Token Content Validation ====================


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.auth.generate_stream_token")
def test_token_jwt_format(mock_generate_token, client):
    """JWT 토큰 형식 검증"""
    # 실제 JWT 토큰 생성
    from utils.jwt_auth import generate_stream_token as real_generate_token

    real_token = real_generate_token("teacher", "teacher1", "publish")
    mock_generate_token.return_value = real_token

    response = client.post(
        "/api/token",
        params={"user_type": "teacher", "user_id": "teacher1", "action": "publish"},
    )

    assert response.status_code == 200
    token = response.json()["token"]

    # JWT 디코딩 확인
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

    assert payload["user_type"] == "teacher"
    assert payload["user_id"] == "teacher1"
    assert payload["action"] == "publish"
    assert payload["path"] == "live/stream"
    assert "exp" in payload
    assert "iat" in payload


@patch.dict("os.environ", {"MODE": "standalone"})
@patch("routers.auth.generate_stream_token")
def test_token_expiration(mock_generate_token, client):
    """토큰 만료 시간 검증"""
    from utils.jwt_auth import generate_stream_token as real_generate_token

    real_token = real_generate_token("student", "student1", "read")
    mock_generate_token.return_value = real_token

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student1"},
    )

    assert response.status_code == 200
    data = response.json()

    # expires_in이 올바른지 확인
    assert data["expires_in"] == JWT_EXPIRATION_MINUTES * 60

    # JWT 만료 시간 확인
    payload = jwt.decode(data["token"], JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
    iat_time = datetime.fromtimestamp(payload["iat"], tz=UTC)

    # 만료 시간이 발급 시간 + JWT_EXPIRATION_MINUTES인지 확인
    expected_exp = iat_time + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    assert abs((exp_time - expected_exp).total_seconds()) < 2  # 2초 오차 허용


# ==================== URL Format Tests ====================


@patch.dict(
    "os.environ",
    {"MODE": "standalone", "NODE_HOST": "example.com", "WEBRTC_PORT": "9999"},
)
@patch("routers.auth.generate_stream_token")
def test_webrtc_url_format_publish(mock_generate_token, client):
    """WebRTC URL 형식 검증 (publish - WHIP)"""
    mock_generate_token.return_value = "token123"

    response = client.post(
        "/api/token",
        params={"user_type": "teacher", "user_id": "teacher1", "action": "publish"},
    )

    assert response.status_code == 200
    webrtc_url = response.json()["webrtc_url"]

    assert webrtc_url == "http://example.com:9999/live/stream/whip?jwt=token123"


@patch.dict(
    "os.environ",
    {"MODE": "standalone", "NODE_HOST": "example.com", "WEBRTC_PORT": "9999"},
)
@patch("routers.auth.generate_stream_token")
def test_webrtc_url_format_read(mock_generate_token, client):
    """WebRTC URL 형식 검증 (read - WHEP)"""
    mock_generate_token.return_value = "token456"

    response = client.post(
        "/api/token",
        params={"user_type": "student", "user_id": "student1", "action": "read"},
    )

    assert response.status_code == 200
    webrtc_url = response.json()["webrtc_url"]

    assert webrtc_url == "http://example.com:9999/live/stream/whep?jwt=token456"


@patch.dict("os.environ", {"MODE": "main", "WEBRTC_PORT": "8889"})
@patch("routers.auth.SERVER_IP", "192.168.1.100")
@patch("routers.auth.generate_stream_token")
def test_main_mode_uses_server_ip(mock_generate_token, client):
    """Main Mode는 SERVER_IP 사용"""
    mock_generate_token.return_value = "main_token_789"

    response = client.post(
        "/api/token",
        params={"user_type": "teacher", "user_id": "teacher1", "action": "publish"},
    )

    assert response.status_code == 200
    webrtc_url = response.json()["webrtc_url"]

    # SERVER_IP가 URL에 포함되어야 함
    assert "192.168.1.100" in webrtc_url
