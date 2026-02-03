"""
Schemas Package
Pydantic 데이터 모델 정의
"""

# Common types
from .common import (
    UserType,
    ActivityType,
    SentimentType,
    QuestionCategory,
)

# Session models
from .session import (
    SessionBase,
    SessionCreate,
    Session,
    StudentWeakness,
    SessionSummary,
    StudentLearningPath,
)

# Quiz models
from .quiz import (
    QuizOption,
    QuizBase,
    QuizCreate,
    Quiz,
    QuizResponseBase,
    QuizResponseCreate,
    QuizResponse,
    QuizPublishRequest,
    QuizResponseRequest,
)

# Engagement models
from .engagement import (
    EngagementMetrics,
    StudentEngagement,
    ScreenshotAnalysis,
)

# Chat models
from .chat import (
    ChatMessage,
    ChatMessageRequest,
    TokenRequest,
    TokenResponse,
)

__all__ = [
    # Common
    "UserType",
    "ActivityType",
    "SentimentType",
    "QuestionCategory",
    # Session
    "SessionBase",
    "SessionCreate",
    "Session",
    "StudentWeakness",
    "SessionSummary",
    "StudentLearningPath",
    # Quiz
    "QuizOption",
    "QuizBase",
    "QuizCreate",
    "Quiz",
    "QuizResponseBase",
    "QuizResponseCreate",
    "QuizResponse",
    "QuizPublishRequest",
    "QuizResponseRequest",
    # Engagement
    "EngagementMetrics",
    "StudentEngagement",
    "ScreenshotAnalysis",
    # Chat
    "ChatMessage",
    "ChatMessageRequest",
    "TokenRequest",
    "TokenResponse",
]
