"""
AIRClass Engagement Event Listener
Redis 이벤트를 수신하여 실시간 참여도 추적
"""

import logging
import json
import asyncio
from typing import Optional
from datetime import datetime
import redis.asyncio as redis

from engagement import get_engagement_tracker, EngagementTracker
from database import get_database_manager
from models import ActivityType

logger = logging.getLogger(__name__)


class EngagementEventListener:
    """Engagement 이벤트 리스너"""

    def __init__(self, redis_url: str, tracker: EngagementTracker, db_manager):
        """
        Args:
            redis_url: Redis URL
            tracker: EngagementTracker 인스턴스
            db_manager: DatabaseManager 인스턴스
        """
        self.redis_url = redis_url
        self.tracker = tracker
        self.db_manager = db_manager
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.running = False

        logger.info("🎧 EngagementEventListener initialized")

    async def connect(self) -> bool:
        """Redis 연결"""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            return False

    async def start(self, session_id: str):
        """
        특정 세션의 engagement 이벤트 수신 시작

        Args:
            session_id: 세션 ID
        """
        if not self.redis_client:
            logger.error("❌ Redis not connected")
            return

        try:
            self.pubsub = self.redis_client.pubsub()

            # Engagement 이벤트 채널 구독
            channel = f"airclass:session:{session_id}:engagement"
            await self.pubsub.subscribe(channel)

            logger.info(f"🎧 Listening to engagement events: {channel}")

            self.running = True

            # 메시지 수신 루프
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        await self._handle_engagement_event(event)
                    except Exception as e:
                        logger.error(f"❌ Error handling event: {e}")

        except Exception as e:
            logger.error(f"❌ Failed to listen to events: {e}")
            self.running = False

    async def stop(self):
        """이벤트 수신 중지"""
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        logger.info("🛑 Event listener stopped")

    async def _handle_engagement_event(self, event: dict):
        """
        Engagement 이벤트 처리

        Args:
            event: Redis에서 수신한 이벤트
        """
        try:
            activity_type = event.get("activity_type")
            session_id = event.get("session_id")
            student_id = event.get("student_id")

            if not all([activity_type, session_id, student_id]):
                logger.warning(f"⚠️ Invalid event: missing fields - {event}")
                return

            # Activity Type별 처리
            if activity_type == "chat":
                await self._handle_chat_activity(event)

            elif activity_type == "quiz_response":
                await self._handle_quiz_response(event)

            elif activity_type == "presence":
                await self._handle_presence_activity(event)

            else:
                logger.warning(f"⚠️ Unknown activity type: {activity_type}")

        except Exception as e:
            logger.error(f"❌ Error processing event: {e}")

    async def _handle_chat_activity(self, event: dict):
        """
        채팅 활동 처리

        Event 구조:
        {
            "type": "engagement",
            "activity_type": "chat",
            "session_id": "...",
            "student_id": "...",
            "student_name": "...",
            "node_name": "...",
            "timestamp": "..."
        }
        """
        try:
            session_id = event.get("session_id")
            student_id = event.get("student_id")
            student_name = event.get("student_name", "Unknown")
            node_name = event.get("node_name", "unknown")

            # 참여도 업데이트
            engagement = await self.tracker.track_activity(
                session_id=session_id,
                student_id=student_id,
                student_name=student_name,
                node_name=node_name,
                activity_type=ActivityType.CHAT,
                activity_data={},
            )

            if engagement:
                logger.debug(
                    f"💬 Chat activity tracked: {student_id} - "
                    f"total: {engagement.metrics.chat_message_count}"
                )

        except Exception as e:
            logger.error(f"❌ Error handling chat activity: {e}")

    async def _handle_quiz_response(self, event: dict):
        """
        퀴즈 응답 처리

        Event 구조:
        {
            "type": "engagement",
            "activity_type": "quiz_response",
            "session_id": "...",
            "student_id": "...",
            "student_name": "...",
            "node_name": "...",
            "quiz_id": "...",
            "is_correct": bool,
            "response_time_ms": int,
            "timestamp": "..."
        }
        """
        try:
            session_id = event.get("session_id")
            student_id = event.get("student_id")
            student_name = event.get("student_name", "Unknown")
            node_name = event.get("node_name", "unknown")
            response_time_ms = event.get("response_time_ms", 0)
            is_correct = event.get("is_correct", False)

            # 참여도 업데이트
            engagement = await self.tracker.track_activity(
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

            if engagement:
                logger.debug(
                    f"📝 Quiz response tracked: {student_id} - "
                    f"accuracy: {engagement.metrics.quiz_accuracy:.2%} - "
                    f"response_time: {response_time_ms}ms"
                )

        except Exception as e:
            logger.error(f"❌ Error handling quiz response: {e}")

    async def _handle_presence_activity(self, event: dict):
        """
        화면 시청 시간 처리

        Event 구조:
        {
            "type": "engagement",
            "activity_type": "presence",
            "session_id": "...",
            "student_id": "...",
            "student_name": "...",
            "node_name": "...",
            "screen_time_seconds": int,
            "timestamp": "..."
        }
        """
        try:
            session_id = event.get("session_id")
            student_id = event.get("student_id")
            student_name = event.get("student_name", "Unknown")
            node_name = event.get("node_name", "unknown")

            # 현재는 단순히 로깅만 수행
            # 추후 screen_time 기반 attention_score 계산에 사용
            logger.debug(f"👁️  Presence activity: {student_id} on {node_name}")

        except Exception as e:
            logger.error(f"❌ Error handling presence activity: {e}")

    async def close(self):
        """연결 종료"""
        await self.stop()
        if self.redis_client:
            await self.redis_client.close()
            logger.info("✅ Engagement listener closed")


# 전역 인스턴스
engagement_listener = None


async def init_engagement_listener(
    redis_url: str,
    tracker: EngagementTracker,
    db_manager,
) -> Optional[EngagementEventListener]:
    """EngagementEventListener 초기화"""
    global engagement_listener

    try:
        engagement_listener = EngagementEventListener(redis_url, tracker, db_manager)

        if await engagement_listener.connect():
            logger.info("✅ EngagementEventListener initialized successfully")
            return engagement_listener
        else:
            logger.error("❌ Failed to initialize EngagementEventListener")
            engagement_listener = None
            return None

    except Exception as e:
        logger.error(f"❌ Error initializing EngagementEventListener: {e}")
        engagement_listener = None
        return None


def get_engagement_listener() -> Optional[EngagementEventListener]:
    """EngagementEventListener 인스턴스 반환"""
    return engagement_listener
