"""
Quiz Schema Models
퀴즈 관련 Pydantic 모델
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class QuizOption(BaseModel):
    """퀴즈 선택지"""

    id: str
    text: str


class QuizBase(BaseModel):
    """퀴즈 기본 모델"""

    quiz_id: str
    session_id: str
    question: str
    options: List[QuizOption]
    correct_option_id: str
    topic: str
    difficulty: int = 1  # 1-5
    explanation: Optional[str] = None


class QuizCreate(QuizBase):
    """퀴즈 생성 요청"""

    pass


class Quiz(QuizBase):
    """퀴즈 조회 응답"""

    created_at: datetime
    published: bool = False
    status: str = "draft"  # draft, active, closed
    published_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    total_responses: int = 0
    correct_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class QuizResponseBase(BaseModel):
    """퀴즈 응답 기본 모델"""

    quiz_id: str
    student_id: str
    selected_option_id: str


class QuizResponseCreate(QuizResponseBase):
    """퀴즈 응답 생성 요청"""

    response_time: float  # 응답 시간 (초)


class QuizResponse(QuizResponseBase):
    """퀴즈 응답 조회 응답"""

    is_correct: bool
    response_time: float  # 응답 시간 (초)
    responded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuizPublishRequest(BaseModel):
    """퀴즈 발행 요청"""

    session_id: str
    quiz: QuizCreate
    publish_to_all: bool = True


class QuizResponseRequest(BaseModel):
    """퀴즈 응답 요청"""

    session_id: str
    quiz_id: str
    student_id: str
    selected_option_id: str
    response_time_ms: int
