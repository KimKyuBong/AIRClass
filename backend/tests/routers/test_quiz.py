"""
Tests for Quiz Router
=====================
퀴즈 생성, 발행, 응답, 통계 엔드포인트 테스트 (실제 DB 사용)

Test Coverage:
- POST /api/quiz/create: 퀴즈 생성
- POST /api/quiz/publish: 퀴즈 발행
- POST /api/quiz/response: 학생 응답 제출
- GET /api/quiz/{quiz_id}: 퀴즈 조회
- GET /api/quiz/{quiz_id}/stats: 통계 조회
- DELETE /api/quiz/{quiz_id}: 퀴즈 삭제
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from datetime import datetime

from schemas.quiz import QuizCreate, QuizOption, QuizResponseRequest


@pytest.fixture
def sample_quiz_data():
    """샘플 퀴즈 데이터"""
    return {
        "quiz_id": "quiz_001",
        "session_id": "session_001",
        "question": "What is 2 + 2?",
        "options": [
            {"id": "opt_a", "text": "3"},
            {"id": "opt_b", "text": "4"},
            {"id": "opt_c", "text": "5"},
            {"id": "opt_d", "text": "6"},
        ],
        "correct_option_id": "opt_b",
        "topic": "Mathematics",
        "difficulty": 1,
        "explanation": "2 + 2 equals 4",
    }


# ==================== Quiz Creation Tests ====================


@pytest.mark.asyncio
async def test_create_quiz_success(async_client: AsyncClient, sample_quiz_data):
    """퀴즈 생성 성공"""
    response = await async_client.post("/api/quiz/create", json=sample_quiz_data)

    assert response.status_code == 200
    data = response.json()

    assert data["quiz_id"] == "quiz_001"
    assert data["session_id"] == "session_001"
    assert data["question"] == "What is 2 + 2?"
    assert len(data["options"]) == 4
    assert data["correct_option_id"] == "opt_b"
    assert data["status"] == "draft"
    assert data["published"] is False


@pytest.mark.asyncio
async def test_create_quiz_duplicate_id(async_client: AsyncClient, sample_quiz_data):
    """중복된 quiz_id로 생성 시도"""
    # 첫 번째 퀴즈 생성
    await async_client.post("/api/quiz/create", json=sample_quiz_data)

    # 같은 ID로 다시 생성 시도
    response = await async_client.post("/api/quiz/create", json=sample_quiz_data)

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_quiz_missing_required_fields(async_client: AsyncClient):
    """필수 필드 누락"""
    invalid_data = {
        "quiz_id": "quiz_002",
        "question": "What is 3 + 3?",
        # session_id, options, correct_option_id 누락
    }

    response = await async_client.post("/api/quiz/create", json=invalid_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_quiz_invalid_correct_option(async_client: AsyncClient):
    """잘못된 correct_option_id"""
    invalid_data = {
        "quiz_id": "quiz_003",
        "session_id": "session_001",
        "question": "Test question?",
        "options": [
            {"id": "opt_a", "text": "A"},
            {"id": "opt_b", "text": "B"},
        ],
        "correct_option_id": "opt_z",  # 존재하지 않는 옵션
        "topic": "Test",
        "difficulty": 1,
    }

    response = await async_client.post("/api/quiz/create", json=invalid_data)

    assert response.status_code == 400
    assert "correct_option_id must match" in response.json()["detail"]


# ==================== Quiz Publish Tests ====================


@pytest.mark.asyncio
async def test_publish_quiz_success(async_client: AsyncClient, sample_quiz_data):
    """퀴즈 발행 성공"""
    # 퀴즈 생성
    await async_client.post("/api/quiz/create", json=sample_quiz_data)

    # 발행
    response = await async_client.post(
        "/api/quiz/publish", params={"quiz_id": "quiz_001"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["quiz_id"] == "quiz_001"
    assert data["status"] == "active"
    assert data["published"] is True
    assert "published_at" in data


@pytest.mark.asyncio
async def test_publish_nonexistent_quiz(async_client: AsyncClient):
    """존재하지 않는 퀴즈 발행 시도"""
    response = await async_client.post(
        "/api/quiz/publish", params={"quiz_id": "nonexistent"}
    )

    assert response.status_code == 404
    assert "Quiz not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_publish_already_published_quiz(
    async_client: AsyncClient, sample_quiz_data
):
    """이미 발행된 퀴즈 재발행"""
    # 생성 및 발행
    await async_client.post("/api/quiz/create", json=sample_quiz_data)
    await async_client.post("/api/quiz/publish", params={"quiz_id": "quiz_001"})

    # 재발행 시도
    response = await async_client.post(
        "/api/quiz/publish", params={"quiz_id": "quiz_001"}
    )

    # 이미 발행된 상태여도 성공 (멱등성)
    assert response.status_code == 200


# ==================== Quiz Response Tests ====================


@pytest.mark.asyncio
async def test_submit_quiz_response_success(
    async_client: AsyncClient, sample_quiz_data
):
    """학생 응답 제출 성공"""
    # 퀴즈 생성 및 발행
    await async_client.post("/api/quiz/create", json=sample_quiz_data)
    await async_client.post("/api/quiz/publish", params={"quiz_id": "quiz_001"})

    # 학생 응답 제출
    response_data = {
        "quiz_id": "quiz_001",
        "student_id": "student_001",
        "selected_option_id": "opt_b",
        "response_time": 5.2,
    }

    response = await async_client.post("/api/quiz/response", json=response_data)

    assert response.status_code == 200
    data = response.json()

    assert data["quiz_id"] == "quiz_001"
    assert data["student_id"] == "student_001"
    assert data["selected_option_id"] == "opt_b"
    assert data["is_correct"] is True  # opt_b가 정답
    assert data["response_time"] == 5.2


@pytest.mark.asyncio
async def test_submit_incorrect_response(async_client: AsyncClient, sample_quiz_data):
    """오답 제출"""
    await async_client.post("/api/quiz/create", json=sample_quiz_data)
    await async_client.post("/api/quiz/publish", params={"quiz_id": "quiz_001"})

    response_data = {
        "quiz_id": "quiz_001",
        "student_id": "student_002",
        "selected_option_id": "opt_a",  # 오답
        "response_time": 3.5,
    }

    response = await async_client.post("/api/quiz/response", json=response_data)

    assert response.status_code == 200
    data = response.json()

    assert data["is_correct"] is False


@pytest.mark.asyncio
async def test_submit_response_to_unpublished_quiz(
    async_client: AsyncClient, sample_quiz_data
):
    """발행되지 않은 퀴즈에 응답 시도"""
    await async_client.post("/api/quiz/create", json=sample_quiz_data)
    # 발행하지 않음

    response_data = {
        "quiz_id": "quiz_001",
        "student_id": "student_003",
        "selected_option_id": "opt_b",
        "response_time": 2.0,
    }

    response = await async_client.post("/api/quiz/response", json=response_data)

    assert response.status_code == 400
    assert "not published" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_duplicate_response(async_client: AsyncClient, sample_quiz_data):
    """동일 학생의 중복 응답"""
    await async_client.post("/api/quiz/create", json=sample_quiz_data)
    await async_client.post("/api/quiz/publish", params={"quiz_id": "quiz_001"})

    response_data = {
        "quiz_id": "quiz_001",
        "student_id": "student_004",
        "selected_option_id": "opt_b",
        "response_time": 4.0,
    }

    # 첫 번째 응답
    await async_client.post("/api/quiz/response", json=response_data)

    # 두 번째 응답 (덮어쓰기)
    response_data["selected_option_id"] = "opt_c"
    response = await async_client.post("/api/quiz/response", json=response_data)

    # 덮어쓰기 성공 (최신 응답으로 업데이트)
    assert response.status_code == 200


# ==================== Quiz Retrieval Tests ====================


@pytest.mark.asyncio
async def test_get_quiz_success(async_client: AsyncClient, sample_quiz_data):
    """퀴즈 조회 성공"""
    await async_client.post("/api/quiz/create", json=sample_quiz_data)

    response = await async_client.get("/api/quiz/quiz_001")

    assert response.status_code == 200
    data = response.json()

    assert data["quiz_id"] == "quiz_001"
    assert data["question"] == "What is 2 + 2?"


@pytest.mark.asyncio
async def test_get_nonexistent_quiz(async_client: AsyncClient):
    """존재하지 않는 퀴즈 조회"""
    response = await async_client.get("/api/quiz/nonexistent")

    assert response.status_code == 404


# ==================== Quiz Statistics Tests ====================


@pytest.mark.asyncio
async def test_get_quiz_stats_with_responses(
    async_client: AsyncClient, sample_quiz_data
):
    """응답이 있는 퀴즈 통계 조회"""
    # 퀴즈 생성 및 발행
    await async_client.post("/api/quiz/create", json=sample_quiz_data)
    await async_client.post("/api/quiz/publish", params={"quiz_id": "quiz_001"})

    # 여러 학생 응답 제출
    responses = [
        {
            "student_id": "student_1",
            "selected_option_id": "opt_b",
            "response_time": 3.0,
        },  # 정답
        {
            "student_id": "student_2",
            "selected_option_id": "opt_b",
            "response_time": 4.0,
        },  # 정답
        {
            "student_id": "student_3",
            "selected_option_id": "opt_a",
            "response_time": 2.5,
        },  # 오답
        {
            "student_id": "student_4",
            "selected_option_id": "opt_c",
            "response_time": 5.0,
        },  # 오답
    ]

    for resp in responses:
        await async_client.post(
            "/api/quiz/response",
            json={
                "quiz_id": "quiz_001",
                **resp,
            },
        )

    # 통계 조회
    response = await async_client.get("/api/quiz/quiz_001/stats")

    assert response.status_code == 200
    data = response.json()

    assert data["quiz_id"] == "quiz_001"
    assert data["total_responses"] == 4
    assert data["correct_responses"] == 2
    assert data["accuracy"] == 50.0  # 2/4 = 50%
    assert "option_distribution" in data
    assert data["option_distribution"]["opt_b"] == 2
    assert data["option_distribution"]["opt_a"] == 1


@pytest.mark.asyncio
async def test_get_quiz_stats_no_responses(async_client: AsyncClient, sample_quiz_data):
    """응답이 없는 퀴즈 통계"""
    await async_client.post("/api/quiz/create", json=sample_quiz_data)
    await async_client.post("/api/quiz/publish", params={"quiz_id": "quiz_001"})

    response = await async_client.get("/api/quiz/quiz_001/stats")

    assert response.status_code == 200
    data = response.json()

    assert data["total_responses"] == 0
    assert data["correct_responses"] == 0
    assert data["accuracy"] == 0.0


# ==================== Quiz Deletion Tests ====================


@pytest.mark.asyncio
async def test_delete_quiz_success(async_client: AsyncClient, sample_quiz_data):
    """퀴즈 삭제 성공"""
    await async_client.post("/api/quiz/create", json=sample_quiz_data)

    response = await async_client.delete("/api/quiz/quiz_001")

    assert response.status_code == 200

    # 삭제 후 조회 시 404
    get_response = await async_client.get("/api/quiz/quiz_001")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_quiz(async_client: AsyncClient):
    """존재하지 않는 퀴즈 삭제"""
    response = await async_client.delete("/api/quiz/nonexistent")

    assert response.status_code == 404


# ==================== Session Quizzes Tests ====================


@pytest.mark.asyncio
async def test_get_session_quizzes(async_client: AsyncClient):
    """세션의 모든 퀴즈 조회"""
    # 같은 세션에 여러 퀴즈 생성
    quiz1 = {
        "quiz_id": "quiz_s1_001",
        "session_id": "session_100",
        "question": "Question 1?",
        "options": [{"id": "opt_a", "text": "A"}, {"id": "opt_b", "text": "B"}],
        "correct_option_id": "opt_a",
        "topic": "Test",
        "difficulty": 1,
    }

    quiz2 = {
        "quiz_id": "quiz_s1_002",
        "session_id": "session_100",
        "question": "Question 2?",
        "options": [{"id": "opt_a", "text": "A"}, {"id": "opt_b", "text": "B"}],
        "correct_option_id": "opt_b",
        "topic": "Test",
        "difficulty": 2,
    }

    await async_client.post("/api/quiz/create", json=quiz1)
    await async_client.post("/api/quiz/create", json=quiz2)

    # 세션 퀴즈 목록 조회
    response = await async_client.get("/api/quiz/session/session_100")

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert data[0]["quiz_id"] == "quiz_s1_001"
    assert data[1]["quiz_id"] == "quiz_s1_002"
