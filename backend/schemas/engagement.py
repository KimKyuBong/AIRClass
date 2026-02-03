"""
Engagement Schema Models
참여도 관련 Pydantic 모델
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class EngagementMetrics(BaseModel):
    """참여도 지표"""

    attention_score: float = 0.0  # 0-1
    participation_count: int = 0
    quiz_accuracy: float = 0.0  # 0-1
    response_latency_ms: int = 0
    chat_message_count: int = 0
    last_activity_time: Optional[datetime] = None


class StudentEngagement(BaseModel):
    """학생 개별 참여도"""

    session_id: str
    student_id: str
    student_name: str
    node_name: str
    metrics: EngagementMetrics
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreenshotAnalysis(BaseModel):
    """스크린샷 분석 결과"""

    session_id: str
    screenshot_id: str
    screenshot_time: datetime

    # AI 분석 결과
    summary: str  # 3줄 요약
    concepts: list[str]  # 추출된 개념
    learning_objectives: list[str]  # 학습 목표

    # 저장 위치
    file_path: str
    thumbnail_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
