"""
WebSocket Connection Manager
교사/학생/모니터 WebSocket 연결 관리
"""

from fastapi import WebSocket
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 연결 관리"""

    def __init__(self):
        self.teacher: WebSocket | None = None
        self.students: Dict[str, WebSocket] = {}
        self.monitors: Set[WebSocket] = set()

    async def connect_teacher(self, websocket: WebSocket):
        """교사 연결"""
        await websocket.accept()
        if self.teacher:
            # 기존 교사가 있으면 연결 해제
            try:
                await self.teacher.close()
            except:
                pass
        self.teacher = websocket
        logger.info("👨‍🏫 Teacher connected")

    async def connect_student(self, websocket: WebSocket, name: str):
        """학생 연결"""
        await websocket.accept()
        self.students[name] = websocket
        logger.info(f"👨‍🎓 Student '{name}' connected ({len(self.students)} total)")

        # 교사에게 학생 목록 업데이트 전송
        if self.teacher:
            await self.send_to_teacher(
                {"type": "student_list", "students": list(self.students.keys())}
            )

    async def connect_monitor(self, websocket: WebSocket):
        """모니터 연결"""
        await websocket.accept()
        self.monitors.add(websocket)
        logger.info(f"📺 Monitor connected ({len(self.monitors)} total)")

    def disconnect_teacher(self):
        """교사 연결 해제"""
        self.teacher = None
        logger.info("👨‍🏫 Teacher disconnected")

    def disconnect_student(self, name: str):
        """학생 연결 해제"""
        if name in self.students:
            del self.students[name]
            logger.info(
                f"👨‍🎓 Student '{name}' disconnected ({len(self.students)} remaining)"
            )

    def disconnect_monitor(self, ws: WebSocket):
        """모니터 연결 해제"""
        self.monitors.discard(ws)
        logger.info(f"📺 Monitor disconnected ({len(self.monitors)} remaining)")

    async def send_to_teacher(self, message: dict):
        """교사에게 메시지 전송"""
        if self.teacher:
            try:
                await self.teacher.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to teacher: {e}")
                self.disconnect_teacher()

    async def send_to_student(self, name: str, message: dict):
        """특정 학생에게 메시지 전송"""
        if name in self.students:
            try:
                await self.students[name].send_json(message)
            except Exception as e:
                logger.error(f"Error sending to student {name}: {e}")
                self.disconnect_student(name)

    async def send_to_all_students(self, message: dict):
        """모든 학생에게 메시지 브로드캐스트"""
        disconnected = []
        for name, ws in self.students.items():
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to student {name}: {e}")
                disconnected.append(name)

        # 연결 실패한 학생 제거
        for name in disconnected:
            self.disconnect_student(name)

    async def send_to_monitors(self, message: dict):
        """모든 모니터에게 메시지 브로드캐스트"""
        disconnected = []
        for ws in self.monitors:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to monitor: {e}")
                disconnected.append(ws)

        # 연결 실패한 모니터 제거
        for ws in disconnected:
            self.disconnect_monitor(ws)

    async def broadcast_quiz(self, quiz_data: dict):
        """
        퀴즈 발행 시 모든 학생에게 알림

        Args:
            quiz_data: 퀴즈 정보 (quiz_id, question, options, time_limit 등)
        """
        message = {"type": "quiz_published", "data": quiz_data}
        await self.send_to_all_students(message)
        logger.info(
            f"📢 Quiz {quiz_data.get('quiz_id')} broadcasted to {len(self.students)} students"
        )

    async def broadcast_engagement_update(self, engagement_data: dict):
        """
        참여도 업데이트를 교사와 모니터에게 전송

        Args:
            engagement_data: 참여도 정보 (session_id, student_id, engagement_score 등)
        """
        message = {"type": "engagement_update", "data": engagement_data}

        # 교사에게 전송
        if self.teacher:
            try:
                await self.teacher.send_json(message)
            except Exception as e:
                logger.error(f"Error sending engagement to teacher: {e}")

        # 모니터에게 전송
        await self.send_to_monitors(message)

        logger.debug(
            f"📊 Engagement update sent for student {engagement_data.get('student_id')}"
        )


# Singleton instance
_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """ConnectionManager 싱글톤 인스턴스 반환"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
