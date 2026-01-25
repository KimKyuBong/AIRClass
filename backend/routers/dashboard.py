"""
AIRClass Teacher Dashboard API
실시간 학생 참여도 대시보드 및 혼동도 감지
"""

import logging
import asyncio
from fastapi import APIRouter, HTTPException, Depends, WebSocket, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from datetime import datetime

from models import ActivityType
from engagement import get_engagement_tracker, EngagementCalculator
from database import get_database_manager
from messaging import get_messaging_system

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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


def get_messaging():
    """MessagingSystem 의존성"""
    messaging = get_messaging_system()
    if not messaging:
        raise HTTPException(status_code=503, detail="Messaging system not initialized")
    return messaging


# ============================================
# Session Dashboard Endpoints
# ============================================


@router.get("/session/{session_id}/overview")
async def get_session_overview(
    session_id: str,
    session_duration_minutes: float = Query(50.0, description="세션 진행 시간 (분)"),
    tracker=Depends(get_tracker),
    db=Depends(get_db),
):
    """
    세션 전체 개요 조회

    Args:
        session_id: 세션 ID
        session_duration_minutes: 세션 진행 시간

    Returns:
        Dict: 세션 개요 (학생 수, 평균 참여도, 문제 학생 등)
    """
    try:
        # 세션 참여도 통계 계산
        stats = await tracker.calculate_session_engagement(
            session_id=session_id,
            session_duration_minutes=session_duration_minutes,
        )

        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")

        # 상세 분석
        engagements = await db.get_session_engagement(session_id)
        calculator = EngagementCalculator()

        # 혼동 학생 감지
        confused_students = []
        for eng in engagements:
            is_confused, confidence = calculator.detect_confusion(
                quiz_accuracy=eng.metrics.quiz_accuracy,
                chat_activity_high=eng.metrics.chat_message_count > 5,
                confusion_indicators=[],
            )
            if is_confused and confidence > 0.6:
                confused_students.append(
                    {
                        "student_id": eng.student_id,
                        "student_name": eng.student_name,
                        "confidence": confidence,
                        "quiz_accuracy": eng.metrics.quiz_accuracy,
                        "chat_count": eng.metrics.chat_message_count,
                    }
                )

        return {
            "success": True,
            "session_id": session_id,
            "overview": {
                **stats,
                "confused_students": confused_students,
                "needs_attention": len(confused_students),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting session overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/students")
async def get_students_dashboard(
    session_id: str,
    sort_by: str = Query(
        "engagement", description="정렬 기준: engagement, name, accuracy"
    ),
    session_duration_minutes: float = Query(50.0, description="세션 진행 시간 (분)"),
    db=Depends(get_db),
):
    """
    세션의 모든 학생 상태 조회 (정렬 가능)

    Args:
        session_id: 세션 ID
        sort_by: 정렬 기준 (engagement, name, accuracy)
        session_duration_minutes: 세션 진행 시간

    Returns:
        List[Dict]: 학생별 상세 정보 (참여도, 정답률, 반응 시간 등)
    """
    try:
        engagements = await db.get_session_engagement(session_id)
        calculator = EngagementCalculator()

        student_data = []

        for eng in engagements:
            # 참여도 점수 계산
            participation_score = calculator.calculate_participation_score(
                chat_message_count=eng.metrics.chat_message_count,
                quiz_response_count=eng.metrics.participation_count,
                session_duration_minutes=session_duration_minutes,
            )

            overall_score = calculator.calculate_overall_engagement_score(
                attention_score=eng.metrics.attention_score,
                participation_score=participation_score,
                quiz_accuracy=eng.metrics.quiz_accuracy,
            )

            interpretation = calculator.interpret_engagement_level(overall_score)

            # 혼동 감지
            is_confused, confusion_confidence = calculator.detect_confusion(
                quiz_accuracy=eng.metrics.quiz_accuracy,
                chat_activity_high=eng.metrics.chat_message_count > 5,
                confusion_indicators=[],
            )

            student_data.append(
                {
                    "student_id": eng.student_id,
                    "student_name": eng.student_name,
                    "node_name": eng.node_name,
                    "overall_score": round(overall_score, 2),
                    "level": interpretation["level"],
                    "color": interpretation["color"],
                    "metrics": {
                        "quiz_accuracy": round(eng.metrics.quiz_accuracy * 100, 1),
                        "participation_count": eng.metrics.participation_count,
                        "chat_message_count": eng.metrics.chat_message_count,
                        "avg_response_latency_ms": eng.metrics.response_latency_ms,
                    },
                    "confusion": {
                        "is_confused": is_confused,
                        "confidence": round(confusion_confidence, 2),
                    },
                    "recommendations": interpretation["recommendations"],
                    "updated_at": eng.updated_at.isoformat(),
                }
            )

        # 정렬
        if sort_by == "engagement":
            student_data.sort(key=lambda x: x["overall_score"], reverse=True)
        elif sort_by == "name":
            student_data.sort(key=lambda x: x["student_name"])
        elif sort_by == "accuracy":
            student_data.sort(key=lambda x: x["metrics"]["quiz_accuracy"], reverse=True)

        return {
            "success": True,
            "session_id": session_id,
            "total_students": len(student_data),
            "students": student_data,
        }

    except Exception as e:
        logger.error(f"❌ Error getting students dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/student/{student_id}")
async def get_student_details(
    session_id: str,
    student_id: str,
    session_duration_minutes: float = Query(50.0, description="세션 진행 시간 (분)"),
    db=Depends(get_db),
):
    """
    특정 학생의 상세 정보 조회

    Args:
        session_id: 세션 ID
        student_id: 학생 ID
        session_duration_minutes: 세션 진행 시간

    Returns:
        Dict: 학생 상세 정보 (모든 지표, 권장사항 등)
    """
    try:
        engagements = await db.get_session_engagement(session_id)
        engagement = None

        for eng in engagements:
            if eng.student_id == student_id:
                engagement = eng
                break

        if not engagement:
            raise HTTPException(status_code=404, detail="Student not found in session")

        calculator = EngagementCalculator()

        # 종합 점수 계산
        participation_score = calculator.calculate_participation_score(
            chat_message_count=engagement.metrics.chat_message_count,
            quiz_response_count=engagement.metrics.participation_count,
            session_duration_minutes=session_duration_minutes,
        )

        overall_score = calculator.calculate_overall_engagement_score(
            attention_score=engagement.metrics.attention_score,
            participation_score=participation_score,
            quiz_accuracy=engagement.metrics.quiz_accuracy,
        )

        interpretation = calculator.interpret_engagement_level(overall_score)

        # 혼동 감지
        is_confused, confusion_confidence = calculator.detect_confusion(
            quiz_accuracy=engagement.metrics.quiz_accuracy,
            chat_activity_high=engagement.metrics.chat_message_count > 5,
            confusion_indicators=[],
        )

        # 추세 분석 (현재는 단일 점수이므로 기본값)
        trend = calculator.analyze_trend([overall_score])

        return {
            "success": True,
            "session_id": session_id,
            "student": {
                "student_id": engagement.student_id,
                "student_name": engagement.student_name,
                "node_name": engagement.node_name,
            },
            "scores": {
                "overall": round(overall_score, 2),
                "attention": round(engagement.metrics.attention_score * 100, 1),
                "participation": participation_score,
                "quiz_accuracy": round(engagement.metrics.quiz_accuracy * 100, 1),
                "level": interpretation["level"],
                "color": interpretation["color"],
            },
            "metrics": {
                "participation_count": engagement.metrics.participation_count,
                "quiz_accuracy": round(engagement.metrics.quiz_accuracy * 100, 1),
                "response_latency_ms": engagement.metrics.response_latency_ms,
                "chat_message_count": engagement.metrics.chat_message_count,
                "last_activity": engagement.metrics.last_activity_time.isoformat()
                if engagement.metrics.last_activity_time
                else None,
            },
            "confusion": {
                "is_confused": is_confused,
                "confidence": round(confusion_confidence, 2),
                "details": {
                    "low_accuracy": engagement.metrics.quiz_accuracy < 0.5,
                    "high_chat_activity": engagement.metrics.chat_message_count > 5,
                },
            },
            "trend": trend,
            "recommendations": interpretation["recommendations"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting student details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{session_id}")
async def get_alerts(
    session_id: str,
    alert_type: Optional[str] = Query(
        None, description="알림 타입: confusion, low_engagement, no_response"
    ),
    db=Depends(get_db),
):
    """
    세션 알림 조회

    Args:
        session_id: 세션 ID
        alert_type: 알림 타입 필터 (선택사항)

    Returns:
        List[Dict]: 알림 목록
    """
    try:
        engagements = await db.get_session_engagement(session_id)
        calculator = EngagementCalculator()

        alerts = []

        for eng in engagements:
            # 혼동도 감지
            is_confused, confidence = calculator.detect_confusion(
                quiz_accuracy=eng.metrics.quiz_accuracy,
                chat_activity_high=eng.metrics.chat_message_count > 5,
                confusion_indicators=[],
            )

            if is_confused and confidence > 0.6:
                if alert_type is None or alert_type == "confusion":
                    alerts.append(
                        {
                            "type": "confusion",
                            "severity": "high" if confidence > 0.8 else "medium",
                            "student_id": eng.student_id,
                            "student_name": eng.student_name,
                            "message": f"{eng.student_name}이(가) 혼동 상태로 보입니다 (확신도: {confidence:.1%})",
                            "confidence": confidence,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            # 낮은 참여도
            if eng.metrics.quiz_accuracy < 0.3:
                if alert_type is None or alert_type == "low_engagement":
                    alerts.append(
                        {
                            "type": "low_engagement",
                            "severity": "high",
                            "student_id": eng.student_id,
                            "student_name": eng.student_name,
                            "message": f"{eng.student_name}의 정답률이 매우 낮습니다 ({eng.metrics.quiz_accuracy:.1%})",
                            "accuracy": eng.metrics.quiz_accuracy,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

            # 응답 부족
            if (
                eng.metrics.participation_count == 0
                and eng.metrics.chat_message_count == 0
            ):
                if alert_type is None or alert_type == "no_response":
                    alerts.append(
                        {
                            "type": "no_response",
                            "severity": "medium",
                            "student_id": eng.student_id,
                            "student_name": eng.student_name,
                            "message": f"{eng.student_name}이(가) 아직 응답하지 않았습니다",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        return {
            "success": True,
            "session_id": session_id,
            "total_alerts": len(alerts),
            "alerts": sorted(
                alerts, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]]
            ),
        }

    except Exception as e:
        logger.error(f"❌ Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WebSocket: Real-time Dashboard Streaming
# ============================================


@router.websocket("/ws/session/{session_id}")
async def websocket_session_dashboard(
    websocket: WebSocket,
    session_id: str,
    session_duration_minutes: float = 50.0,
):
    """
    실시간 세션 대시보드 스트림 (WebSocket)

    클라이언트로부터:
    - "get_overview" → 세션 개요 전송
    - "get_students" → 학생 목록 전송
    - "get_alerts" → 현재 알림 전송
    - "ping" → pong 응답

    Args:
        session_id: 세션 ID
        session_duration_minutes: 세션 진행 시간
    """
    db = get_database_manager()
    messaging = get_messaging_system()
    tracker = get_engagement_tracker()

    if not all([db, messaging, tracker]):
        await websocket.close(code=4503, reason="Services not available")
        return

    await websocket.accept()

    try:
        logger.info(f"🎧 WebSocket connected: {session_id}")

        while True:
            # 클라이언트로부터 메시지 수신
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # 타임아웃: 자동 갱신
                data = "auto_update"

            if data == "ping":
                await websocket.send_json({"type": "pong"})

            elif data == "get_overview":
                stats = await tracker.calculate_session_engagement(
                    session_id=session_id,
                    session_duration_minutes=session_duration_minutes,
                )
                await websocket.send_json(
                    {
                        "type": "overview",
                        "data": stats,
                    }
                )

            elif data == "get_students":
                engagements = await db.get_session_engagement(session_id)
                calculator = EngagementCalculator()

                students = []
                for eng in engagements:
                    participation_score = calculator.calculate_participation_score(
                        chat_message_count=eng.metrics.chat_message_count,
                        quiz_response_count=eng.metrics.participation_count,
                        session_duration_minutes=session_duration_minutes,
                    )
                    overall_score = calculator.calculate_overall_engagement_score(
                        attention_score=eng.metrics.attention_score,
                        participation_score=participation_score,
                        quiz_accuracy=eng.metrics.quiz_accuracy,
                    )
                    interpretation = calculator.interpret_engagement_level(
                        overall_score
                    )

                    students.append(
                        {
                            "student_id": eng.student_id,
                            "student_name": eng.student_name,
                            "overall_score": round(overall_score, 2),
                            "level": interpretation["level"],
                        }
                    )

                await websocket.send_json(
                    {
                        "type": "students",
                        "count": len(students),
                        "data": students,
                    }
                )

            elif data == "get_alerts" or data == "auto_update":
                engagements = await db.get_session_engagement(session_id)
                calculator = EngagementCalculator()

                alerts = []
                for eng in engagements:
                    is_confused, confidence = calculator.detect_confusion(
                        quiz_accuracy=eng.metrics.quiz_accuracy,
                        chat_activity_high=eng.metrics.chat_message_count > 5,
                        confusion_indicators=[],
                    )
                    if is_confused and confidence > 0.6:
                        alerts.append(
                            {
                                "type": "confusion",
                                "student_id": eng.student_id,
                                "student_name": eng.student_name,
                                "confidence": round(confidence, 2),
                            }
                        )

                await websocket.send_json(
                    {
                        "type": "alerts",
                        "count": len(alerts),
                        "data": alerts,
                    }
                )

    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        await websocket.close(code=4000, reason=str(e))


# ============================================
# Health Check
# ============================================


@router.get("/health")
async def dashboard_health(
    tracker=Depends(get_tracker),
    db=Depends(get_db),
    messaging=Depends(get_messaging),
):
    """
    Dashboard 시스템 상태 확인

    Returns:
        {status: str, tracker: bool, database: bool, messaging: bool}
    """
    return {
        "status": "healthy",
        "tracker": tracker is not None,
        "database": db is not None,
        "messaging": messaging is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }
