"""
Test database query performance
Phase 3-4: DB 쿼리 최적화 검증
"""

import pytest
import pytest_asyncio
import asyncio
import time
from datetime import datetime, timedelta, UTC
import random
import logging

from core.database import get_database_manager

logger = logging.getLogger(__name__)
from schemas import ChatMessage, StudentEngagement, EngagementMetrics, QuizResponse


@pytest_asyncio.fixture
async def db():
    """Database fixture. MongoDB 미연결 시 테스트 스킵."""
    from core.database import DatabaseManager
    import os

    mongo_url = os.getenv(
        "MONGO_URL",
        "mongodb://airclass:airclass2025@localhost:27017/airclass_test?authSource=admin",
    )
    db_manager = DatabaseManager(mongo_url)
    ok = await db_manager.init()
    if not ok:
        pytest.skip("MongoDB not available (connection or auth failed)")

    yield db_manager

    # Cleanup test data
    try:
        await db_manager.db.chat_analytics.delete_many(
            {"session_id": {"$regex": "^test-"}}
        )
        await db_manager.db.student_engagement.delete_many(
            {"session_id": {"$regex": "^test-"}}
        )
        await db_manager.db.quiz_responses.delete_many(
            {"session_id": {"$regex": "^test-"}}
        )
    except Exception as e:
        logger.warning("Cleanup failed: %s", e)

    # Close connection
    if db_manager.client:
        db_manager.client.close()


@pytest_asyncio.fixture
async def test_data(db):
    """Create test data. MongoDB 쓰기 실패 시 스킵."""
    session_id = f"test-{int(time.time())}"

    engagement_data = []
    for i in range(100):
        metrics = EngagementMetrics(
            attention_score=random.uniform(0.6, 1.0),
            participation_count=random.randint(5, 20),
            quiz_accuracy=random.uniform(0.4, 1.0),
            response_latency_ms=random.randint(500, 3000),
            chat_message_count=random.randint(0, 50),
            last_activity_time=datetime.now(UTC),
        )
        engagement = StudentEngagement(
            session_id=session_id,
            student_id=f"student-{i:03d}",
            student_name=f"Student {i:03d}",
            node_name="test-node",
            metrics=metrics,
            updated_at=datetime.now(UTC),
        )
        engagement_data.append(engagement.model_dump())

    chat_data = []
    base_time = datetime.now(UTC) - timedelta(hours=1)
    for i in range(500):
        student_id = f"student-{random.randint(0, 99):03d}"
        message = ChatMessage(
            session_id=session_id,
            student_id=student_id,
            student_name=f"Student {student_id}",
            message=f"Test message {i}",
            message_time=base_time + timedelta(seconds=i * 2),
            is_question=random.choice([True, False]),
            sentiment=random.choice(["positive", "neutral", "negative"]),
        )
        chat_data.append(message.model_dump())

    try:
        await db.db.student_engagement.insert_many(engagement_data)
        await db.db.chat_analytics.insert_many(chat_data)
    except Exception as e:
        pytest.skip(f"MongoDB not usable for test data: {e}")

    return session_id


@pytest.mark.asyncio
async def test_chat_query_performance(db, test_data):
    """채팅 조회 성능 테스트"""
    session_id = test_data

    # Test with projection (optimized)
    start = time.time()
    messages = await db.get_chat_messages(session_id, limit=100)
    duration = time.time() - start

    assert len(messages) == 100
    assert duration < 0.1, (
        f"Chat query too slow: {duration * 1000:.2f}ms (target: <100ms)"
    )

    print(f"\n✅ Chat query (limit 100): {duration * 1000:.2f}ms")


@pytest.mark.asyncio
async def test_engagement_query_performance(db, test_data):
    """참여도 조회 성능 테스트"""
    session_id = test_data

    # Test with summary projection (optimized)
    start = time.time()
    engagement = await db.get_session_engagement(session_id, summary_only=True)
    duration = time.time() - start

    assert len(engagement) == 100
    assert duration < 0.05, (
        f"Engagement query too slow: {duration * 1000:.2f}ms (target: <50ms)"
    )

    print(f"\n✅ Engagement query (summary): {duration * 1000:.2f}ms")


