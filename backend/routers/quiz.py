"""
AIRClass Quiz API Endpoints
퀴즈 배포, 응답 수집, 통계
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket
from typing import List, Optional
import logging
from models import *
from database import get_database_manager
from messaging import get_messaging_system
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.post("/create", response_model=Quiz)
async def create_quiz(request: QuizCreate):
    """
    교사: 퀴즈 생성
    """
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        quiz = await db.create_quiz(request)
        logger.info(f"✅ Quiz created: {request.quiz_id}")
        return quiz
    except Exception as e:
        logger.error(f"❌ Failed to create quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish")
async def publish_quiz(request: QuizPublishRequest):
    """
    교사: 퀴즈 발행 (학생들에게 푸시)
    """
    db = get_database_manager()
    messaging = get_messaging_system()

    if not db or not messaging:
        raise HTTPException(status_code=503, detail="Services not available")

    try:
        # 퀴즈 발행 표시
        await db.publish_quiz(request.quiz.quiz_id)

        # Redis로 모든 학생에게 브로드캐스트
        await messaging.publish_quiz_event(
            session_id=request.quiz.session_id,
            quiz_id=request.quiz.quiz_id,
            event_type="published",
            data={
                "question": request.quiz.question,
                "options": [{"id": opt.id, "text": opt.text} for opt in request.quiz.options],
                "difficulty": request.quiz.difficulty,
            },
        )

        logger.info(f"✅ Quiz published: {request.quiz.quiz_id}")
        return {"status": "published", "quiz_id": request.quiz.quiz_id}

    except Exception as e:
        logger.error(f"❌ Failed to publish quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/response", response_model=Dict)
async def submit_quiz_response(request: QuizResponseRequest):
    """
    학생: 퀴즈 응답 제출
    """
    db = get_database_manager()
    messaging = get_messaging_system()

    if not db or not messaging:
        raise HTTPException(status_code=503, detail="Services not available")

    try:
        # 응답 저장
        response = await db.create_quiz_response(request)

        # 참여도 업데이트
        await messaging.publish_engagement_event(
            session_id=request.session_id,
            student_id=request.student_id,
            activity_type="quiz_response",
            data={
                "quiz_id": request.quiz_id,
                "is_correct": response.is_correct,
                "response_time_ms": request.response_time_ms,
            },
        )

        logger.info(f"✅ Quiz response submitted: {request.student_id} -> {request.quiz_id}")

        return {
            "status": "submitted",
            "is_correct": response.is_correct,
            "response_time_ms": response.response_time_ms,
        }

    except Exception as e:
        logger.error(f"❌ Failed to submit response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/responses/{quiz_id}", response_model=List[QuizResponse])
async def get_quiz_responses(quiz_id: str):
    """
    교사: 퀴즈 응답 목록 조회
    """
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        responses = await db.get_quiz_responses(quiz_id)
        return responses
    except Exception as e:
        logger.error(f"❌ Failed to get responses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/{quiz_id}", response_model=Dict)
async def get_quiz_statistics(quiz_id: str):
    """
    교사/모니터: 퀴즈 통계 조회
    """
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        quiz = await db.get_quiz(quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        responses = await db.get_quiz_responses(quiz_id)

        total_responses = len(responses)
        correct_responses = sum(1 for r in responses if r.is_correct)
        accuracy_rate = (correct_responses / total_responses * 100) if total_responses > 0 else 0
        avg_response_time = (
            sum(r.response_time_ms for r in responses) / total_responses
            if total_responses > 0
            else 0
        )

        return {
            "quiz_id": quiz_id,
            "total_responses": total_responses,
            "correct_responses": correct_responses,
            "accuracy_rate": f"{accuracy_rate:.1f}%",
            "average_response_time_ms": int(avg_response_time),
            "difficulty": quiz.difficulty,
            "topic": quiz.topic,
        }

    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket: 실시간 퀴즈 통계 스트리밍
@router.websocket("/ws/statistics/{quiz_id}")
async def websocket_quiz_statistics(websocket: WebSocket, quiz_id: str):
    """
    교사/모니터: 실시간 퀴즈 통계 스트림
    """
    messaging = get_messaging_system()
    if not messaging:
        await websocket.close(code=4503, reason="Service not available")
        return

    await websocket.accept()

    try:
        # 퀴즈 응답 이벤트 콜백
        async def on_quiz_response(event):
            if event.get("quiz_id") == quiz_id:
                # 최신 통계 전송
                stats = await get_quiz_statistics(quiz_id)
                await websocket.send_json({
                    "type": "stats_update",
                    "data": stats,
                })

        # 콜백 등록
        await messaging.register_callback("quiz_response", on_quiz_response)

        # WebSocket 유지
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await websocket.close(code=4000, reason=str(e))
