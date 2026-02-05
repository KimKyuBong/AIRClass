"""
Tests for LiveKit Router
=========================
LiveKit API 엔드포인트 테스트

Test Coverage:
- POST /api/livekit/token: JWT 토큰 발급
- GET /api/livekit/rooms: 방 목록 조회
- GET /api/livekit/rooms/{room_name}/participants: 참가자 목록
- DELETE /api/livekit/rooms/{room_name}: 방 삭제
- POST /api/livekit/rooms/{room_name}/participants/{identity}/remove: 참가자 제거
"""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
import jwt

import sys

sys.path.insert(0, "/app")

from routers.livekit import router, LIVEKIT_API_KEY, LIVEKIT_API_SECRET


@pytest.fixture
def app():
    """FastAPI 앱 생성"""
    app = FastAPI()
    app.include_router(router)  # router already has /api/livekit prefix
    return app


@pytest_asyncio.fixture
async def async_client(app):
    """비동기 HTTP 클라이언트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ==================== Token Generation Tests ====================


@pytest.mark.asyncio
async def test_create_token_teacher(async_client):
    """Teacher 토큰 발급: 송출 권한 포함"""
    response = await async_client.post(
        "/api/livekit/token",  # prefix already included in app fixture
        params={"user_id": "teacher_001", "room_name": "math_class", "user_type": "teacher"},
    )

    assert response.status_code == 200
    data = response.json()

    # 응답 구조 검증
    assert "token" in data
    assert "url" in data
    assert "room_name" in data
    assert "identity" in data
    assert "user_type" in data

    assert data["room_name"] == "math_class"
    assert data["identity"] == "teacher_001"
    assert data["user_type"] == "teacher"

    # JWT 토큰 디코딩 (서명 검증 없이)
    decoded = jwt.decode(data["token"], options={"verify_signature": False})

    # Teacher 권한 검증
    assert decoded["video"]["room"] == "math_class"
    assert decoded["video"]["roomJoin"] is True
    assert decoded["video"]["canPublish"] is True  # 송출 가능
    assert decoded["video"]["canSubscribe"] is True  # 수신 가능
    assert decoded["video"]["roomCreate"] is True  # 방 생성 가능


@pytest.mark.asyncio
async def test_create_token_student(async_client):
    """Student 토큰 발급: 수신 전용"""
    response = await async_client.post(
        "/api/livekit/token",
        params={"user_id": "student_123", "room_name": "math_class", "user_type": "student"},
    )

    assert response.status_code == 200
    data = response.json()

    # JWT 토큰 디코딩
    decoded = jwt.decode(data["token"], options={"verify_signature": False})

    # Student 권한 검증 (수신만 가능)
    assert decoded["video"]["roomJoin"] is True
    assert decoded["video"]["canPublish"] is False  # 송출 불가
    assert decoded["video"]["canSubscribe"] is True  # 수신 가능


@pytest.mark.asyncio
async def test_create_token_invalid_user_type(async_client):
    """잘못된 user_type: 500 에러 (AccessToken 생성 실패)"""
    response = await async_client.post(
        "/api/livekit/token",
        params={
            "user_id": "user_999",
            "room_name": "test_room",
            "user_type": "admin",  # 잘못된 타입
        },
    )

    # 현재 구현은 500 에러 반환 (향후 400으로 개선 가능)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_create_token_missing_params(async_client):
    """필수 파라미터 누락: 422 에러"""
    response = await async_client.post(
        "/api/livekit/token",
        params={
            "user_id": "test_user"
            # room_name, user_type 누락
        },
    )

    assert response.status_code == 422


# ==================== Room Management Tests ====================


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_list_rooms_empty(mock_get_api, async_client):
    """방 목록 조회: 빈 목록"""
    mock_api = AsyncMock()
    mock_api.room.list_rooms.return_value = MagicMock(rooms=[])
    mock_get_api.return_value = mock_api

    response = await async_client.get("/api/livekit/rooms")

    assert response.status_code == 200
    data = response.json()

    assert data["rooms"] == []
    assert data["count"] == 0


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_list_rooms_with_data(mock_get_api, async_client):
    """방 목록 조회: 데이터 있음"""
    mock_room = MagicMock()
    mock_room.name = "math_class"
    mock_room.num_participants = 25
    mock_room.max_participants = 200
    mock_room.creation_time = 1234567890
    mock_room.empty_timeout = 300

    mock_api = AsyncMock()
    mock_api.room.list_rooms.return_value = MagicMock(rooms=[mock_room])
    mock_api.aclose = AsyncMock()
    mock_get_api.return_value = mock_api

    response = await async_client.get("/api/livekit/rooms")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 1
    assert len(data["rooms"]) == 1

    room = data["rooms"][0]
    assert room["name"] == "math_class"
    assert room["num_participants"] == 25
    assert room["max_participants"] == 200


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_delete_room_success(mock_get_api, async_client):
    """방 삭제 성공"""
    mock_api = AsyncMock()
    mock_api.room.delete_room.return_value = None
    mock_get_api.return_value = mock_api

    response = await async_client.delete("/api/livekit/rooms/test_room")

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Room deleted successfully"
    assert data["room_name"] == "test_room"


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_delete_room_not_found(mock_get_api, async_client):
    """존재하지 않는 방 삭제: 404 에러"""
    mock_api = AsyncMock()
    mock_api.room.delete_room.side_effect = Exception("Room not found")
    mock_get_api.return_value = mock_api

    response = await async_client.delete("/api/livekit/rooms/nonexistent")

    assert response.status_code == 500


# ==================== Participant Management Tests ====================


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_list_participants(mock_get_api, async_client):
    """참가자 목록 조회"""
    mock_participant = MagicMock()
    mock_participant.identity = "student_001"
    mock_participant.name = "student_001"
    mock_participant.state = 0  # ACTIVE state enum value
    mock_participant.is_publisher = False
    mock_participant.joined_at = 1234567890
    mock_participant.tracks = []

    mock_api = AsyncMock()
    mock_api.room.list_participants.return_value = MagicMock(participants=[mock_participant])
    mock_api.aclose = AsyncMock()
    mock_get_api.return_value = mock_api

    response = await async_client.get("/api/livekit/rooms/math_class/participants")

    assert response.status_code == 200
    data = response.json()

    assert data["count"] == 1
    assert len(data["participants"]) == 1

    participant = data["participants"][0]
    assert participant["identity"] == "student_001"
    assert participant["is_publisher"] is False


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_remove_participant_success(mock_get_api, async_client):
    """참가자 제거 성공"""
    mock_api = AsyncMock()
    mock_api.room.remove_participant.return_value = None
    mock_api.aclose = AsyncMock()
    mock_get_api.return_value = mock_api

    response = await async_client.delete("/api/livekit/rooms/math_class/participants/student_001")

    assert response.status_code == 200
    data = response.json()

    assert data["message"] == "Participant removed successfully"
    assert data["room_name"] == "math_class"
    assert data["identity"] == "student_001"


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_remove_participant_not_found(mock_get_api, async_client):
    """존재하지 않는 참가자 제거: 500 에러"""
    mock_api = AsyncMock()
    mock_api.room.remove_participant.side_effect = Exception("Participant not found")
    mock_api.aclose = AsyncMock()
    mock_get_api.return_value = mock_api

    response = await async_client.delete("/api/livekit/rooms/math_class/participants/nonexistent")

    assert response.status_code == 500


# ==================== Edge Cases ====================


@pytest.mark.asyncio
async def test_token_generation_special_characters(async_client):
    """특수 문자 포함 user_id/room_name"""
    response = await async_client.post(
        "/api/livekit/token",
        params={
            "user_id": "teacher@school.com",
            "room_name": "2024-수학-1반",
            "user_type": "teacher",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # JWT에 특수 문자가 올바르게 인코딩되었는지 확인
    decoded = jwt.decode(data["token"], options={"verify_signature": False})
    assert decoded["sub"] == "teacher@school.com"


@pytest.mark.asyncio
@patch("routers.livekit.get_livekit_api")
async def test_api_connection_failure(mock_get_api, async_client):
    """LiveKit API 연결 실패 시나리오"""
    mock_get_api.side_effect = Exception("Connection refused")

    response = await async_client.get("/api/livekit/rooms")

    assert response.status_code == 500
    assert "Connection refused" in response.json()["detail"]
