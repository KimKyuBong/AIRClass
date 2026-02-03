"""
WebSocket Router
================
실시간 통신을 위한 WebSocket 엔드포인트

- /ws/teacher: 교사용 WebSocket (채팅, 제어)
- /ws/student: 학생용 WebSocket (채팅, ping)
- /ws/monitor: 모니터용 WebSocket (연결 상태 유지)
- POST /ws/broadcast/quiz: 퀴즈 발행 알림
- POST /ws/broadcast/engagement: 참여도 업데이트

Note: 비디오 스트리밍은 MediaMTX WebRTC를 통해 처리됨
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from utils import get_connection_manager

logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["websocket"])

# ConnectionManager 싱글톤 가져오기
manager = get_connection_manager()


# ============================================
# Request Models
# ============================================


class QuizBroadcastRequest(BaseModel):
    """퀴즈 브로드캐스트 요청"""

    quiz_id: str
    session_id: str
    question: str
    options: list[str]
    time_limit: int = 60
    metadata: Optional[Dict[str, Any]] = None


class EngagementBroadcastRequest(BaseModel):
    """참여도 브로드캐스트 요청"""

    session_id: str
    student_id: str
    student_name: str
    engagement_score: float
    attention_score: Optional[float] = None
    participation_score: Optional[int] = None
    quiz_accuracy: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@router.websocket("/ws/teacher")
async def websocket_teacher(websocket: WebSocket):
    """교사용 WebSocket - 학생 관리 및 채팅"""
    await manager.connect_teacher(websocket)

    try:
        while True:
            data = await websocket.receive()

            if "text" in data:
                message = json.loads(data["text"])
                msg_type = message.get("type")

                if msg_type == "chat":
                    # 교사의 채팅 메시지를 모든 학생에게 전송
                    await manager.send_to_all_students(
                        {
                            "type": "chat",
                            "from": "teacher",
                            "message": message.get("message"),
                        }
                    )

                elif msg_type == "control":
                    # 제어 명령 (예: 특정 학생에게 메시지)
                    target = message.get("target")
                    command = message.get("command")
                    if target and command:
                        await manager.send_to_student(
                            target, {"type": "control", "command": command}
                        )

            # Note: Screen data is now handled by MediaMTX WebRTC streaming
            # Android app sends RTMP to MediaMTX, clients play WebRTC directly

    except WebSocketDisconnect:
        manager.disconnect_teacher()
    except Exception as e:
        print(f"Error in teacher websocket: {e}")
        manager.disconnect_teacher()


@router.websocket("/ws/student")
async def websocket_student(websocket: WebSocket, name: str):
    """학생용 WebSocket - 채팅"""
    await manager.connect_student(websocket, name)

    try:
        # Note: Students now receive video via WebRTC stream from MediaMTX

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "chat":
                # 학생의 질문을 교사에게 전송
                await manager.send_to_teacher(
                    {"type": "chat", "from": name, "message": message.get("message")}
                )

            elif msg_type == "ping":
                # 연결 유지를 위한 ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect_student(name)
        # 교사에게 학생 목록 업데이트 전송
        if manager.teacher:
            await manager.send_to_teacher(
                {"type": "student_list", "students": list(manager.students.keys())}
            )
    except Exception as e:
        print(f"Error in student websocket ({name}): {e}")
        manager.disconnect_student(name)


@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """모니터용 WebSocket - 연결 상태 유지"""
    await manager.connect_monitor(websocket)

    try:
        # Note: Monitors now receive video via WebRTC stream from MediaMTX

        while True:
            # 모니터는 데이터를 보내지 않고 수신만 함
            # 하지만 연결 유지를 위해 메시지 대기
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect_monitor(websocket)
    except Exception as e:
        print(f"Error in monitor websocket: {e}")
        manager.disconnect_monitor(websocket)


# ============================================
# HTTP Broadcast Endpoints
# ============================================


@router.post("/ws/broadcast/quiz")
async def broadcast_quiz(request: QuizBroadcastRequest):
    """
    퀴즈 발행 알림을 모든 학생에게 전송

    Quiz API에서 퀴즈를 발행할 때 호출됨

    Args:
        request: 퀴즈 정보

    Returns:
        {success: bool, students_notified: int}
    """
    try:
        quiz_data = {
            "quiz_id": request.quiz_id,
            "session_id": request.session_id,
            "question": request.question,
            "options": request.options,
            "time_limit": request.time_limit,
            "metadata": request.metadata or {},
        }

        await manager.broadcast_quiz(quiz_data)

        return {
            "success": True,
            "students_notified": len(manager.students),
            "quiz_id": request.quiz_id,
        }

    except Exception as e:
        logger.error(f"❌ Error broadcasting quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ws/broadcast/engagement")
async def broadcast_engagement(request: EngagementBroadcastRequest):
    """
    참여도 업데이트를 교사와 모니터에게 전송

    Engagement API에서 참여도가 업데이트될 때 호출됨

    Args:
        request: 참여도 정보

    Returns:
        {success: bool, recipients: int}
    """
    try:
        engagement_data = {
            "session_id": request.session_id,
            "student_id": request.student_id,
            "student_name": request.student_name,
            "engagement_score": request.engagement_score,
            "attention_score": request.attention_score,
            "participation_score": request.participation_score,
            "quiz_accuracy": request.quiz_accuracy,
            "metadata": request.metadata or {},
        }

        await manager.broadcast_engagement_update(engagement_data)

        recipients = 0
        if manager.teacher:
            recipients += 1
        recipients += len(manager.monitors)

        return {
            "success": True,
            "recipients": recipients,
            "student_id": request.student_id,
        }

    except Exception as e:
        logger.error(f"❌ Error broadcasting engagement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ws/status")
async def websocket_status():
    """
    WebSocket 연결 상태 조회

    Returns:
        {teacher_connected: bool, students_count: int, monitors_count: int}
    """
    return {
        "teacher_connected": manager.teacher is not None,
        "students_count": len(manager.students),
        "students": list(manager.students.keys()),
        "monitors_count": len(manager.monitors),
    }
