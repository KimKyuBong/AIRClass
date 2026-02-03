"""
AIRClass Messaging System
Redis Pub/Sub을 사용한 멀티노드 채팅 및 학생 목록 동기화
"""

import redis.asyncio as redis
import json
import logging
from typing import Optional, Dict, Set, Callable
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class MessagingSystem:
    """Redis 기반 멀티노드 메시징 시스템"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.pubsub = None
        self.local_students: Set[str] = set()
        self.callbacks: Dict[str, list] = {
            "chat": [],
            "student_joined": [],
            "student_left": [],
            "quiz": [],
            "engagement": [],
        }

        logger.info(f"📨 MessagingSystem initialized")
        logger.info(f"   Redis URL: {redis_url}")

    async def init(self) -> bool:
        """Redis 연결 초기화"""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            
            # Redis 연결 테스트
            await self.redis_client.ping()
            
            logger.info("✅ Redis connection established")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            return False

    async def publish_chat(self, session_id: str, user_id: str, user_name: str, 
                          message: str, user_type: str = "student") -> bool:
        """
        채팅 메시지 발행 (모든 노드에 동기화)
        
        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            user_name: 사용자 이름
            message: 메시지 내용
            user_type: 사용자 타입 (student, teacher, monitor)
        """
        if not self.redis_client:
            logger.warning("⚠️ Redis not connected")
            return False

        try:
            chat_message = {
                "type": "chat",
                "session_id": session_id,
                "user_id": user_id,
                "user_name": user_name,
                "message": message,
                "user_type": user_type,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Redis 채널에 발행 (모든 Sub 노드가 수신)
            await self.redis_client.publish(
                f"airclass:session:{session_id}:chat",
                json.dumps(chat_message)
            )

            logger.debug(f"💬 Chat published: {user_name}: {message}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish chat: {e}")
            return False

    async def publish_student_event(self, session_id: str, event_type: str,
                                   student_id: str, node_name: str) -> bool:
        """
        학생 입장/퇴장 이벤트 발행
        
        Args:
            session_id: 세션 ID
            event_type: "joined" 또는 "left"
            student_id: 학생 ID
            node_name: Sub 노드 이름
        """
        if not self.redis_client:
            logger.warning("⚠️ Redis not connected")
            return False

        try:
            # 로컬 학생 목록 업데이트
            if event_type == "joined":
                self.local_students.add(student_id)
            elif event_type == "left":
                self.local_students.discard(student_id)

            event = {
                "type": "student_event",
                "event_type": event_type,
                "session_id": session_id,
                "student_id": student_id,
                "node_name": node_name,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            await self.redis_client.publish(
                f"airclass:session:{session_id}:events",
                json.dumps(event)
            )

            logger.info(f"👤 Student {event_type}: {student_id} on {node_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish student event: {e}")
            return False

    async def get_all_students(self) -> Set[str]:
        """
        모든 노드의 학생 목록 조회
        
        Redis에 저장된 session:{session_id}:students 집합에서 조회
        """
        if not self.redis_client:
            logger.warning("⚠️ Redis not connected")
            return set()

        try:
            # 현재 활성 세션 찾기 (간단한 구현)
            # 프로덕션에서는 세션 ID를 명시적으로 관리해야 함
            keys = await self.redis_client.keys("airclass:students:*")
            
            all_students = set()
            for key in keys:
                members = await self.redis_client.smembers(key)
                all_students.update(members)
            
            return all_students

        except Exception as e:
            logger.error(f"❌ Failed to get students: {e}")
            return set()

    async def add_student_to_session(self, session_id: str, student_id: str) -> bool:
        """세션에 학생 추가"""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.sadd(f"airclass:students:{session_id}", student_id)
            self.local_students.add(student_id)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add student: {e}")
            return False

    async def remove_student_from_session(self, session_id: str, student_id: str) -> bool:
        """세션에서 학생 제거"""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.srem(f"airclass:students:{session_id}", student_id)
            self.local_students.discard(student_id)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to remove student: {e}")
            return False

    async def publish_quiz_event(self, session_id: str, quiz_id: str, 
                                event_type: str, data: dict) -> bool:
        """
        퀴즈 관련 이벤트 발행
        
        Args:
            session_id: 세션 ID
            quiz_id: 퀴즈 ID
            event_type: "published", "response", "closed"
            data: 이벤트 데이터
        """
        if not self.redis_client:
            return False

        try:
            event = {
                "type": "quiz",
                "event_type": event_type,
                "session_id": session_id,
                "quiz_id": quiz_id,
                "timestamp": datetime.now(UTC).isoformat(),
                **data,
            }

            await self.redis_client.publish(
                f"airclass:session:{session_id}:quiz",
                json.dumps(event)
            )

            logger.info(f"📝 Quiz event published: {event_type} ({quiz_id})")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish quiz event: {e}")
            return False

    async def publish_engagement_event(self, session_id: str, student_id: str,
                                      activity_type: str, data: dict = None) -> bool:
        """
        참여도 관련 이벤트 발행
        
        Args:
            session_id: 세션 ID
            student_id: 학생 ID
            activity_type: "chat", "response", "presence"
            data: 추가 데이터
        """
        if not self.redis_client:
            return False

        try:
            event = {
                "type": "engagement",
                "activity_type": activity_type,
                "session_id": session_id,
                "student_id": student_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if data:
                event.update(data)

            await self.redis_client.publish(
                f"airclass:session:{session_id}:engagement",
                json.dumps(event)
            )

            logger.debug(f"📊 Engagement event: {student_id} - {activity_type}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish engagement event: {e}")
            return False

    async def register_callback(self, event_type: str, callback: Callable):
        """
        이벤트 콜백 등록
        
        Args:
            event_type: 이벤트 타입 ("chat", "student_joined", etc.)
            callback: 비동기 콜백 함수
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []

        self.callbacks[event_type].append(callback)
        logger.info(f"✅ Callback registered: {event_type}")

    async def close(self):
        """Redis 연결 종료"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("✅ Redis connection closed")


# 전역 인스턴스
messaging_system = None


async def init_messaging_system() -> Optional[MessagingSystem]:
    """MessagingSystem 초기화"""
    global messaging_system

    import os

    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        messaging_system = MessagingSystem(redis_url)

        if await messaging_system.init():
            logger.info("✅ MessagingSystem initialized successfully")
            return messaging_system
        else:
            logger.error("❌ Failed to initialize MessagingSystem")
            messaging_system = None
            return None

    except Exception as e:
        logger.error(f"❌ Error initializing MessagingSystem: {e}")
        messaging_system = None
        return None


def get_messaging_system() -> Optional[MessagingSystem]:
    """MessagingSystem 인스턴스 반환"""
    return messaging_system
