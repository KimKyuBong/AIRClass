"""
AIRClass Database Manager
MongoDB 연결 및 데이터 작업
"""

import logging
from motor.motor_asyncio import AsyncClient, AsyncDatabase
from typing import Optional, List, Dict
from models import *

logger = logging.getLogger(__name__)


class DatabaseManager:
    """MongoDB 데이터베이스 관리자"""

    def __init__(self, mongodb_url: str = "mongodb://localhost:27017"):
        self.mongodb_url = mongodb_url
        self.client: Optional[AsyncClient] = None
        self.db: Optional[AsyncDatabase] = None

        logger.info(f"💾 DatabaseManager initialized")
        logger.info(f"   MongoDB URL: {mongodb_url}")

    async def init(self) -> bool:
        """MongoDB 연결 초기화"""
        try:
            self.client = AsyncClient(self.mongodb_url)
            self.db = self.client["airclass"]

            # 연결 테스트
            await self.db.command("ping")

            logger.info("✅ MongoDB connection established")

            # 인덱스 생성
            await self._create_indexes()

            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return False

    async def _create_indexes(self):
        """필요한 인덱스 생성"""
        try:
            # Session 인덱스
            await self.db.sessions.create_index("session_id", unique=True)
            await self.db.sessions.create_index("teacher_id")
            await self.db.sessions.create_index("start_time")

            # Quiz 인덱스
            await self.db.quizzes.create_index("quiz_id", unique=True)
            await self.db.quizzes.create_index("session_id")
            await self.db.quizzes.create_index("created_at")

            # QuizResponse 인덱스
            await self.db.quiz_responses.create_index([("session_id", 1), ("quiz_id", 1), ("student_id", 1)])
            await self.db.quiz_responses.create_index("responded_at")

            # Chat 인덱스
            await self.db.chat_analytics.create_index([("session_id", 1), ("message_time", 1)])
            await self.db.chat_analytics.create_index("student_id")

            # Engagement 인덱스
            await self.db.student_engagement.create_index([("session_id", 1), ("student_id", 1)])
            await self.db.student_engagement.create_index("updated_at")

            # Screenshot 인덱스
            await self.db.screenshot_analysis.create_index([("session_id", 1), ("screenshot_time", 1)])

            logger.info("✅ Database indexes created")

        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")

    # ============================================
    # Session Operations
    # ============================================

    async def create_session(self, session: SessionCreate) -> Session:
        """세션 생성"""
        result = await self.db.sessions.insert_one(session.model_dump())
        return await self.get_session(session.session_id)

    async def get_session(self, session_id: str) -> Optional[Session]:
        """세션 조회"""
        doc = await self.db.sessions.find_one({"session_id": session_id})
        return Session(**doc) if doc else None

    async def end_session(self, session_id: str) -> bool:
        """세션 종료"""
        result = await self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "ended", "end_time": datetime.utcnow()}}
        )
        return result.modified_count > 0

    # ============================================
    # Quiz Operations
    # ============================================

    async def create_quiz(self, quiz: QuizCreate) -> Quiz:
        """퀴즈 생성"""
        await self.db.quizzes.insert_one(quiz.model_dump())
        return await self.get_quiz(quiz.quiz_id)

    async def get_quiz(self, quiz_id: str) -> Optional[Quiz]:
        """퀴즈 조회"""
        doc = await self.db.quizzes.find_one({"quiz_id": quiz_id})
        return Quiz(**doc) if doc else None

    async def publish_quiz(self, quiz_id: str) -> bool:
        """퀴즈 발행"""
        result = await self.db.quizzes.update_one(
            {"quiz_id": quiz_id},
            {"$set": {"published_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    # ============================================
    # Quiz Response Operations
    # ============================================

    async def create_quiz_response(self, response: QuizResponseCreate) -> QuizResponse:
        """퀴즈 응답 저장"""
        quiz = await self.get_quiz(response.quiz_id)
        is_correct = response.selected_option_id == quiz.correct_option_id

        response_doc = {
            **response.model_dump(),
            "is_correct": is_correct,
            "responded_at": datetime.utcnow(),
        }

        await self.db.quiz_responses.insert_one(response_doc)

        # 퀴즈 통계 업데이트
        await self.db.quizzes.update_one(
            {"quiz_id": response.quiz_id},
            {
                "$inc": {
                    "total_responses": 1,
                    "correct_count": 1 if is_correct else 0,
                }
            },
        )

        return QuizResponse(**response_doc)

    async def get_quiz_responses(self, quiz_id: str) -> List[QuizResponse]:
        """퀴즈 응답 목록 조회"""
        docs = await self.db.quiz_responses.find({"quiz_id": quiz_id}).to_list(None)
        return [QuizResponse(**doc) for doc in docs]

    # ============================================
    # Chat Analytics Operations
    # ============================================

    async def save_chat_analysis(self, chat: ChatMessage) -> bool:
        """채팅 분석 결과 저장"""
        try:
            await self.db.chat_analytics.insert_one(chat.model_dump())
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save chat analysis: {e}")
            return False

    async def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        """세션의 채팅 메시지 조회"""
        docs = await self.db.chat_analytics.find(
            {"session_id": session_id}
        ).sort("message_time", 1).to_list(None)
        return [ChatMessage(**doc) for doc in docs]

    # ============================================
    # Student Engagement Operations
    # ============================================

    async def update_student_engagement(self, engagement: StudentEngagement) -> bool:
        """학생 참여도 업데이트"""
        try:
            result = await self.db.student_engagement.update_one(
                {"session_id": engagement.session_id, "student_id": engagement.student_id},
                {"$set": engagement.model_dump()},
                upsert=True,
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update engagement: {e}")
            return False

    async def get_session_engagement(self, session_id: str) -> List[StudentEngagement]:
        """세션의 모든 학생 참여도 조회"""
        docs = await self.db.student_engagement.find(
            {"session_id": session_id}
        ).to_list(None)
        return [StudentEngagement(**doc) for doc in docs]

    # ============================================
    # Screenshot Analysis Operations
    # ============================================

    async def save_screenshot_analysis(self, screenshot: ScreenshotAnalysis) -> bool:
        """스크린샷 분석 결과 저장"""
        try:
            await self.db.screenshot_analysis.insert_one(screenshot.model_dump())
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save screenshot analysis: {e}")
            return False

    async def get_session_screenshots(self, session_id: str) -> List[ScreenshotAnalysis]:
        """세션의 스크린샷 분석 조회"""
        docs = await self.db.screenshot_analysis.find(
            {"session_id": session_id}
        ).sort("screenshot_time", 1).to_list(None)
        return [ScreenshotAnalysis(**doc) for doc in docs]

    # ============================================
    # Learning Analytics Operations
    # ============================================

    async def save_session_summary(self, summary: SessionSummary) -> bool:
        """세션 분석 요약 저장"""
        try:
            await self.db.session_summaries.insert_one(summary.model_dump())
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save session summary: {e}")
            return False

    async def get_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        """세션 분석 요약 조회"""
        doc = await self.db.session_summaries.find_one({"session_id": session_id})
        return SessionSummary(**doc) if doc else None

    async def save_student_learning_path(self, path: StudentLearningPath) -> bool:
        """학생 학습 경로 저장"""
        try:
            result = await self.db.student_learning_paths.update_one(
                {"student_id": path.student_id},
                {"$set": path.model_dump()},
                upsert=True,
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save learning path: {e}")
            return False

    async def get_student_learning_path(self, student_id: str) -> Optional[StudentLearningPath]:
        """학생 학습 경로 조회"""
        doc = await self.db.student_learning_paths.find_one({"student_id": student_id})
        return StudentLearningPath(**doc) if doc else None

    async def close(self):
        """MongoDB 연결 종료"""
        if self.client:
            self.client.close()
            logger.info("✅ MongoDB connection closed")


# 전역 인스턴스
db_manager = None


async def init_database_manager() -> Optional[DatabaseManager]:
    """DatabaseManager 초기화"""
    global db_manager

    import os

    try:
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
        db_manager = DatabaseManager(mongodb_url)

        if await db_manager.init():
            logger.info("✅ DatabaseManager initialized successfully")
            return db_manager
        else:
            logger.error("❌ Failed to initialize DatabaseManager")
            db_manager = None
            return None

    except Exception as e:
        logger.error(f"❌ Error initializing DatabaseManager: {e}")
        db_manager = None
        return None


def get_database_manager() -> Optional[DatabaseManager]:
    """DatabaseManager 인스턴스 반환"""
    return db_manager