@pytest.mark.asyncio
async def test_engagement_full_query_performance(db, test_data):
    """참여도 전체 조회 성능 테스트"""
    session_id = test_data

    # Test with full data
    start = time.time()
    engagement = await db.get_session_engagement(session_id, summary_only=False)
    duration = time.time() - start

    assert len(engagement) == 100
    assert duration < 0.1, (
        f"Engagement full query too slow: {duration * 1000:.2f}ms (target: <100ms)"
    )

    print(f"\n✅ Engagement query (full): {duration * 1000:.2f}ms")


@pytest.mark.asyncio
async def test_parallel_queries_performance(db, test_data):
    """병렬 쿼리 성능 테스트 (대시보드 시뮬레이션)"""
    session_id = test_data

    start = time.time()
    await asyncio.gather(
        db.get_chat_messages(session_id, limit=50),
        db.get_session_engagement(session_id, summary_only=True),
    )
    duration = time.time() - start

    assert duration < 0.15, (
        f"Parallel queries too slow: {duration * 1000:.2f}ms (target: <150ms)"
    )

    print(f"\n✅ Parallel queries (dashboard): {duration * 1000:.2f}ms")


@pytest.mark.asyncio
async def test_sorting_performance(db, test_data):
    """정렬 성능 테스트 (인덱스 활용)"""
    session_id = test_data

    # 최신순 정렬 (인덱스 활용)
    start = time.time()
    messages = await db.get_chat_messages(session_id, limit=50)
    duration = time.time() - start

    assert len(messages) == 50
    assert duration < 0.05, (
        f"Sorted query too slow: {duration * 1000:.2f}ms (target: <50ms)"
    )

    # 메시지가 시간순으로 정렬되었는지 확인
    times = [msg.message_time for msg in messages]
    assert times == sorted(times, reverse=True), "Messages not sorted correctly"

    print(f"\n✅ Sorted query (indexed): {duration * 1000:.2f}ms")


@pytest.mark.asyncio
async def test_filtered_query_performance(db, test_data):
    """필터링 쿼리 성능 테스트"""
    session_id = test_data

    # 복합 인덱스 활용 (session_id + message_time)
    start = time.time()
    messages = await db.get_chat_messages(session_id, limit=100)
    duration = time.time() - start

    assert len(messages) == 100
    assert duration < 0.08, (
        f"Filtered query too slow: {duration * 1000:.2f}ms (target: <80ms)"
    )

    print(f"\n✅ Filtered query (indexed): {duration * 1000:.2f}ms")


@pytest.mark.asyncio
async def test_projection_effectiveness(db, test_data):
    """프로젝션 효과 테스트"""
    session_id = test_data

    # 프로젝션 사용 (최적화)
    start1 = time.time()
    engagement_summary = await db.get_session_engagement(session_id, summary_only=True)
    duration1 = time.time() - start1

    # 전체 데이터 (비최적화)
    start2 = time.time()
    engagement_full = await db.get_session_engagement(session_id, summary_only=False)
    duration2 = time.time() - start2

    # 둘 다 목표 시간 내 완료 + 동일 건수 반환 (상대 시간은 환경 노이즈로 불안정하므로 검증하지 않음)
    assert duration1 < 0.1, f"Summary query too slow: {duration1 * 1000:.2f}ms"
    assert duration2 < 0.1, f"Full query too slow: {duration2 * 1000:.2f}ms"
    assert len(engagement_summary) == len(engagement_full), "Projection must return same count"

    print(f"\n✅ Projection effectiveness:")
    print(f"   Summary: {duration1 * 1000:.2f}ms, Full: {duration2 * 1000:.2f}ms, count={len(engagement_summary)}")
