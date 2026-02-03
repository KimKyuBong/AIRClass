"""
Common Schema Types
공통 타입 및 Enum 정의
"""

from enum import Enum


class UserType(str, Enum):
    """사용자 타입"""

    TEACHER = "teacher"
    STUDENT = "student"
    MONITOR = "monitor"


class ActivityType(str, Enum):
    """활동 타입"""

    CHAT = "chat"
    QUIZ_RESPONSE = "quiz_response"
    PRESENCE = "presence"
    SCREENSHOT = "screenshot"


class SentimentType(str, Enum):
    """감정 타입"""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class QuestionCategory(str, Enum):
    """질문 분류"""

    CONCEPT = "concept"  # 개념 이해
    CALCULATION = "calculation"  # 계산 방법
    APPLICATION = "application"  # 응용
    GENERAL = "general"  # 일반
