"""
WebSocket Router Tests
실시간 통신 기능 테스트

Note: WebSocket 연결 테스트는 httpx.AsyncClient가 WebSocket을 지원하지 않아서
HTTP 브로드캐스트 엔드포인트와 상태 API만 테스트합니다.
실제 WebSocket 연결은 통합 테스트나 수동 테스트로 검증 필요.
"""

import pytest
from httpx import AsyncClient


# ============================================
# Status Endpoint Tests
# ============================================


@pytest.mark.asyncio
async def test_websocket_status_no_connections(async_client: AsyncClient):
    """연결 없는 상태 조회 테스트"""
    response = await async_client.get("/ws/status")
    assert response.status_code == 200
    data = response.json()
    assert data["teacher_connected"] is False
    assert data["students_count"] == 0
    assert data["monitors_count"] == 0
    assert data["students"] == []


# ============================================
# Quiz Broadcast Tests (HTTP Endpoints)
# ============================================


@pytest.mark.asyncio
async def test_broadcast_quiz_http_endpoint(async_client: AsyncClient):
    """퀴즈 브로드캐스트 HTTP 엔드포인트 테스트"""
    response = await async_client.post(
        "/ws/broadcast/quiz",
        json={
            "quiz_id": "quiz123",
            "session_id": "session456",
            "question": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
            "time_limit": 60,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "students_notified" in data
    assert data["quiz_id"] == "quiz123"
    # 연결된 학생이 없으므로 0명에게 알림
    assert data["students_notified"] == 0


@pytest.mark.asyncio
async def test_broadcast_quiz_with_metadata(async_client: AsyncClient):
    """메타데이터 포함 퀴즈 브로드캐스트 테스트"""
    response = await async_client.post(
        "/ws/broadcast/quiz",
        json={
            "quiz_id": "quiz456",
            "session_id": "session789",
            "question": "What is Python?",
            "options": ["A snake", "A programming language", "A movie", "A game"],
            "time_limit": 120,
            "metadata": {"difficulty": "easy", "topic": "programming"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["quiz_id"] == "quiz456"


@pytest.mark.asyncio
async def test_broadcast_quiz_invalid_data(async_client: AsyncClient):
    """잘못된 데이터로 퀴즈 브로드캐스트 테스트"""
    # quiz_id 누락
    response = await async_client.post(
        "/ws/broadcast/quiz",
        json={
            "session_id": "session456",
            "question": "What is 2+2?",
            "options": ["3", "4", "5", "6"],
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_broadcast_quiz_missing_options(async_client: AsyncClient):
    """옵션 누락 퀴즈 브로드캐스트 테스트"""
    response = await async_client.post(
        "/ws/broadcast/quiz",
        json={
            "quiz_id": "quiz123",
            "session_id": "session456",
            "question": "What is 2+2?",
            # options 누락
        },
    )

    assert response.status_code == 422  # Validation error


# ============================================
# Engagement Broadcast Tests (HTTP Endpoints)
# ============================================


@pytest.mark.asyncio
async def test_broadcast_engagement_http_endpoint(async_client: AsyncClient):
    """참여도 브로드캐스트 HTTP 엔드포인트 테스트"""
    response = await async_client.post(
        "/ws/broadcast/engagement",
        json={
            "session_id": "session456",
            "student_id": "student1",
            "student_name": "John Doe",
            "engagement_score": 85.5,
            "attention_score": 0.9,
            "participation_score": 80,
            "quiz_accuracy": 0.85,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["student_id"] == "student1"
    assert "recipients" in data
    # 연결된 교사/모니터가 없으므로 0명에게 전송
    assert data["recipients"] == 0


@pytest.mark.asyncio
async def test_broadcast_engagement_minimal_data(async_client: AsyncClient):
    """최소 데이터로 참여도 브로드캐스트 테스트"""
    response = await async_client.post(
        "/ws/broadcast/engagement",
        json={
            "session_id": "session456",
            "student_id": "student2",
            "student_name": "Jane Smith",
            "engagement_score": 75.0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["student_id"] == "student2"


@pytest.mark.asyncio
async def test_broadcast_engagement_with_metadata(async_client: AsyncClient):
    """메타데이터 포함 참여도 브로드캐스트 테스트"""
    response = await async_client.post(
        "/ws/broadcast/engagement",
        json={
            "session_id": "session456",
            "student_id": "student3",
            "student_name": "Bob Johnson",
            "engagement_score": 92.3,
            "metadata": {"alert_level": "high", "trend": "improving"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_broadcast_engagement_invalid_data(async_client: AsyncClient):
    """잘못된 데이터로 참여도 브로드캐스트 테스트"""
    # student_id 누락
    response = await async_client.post(
        "/ws/broadcast/engagement",
        json={
            "session_id": "session456",
            "student_name": "Test Student",
            "engagement_score": 85.5,
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_broadcast_engagement_missing_score(async_client: AsyncClient):
    """점수 누락 참여도 브로드캐스트 테스트"""
    response = await async_client.post(
        "/ws/broadcast/engagement",
        json={
            "session_id": "session456",
            "student_id": "student1",
            "student_name": "Test Student",
            # engagement_score 누락
        },
    )

    assert response.status_code == 422  # Validation error


# ============================================
# Integration Tests
# ============================================


@pytest.mark.asyncio
async def test_broadcast_quiz_and_check_status(async_client: AsyncClient):
    """퀴즈 브로드캐스트 후 상태 확인 통합 테스트"""
    # 상태 확인 (초기)
    status_response = await async_client.get("/ws/status")
    assert status_response.status_code == 200
    initial_status = status_response.json()

    # 퀴즈 브로드캐스트
    broadcast_response = await async_client.post(
        "/ws/broadcast/quiz",
        json={
            "quiz_id": "integration_quiz",
            "session_id": "integration_session",
            "question": "Integration test question?",
            "options": ["A", "B", "C", "D"],
            "time_limit": 60,
        },
    )

    assert broadcast_response.status_code == 200
    broadcast_data = broadcast_response.json()
    assert broadcast_data["success"] is True

    # 상태 확인 (변화 없음 - WebSocket 연결 없음)
    status_response2 = await async_client.get("/ws/status")
    assert status_response2.status_code == 200
    final_status = status_response2.json()
    assert final_status["students_count"] == initial_status["students_count"]


@pytest.mark.asyncio
async def test_broadcast_engagement_and_check_status(async_client: AsyncClient):
    """참여도 브로드캐스트 후 상태 확인 통합 테스트"""
    # 상태 확인 (초기)
    status_response = await async_client.get("/ws/status")
    assert status_response.status_code == 200

    # 참여도 브로드캐스트
    broadcast_response = await async_client.post(
        "/ws/broadcast/engagement",
        json={
            "session_id": "integration_session",
            "student_id": "integration_student",
            "student_name": "Integration Student",
            "engagement_score": 88.0,
        },
    )

    assert broadcast_response.status_code == 200
    broadcast_data = broadcast_response.json()
    assert broadcast_data["success"] is True

    # 상태 확인 (변화 없음 - WebSocket 연결 없음)
    status_response2 = await async_client.get("/ws/status")
    assert status_response2.status_code == 200


@pytest.mark.asyncio
async def test_multiple_quiz_broadcasts(async_client: AsyncClient):
    """여러 퀴즈 순차 브로드캐스트 테스트"""
    quiz_ids = ["quiz1", "quiz2", "quiz3"]

    for i, quiz_id in enumerate(quiz_ids):
        response = await async_client.post(
            "/ws/broadcast/quiz",
            json={
                "quiz_id": quiz_id,
                "session_id": f"session{i}",
                "question": f"Question {i + 1}?",
                "options": ["A", "B", "C", "D"],
                "time_limit": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["quiz_id"] == quiz_id


@pytest.mark.asyncio
async def test_multiple_engagement_broadcasts(async_client: AsyncClient):
    """여러 학생 참여도 순차 브로드캐스트 테스트"""
    students = [
        {"id": "student1", "name": "Student One", "score": 85.5},
        {"id": "student2", "name": "Student Two", "score": 72.3},
        {"id": "student3", "name": "Student Three", "score": 91.8},
    ]

    for student in students:
        response = await async_client.post(
            "/ws/broadcast/engagement",
            json={
                "session_id": "multi_session",
                "student_id": student["id"],
                "student_name": student["name"],
                "engagement_score": student["score"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["student_id"] == student["id"]
