"""
AIRClass Engagement Tracking API
학생 참여도 추적 및 조회 엔드포인트
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from datetime import datetime, UTC

from schemas import ActivityType, StudentEngagement, EngagementMetrics
from services.engagement_service import get_engagement_tracker, EngagementCalculator
from core.database import get_database_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/engagement", tags=["engagement"])


# ============================================
# Dependencies
# ============================================


def get_tracker():
    """EngagementTracker 의존성"""
    tracker = get_engagement_tracker()
    if not tracker:
        raise HTTPException(
            status_code=503, detail="Engagement tracker not initialized"
        )
    return tracker


def get_db():
    """DatabaseManager 의존성"""
    db = get_database_manager()
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return db


def _is_service_unavailable(exc: Exception) -> bool:
    """DB/연결·이벤트 루프 등 서비스 이용 불가 상태면 True"""
    msg = str(exc).lower()
    return (
        "event loop" in msg
        or "connection" in msg
        or "closed" in msg
        or "not initialized" in msg
    )


# ============================================
# Activity Tracking Endpoints
# ============================================


@router.post("/track/chat")
async def track_chat_activity(
    session_id: str,
    student_id: str,
    student_name: str,
    node_name: str,
    tracker=Depends(get_tracker),
):
    """
    채팅 활동 기록

    Args:
        session_id: 세션 ID
        student_id: 학생 ID
        student_name: 학생 이름
        node_name: 노드 이름

    Returns:
        {success: bool, engagement: StudentEngagement}
    """
    try:
        engagement = await tracker.track_activity(
            session_id=session_id,
            student_id=student_id,
            student_name=student_name,
            node_name=node_name,
            activity_type=ActivityType.CHAT,
            activity_data={},
        )

        if not engagement:
            raise HTTPException(status_code=500, detail="Failed to track chat activity")

        # WebSocket으로 참여도 업데이트 브로드캐스트
        try:
            from utils import get_connection_manager

            manager = get_connection_manager()
            await manager.broadcast_engagement_update(
                {
                    "session_id": session_id,
                    "student_id": student_id,
                    "student_name": student_name,
                    "engagement_score": engagement.engagement_score,
                    "attention_score": engagement.attention_score,
                    "participation_score": engagement.participation_score,
                    "quiz_accuracy": engagement.quiz_accuracy,
                }
            )
        except Exception as ws_error:
            logger.warning(
                f"⚠️ Failed to broadcast engagement via WebSocket: {ws_error}"
            )

        return {
            "success": True,
            "engagement": engagement.model_dump(),
        }

    except Exception as e:
        logger.error(f"❌ Error tracking chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track/quiz-response")
async def track_quiz_response(
    session_id: str,
    student_id: str,
    student_name: str,
    node_name: str,
    response_time_ms: int,
    is_correct: bool,
    tracker=Depends(get_tracker),
):
    """
    퀴즈 응답 기록

    Args:
        session_id: 세션 ID
        student_id: 학생 ID
        student_name: 학생 이름
        node_name: 노드 이름
        response_time_ms: 응답 시간 (밀리초)
        is_correct: 정답 여부

    Returns:
        {success: bool, engagement: StudentEngagement}
    """
    try:
        engagement = await tracker.track_activity(
            session_id=session_id,
            student_id=student_id,
            student_name=student_name,
            node_name=node_name,
            activity_type=ActivityType.QUIZ_RESPONSE,
            activity_data={
                "response_time_ms": response_time_ms,
                "is_correct": is_correct,
            },
        )

        if not engagement:
            raise HTTPException(status_code=500, detail="Failed to track quiz response")

        # WebSocket으로 참여도 업데이트 브로드캐스트
        try:
            from utils import get_connection_manager

            manager = get_connection_manager()
            await manager.broadcast_engagement_update(
                {
                    "session_id": session_id,
                    "student_id": student_id,
                    "student_name": student_name,
                    "engagement_score": engagement.engagement_score,
                    "attention_score": engagement.attention_score,
                    "participation_score": engagement.participation_score,
                    "quiz_accuracy": engagement.quiz_accuracy,
                }
            )
        except Exception as ws_error:
            logger.warning(
                f"⚠️ Failed to broadcast engagement via WebSocket: {ws_error}"
            )

        return {
            "success": True,
            "engagement": engagement.model_dump(),
        }

    except Exception as e:
        logger.error(f"❌ Error tracking quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Engagement Metrics Endpoints
# ============================================


@router.get("/students/{session_id}")
async def get_session_engagement(
    session_id: str,
    db=Depends(get_db),
):
    """
    세션의 모든 학생 참여도 조회

    Args:
        session_id: 세션 ID

    Returns:
        List[StudentEngagement]: 학생별 참여도 목록
    """
    try:
        engagements = await db.get_session_engagement(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "total_students": len(engagements),
            "engagements": [eng.model_dump() for eng in engagements],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting session engagement: {e}")
        # DB/연결·루프 오류는 503 (서비스 이용 불가)
        if _is_service_unavailable(e):
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/student/{session_id}/{student_id}")
async def get_student_engagement(
    session_id: str,
    student_id: str,
    db=Depends(get_db),
):
    """
    특정 학생의 참여도 조회

    Args:
        session_id: 세션 ID
        student_id: 학생 ID

    Returns:
        StudentEngagement: 학생 참여도
    """
    try:
        engagements = await db.get_session_engagement(session_id)
        engagement = None
        for eng in engagements:
            if eng.student_id == student_id:
                engagement = eng
                break

        if not engagement:
            raise HTTPException(status_code=404, detail="Student engagement not found")

        return {
            "success": True,
            "engagement": engagement.model_dump(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting student engagement: {e}")
        if _is_service_unavailable(e):
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session-stats/{session_id}")
async def get_session_stats(
    session_id: str,
    session_duration_minutes: float = Query(50.0, description="세션 진행 시간 (분)"),
    tracker=Depends(get_tracker),
):
    """
    세션 전체 참여도 통계

    Args:
        session_id: 세션 ID
        session_duration_minutes: 세션 진행 시간

    Returns:
        Dict: 세션별 참여도 통계 (평균, 범위, 레벨별 분포)
    """
    try:
        stats = await tracker.calculate_session_engagement(
            session_id=session_id,
            session_duration_minutes=session_duration_minutes,
        )

        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "success": True,
            "stats": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error calculating session stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Engagement Calculation Endpoints
# ============================================


@router.post("/calculate/attention-score")
async def calculate_attention_score(
    quiz_participation_rate: float,
    avg_response_latency_ms: int,
    screen_time_minutes: float,
    max_possible_time: float = 50.0,
):
    """
    주의집중도 점수 계산 (0-1)

    Args:
        quiz_participation_rate: 퀴즈 응답률 (0-1)
        avg_response_latency_ms: 평균 응답 시간 (밀리초)
        screen_time_minutes: 총 시청 시간 (분)
        max_possible_time: 최대 가능 시간 (분, 기본 50분)

    Returns:
        {attention_score: float}
    """
    try:
        calculator = EngagementCalculator()
        score = calculator.calculate_attention_score(
            quiz_participation_rate=quiz_participation_rate,
            avg_response_latency_ms=avg_response_latency_ms,
            screen_time_minutes=screen_time_minutes,
            max_possible_time=max_possible_time,
        )

        return {
            "success": True,
            "attention_score": score,
            "interpretation": EngagementCalculator.interpret_engagement_level(
                score * 100
            ),
        }

    except Exception as e:
        logger.error(f"❌ Error calculating attention score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/participation-score")
async def calculate_participation_score(
    chat_message_count: int,
    quiz_response_count: int,
    session_duration_minutes: float,
):
    """
    참여 점수 계산 (0-100)

    Args:
        chat_message_count: 채팅 메시지 수
        quiz_response_count: 퀴즈 응답 수
        session_duration_minutes: 세션 참석 시간

    Returns:
        {participation_score: int}
    """
    try:
        calculator = EngagementCalculator()
        score = calculator.calculate_participation_score(
            chat_message_count=chat_message_count,
            quiz_response_count=quiz_response_count,
            session_duration_minutes=session_duration_minutes,
        )

        return {
            "success": True,
            "participation_score": score,
            "interpretation": EngagementCalculator.interpret_engagement_level(score),
        }

    except Exception as e:
        logger.error(f"❌ Error calculating participation score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/quiz-accuracy")
async def calculate_quiz_accuracy(
    correct_responses: int,
    total_responses: int,
):
    """
    정답률 계산 (0-1)

    Args:
        correct_responses: 정답 개수
        total_responses: 총 응답 개수

    Returns:
        {quiz_accuracy: float}
    """
    try:
        calculator = EngagementCalculator()
        accuracy = calculator.calculate_quiz_accuracy(
            correct_responses=correct_responses,
            total_responses=total_responses,
        )

        return {
            "success": True,
            "quiz_accuracy": accuracy,
            "percentage": accuracy * 100,
        }

    except Exception as e:
        logger.error(f"❌ Error calculating quiz accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate/overall-score")
async def calculate_overall_engagement_score(
    attention_score: float,
    participation_score: int,
    quiz_accuracy: float,
):
    """
    총 참여도 점수 계산 (0-100)

    가중평균:
    - Attention Score (40%)
    - Participation Score (40%)
    - Quiz Accuracy (20%)

    Args:
        attention_score: 주의집중도 (0-1)
        participation_score: 참여 점수 (0-100)
        quiz_accuracy: 정답률 (0-1)

    Returns:
        {overall_score: float, level: str, recommendations: List[str]}
    """
    try:
        calculator = EngagementCalculator()
        score = calculator.calculate_overall_engagement_score(
            attention_score=attention_score,
            participation_score=participation_score,
            quiz_accuracy=quiz_accuracy,
        )

        interpretation = calculator.interpret_engagement_level(score)

        return {
            "success": True,
            "overall_score": score,
            "level": interpretation["level"],
            "description": interpretation["description"],
            "color": interpretation["color"],
            "recommendations": interpretation["recommendations"],
        }

    except Exception as e:
        logger.error(f"❌ Error calculating overall score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Confusion Detection Endpoint
# ============================================


@router.post("/detect-confusion")
async def detect_confusion(
    quiz_accuracy: float,
    chat_activity_high: bool,
    confusion_indicators: Optional[List[str]] = None,
):
    """
    혼동도 감지

    혼동 지표:
    1. 낮은 정답률 (< 50%) + 높은 채팅 활동
    2. 반복되는 같은 질문 패턴
    3. 분명한 실수 패턴

    Args:
        quiz_accuracy: 정답률 (0-1)
        chat_activity_high: 채팅 활동 많음 여부
        confusion_indicators: 혼동 지표 리스트 (선택사항)

    Returns:
        {is_confused: bool, confidence: float, recommendations: List[str]}
    """
    try:
        calculator = EngagementCalculator()
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=quiz_accuracy,
            chat_activity_high=chat_activity_high,
            confusion_indicators=confusion_indicators or [],
        )

        recommendations = []
        if is_confused:
            if quiz_accuracy < 0.3:
                recommendations.append("개념 재설명 필요")
                recommendations.append("예제 추가 제시")
            if chat_activity_high:
                recommendations.append("질문 양식 정리")
                recommendations.append("일대일 확인 권장")
            recommendations.append("진도 속도 조절 고려")

        return {
            "success": True,
            "is_confused": is_confused,
            "confidence": confidence,
            "quiz_accuracy": quiz_accuracy,
            "chat_activity": "high" if chat_activity_high else "low",
            "indicators_count": len(confusion_indicators or []),
            "recommendations": recommendations,
        }

    except Exception as e:
        logger.error(f"❌ Error detecting confusion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Engagement Trend Endpoint
# ============================================


@router.post("/analyze-trend")
async def analyze_trend(
    recent_scores: List[float] = Body(..., embed=True),
    window_minutes: int = Body(10, embed=True),
):
    """
    참여도 추세 분석

    Args:
        recent_scores: 최근 참여도 점수들 (시간순)
        window_minutes: 분석 윈도우

    Returns:
        Dict: trend_direction, trend_strength, average 등
    """
    try:
        if not recent_scores:
            raise ValueError("recent_scores cannot be empty")

        calculator = EngagementCalculator()
        trend = calculator.analyze_trend(
            recent_scores=recent_scores,
            window_minutes=window_minutes,
        )

        return {
            "success": True,
            "trend": trend,
        }

    except Exception as e:
        logger.error(f"❌ Error analyzing trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Health Check
# ============================================


@router.get("/health")
async def engagement_health(
    tracker=Depends(get_tracker),
    db=Depends(get_db),
):
    """
    Engagement 시스템 상태 확인

    Returns:
        {status: str, tracker: bool, database: bool}
    """
    return {
        "status": "healthy",
        "tracker": tracker is not None,
        "database": db is not None,
        "timestamp": datetime.now(UTC).isoformat(),
    }
