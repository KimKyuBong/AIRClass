"""
AIRClass Quiz API Endpoints
퀴즈 배포, 응답 수집, 통계
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket
from typing import List, Optional, Dict
import logging
from schemas import *
from core.database import get_database_manager
from core.messaging import get_messaging_system
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
        # 중복 체크
        existing = await db.get_quiz(request.quiz_id)
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Quiz {request.quiz_id} already exists"
            )

        # correct_option_id 검증
        option_ids = [opt.id for opt in request.options]
        if request.correct_option_id not in option_ids:
            raise HTTPException(
                status_code=400,
                detail="correct_option_id must match one of the option IDs",
            )

        quiz = await db.create_quiz(request)
        logger.info(f"✅ Quiz created: {request.quiz_id}")
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}", response_model=Quiz)
async def get_quiz(quiz_id: str):
    """
    퀴즈 조회
    """
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        quiz = await db.get_quiz(quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return quiz
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{quiz_id}")
async def delete_quiz(quiz_id: str):
    """
    퀴즈 삭제
    """
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        deleted = await db.delete_quiz(quiz_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Quiz not found")

        logger.info(f"✅ Quiz deleted: {quiz_id}")
        return {"status": "deleted", "quiz_id": quiz_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}", response_model=List[Quiz])
async def get_session_quizzes(session_id: str):
    """
    세션의 모든 퀴즈 조회
    """
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        quizzes = await db.get_session_quizzes(session_id)
        return quizzes
    except Exception as e:
        logger.error(f"❌ Failed to get session quizzes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish", response_model=Quiz)
async def publish_quiz(quiz_id: str):
    """
    교사: 퀴즈 발행 (query parameter로 quiz_id 전달)
    """
    db = get_database_manager()
    messaging = get_messaging_system()

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # 퀴즈 존재 확인
        quiz = await db.get_quiz(quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        # 퀴즈 발행 표시
        await db.publish_quiz(quiz_id)

        # 발행된 퀴즈 반환
        published_quiz = await db.get_quiz(quiz_id)

        # Redis로 모든 학생에게 브로드캐스트 (messaging이 있으면)
        if messaging:
            try:
                await messaging.publish_quiz_event(
                    session_id=quiz.session_id,
                    quiz_id=quiz_id,
                    event_type="published",
                    data={
                        "question": quiz.question,
                        "options": [
                            {"id": opt.id, "text": opt.text} for opt in quiz.options
                        ],
                        "difficulty": quiz.difficulty,
                    },
                )
            except Exception as msg_error:
                logger.warning(f"⚠️ Failed to publish quiz event: {msg_error}")

        # WebSocket으로 학생들에게 직접 브로드캐스트
        try:
            from utils import get_connection_manager

            manager = get_connection_manager()
            await manager.broadcast_quiz(
                {
                    "quiz_id": quiz_id,
                    "session_id": quiz.session_id,
                    "question": quiz.question,
                    "options": [opt.text for opt in quiz.options],
                    "time_limit": 60,  # 기본값
                }
            )
        except Exception as ws_error:
            logger.warning(f"⚠️ Failed to broadcast quiz via WebSocket: {ws_error}")

        logger.info(f"✅ Quiz published: {quiz_id}")
        return published_quiz

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to publish quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/response", response_model=QuizResponse)
async def submit_quiz_response(request: QuizResponseCreate):
    """
    학생: 퀴즈 응답 제출
    """
    db = get_database_manager()
    messaging = get_messaging_system()

    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # 퀴즈가 발행되었는지 확인
        quiz = await db.get_quiz(request.quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        if not quiz.published:
            raise HTTPException(status_code=400, detail="Quiz is not published yet")

        # 응답 저장
        response = await db.create_quiz_response(request)

        # 참여도 업데이트 (messaging이 있으면)
        if messaging:
            try:
                await messaging.publish_engagement_event(
                    session_id=quiz.session_id,
                    student_id=request.student_id,
                    activity_type="quiz_response",
                    data={
                        "quiz_id": request.quiz_id,
                        "is_correct": response.is_correct,
                        "response_time": request.response_time,
                    },
                )
            except Exception as msg_error:
                logger.warning(f"⚠️ Failed to publish engagement event: {msg_error}")

        logger.info(
            f"✅ Quiz response submitted: {request.student_id} -> {request.quiz_id}"
        )

        return response

    except HTTPException:
        raise
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


@router.get("/{quiz_id}/stats", response_model=Dict)
async def get_quiz_statistics(quiz_id: str):
    """
    교사/모니터: 퀴즈 통계 조회
    """
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        stats = await db.get_quiz_stats(quiz_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Quiz not found")

        return stats

    except HTTPException:
        raise
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
                await websocket.send_json(
                    {
                        "type": "stats_update",
                        "data": stats,
                    }
                )

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
