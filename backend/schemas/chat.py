"""
Chat Schema Models
채팅 및 분석 관련 Pydantic 모델
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from .common import SentimentType, QuestionCategory, UserType


class ChatMessage(BaseModel):
    """채팅 메시지 분석"""

    session_id: str
    student_id: str
    student_name: str
    message: str
    message_time: datetime

    # 분석 결과
    is_question: bool
    sentiment: SentimentType
    question_category: Optional[QuestionCategory] = None
    confusion_level: int = 0  # 1-5 (높을수록 혼동도 높음)
    topic: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatMessageRequest(BaseModel):
    """채팅 메시지 요청"""

    session_id: str
    user_id: str
    user_name: str
    message: str
    user_type: UserType


class TokenRequest(BaseModel):
    """토큰 생성 요청"""

    user_type: UserType
    user_id: str
    user_name: Optional[str] = None
    session_id: str
    node_id: Optional[str] = None


class TokenResponse(BaseModel):
    """토큰 생성 응답"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # 초 단위
    user_type: UserType
    session_id: str
