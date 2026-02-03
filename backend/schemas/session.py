"""
Session Schema Models
세션 관련 Pydantic 모델
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class SessionBase(BaseModel):
    """세션 기본 모델"""

    session_id: str
    teacher_id: str
    class_name: str
    topics: List[str] = []
    start_time: datetime


class SessionCreate(SessionBase):
    """세션 생성 요청"""

    pass


class Session(SessionBase):
    """세션 조회 응답"""

    end_time: Optional[datetime] = None
    total_students: int = 0
    recording_file: Optional[str] = None
    status: str = "active"  # active, ended, archived

    model_config = ConfigDict(from_attributes=True)


class StudentWeakness(BaseModel):
    """학생 약점"""

    concept: str
    confusion_level: float  # 0-1
    frequency: int  # 혼동 횟수
    last_mentioned: datetime


class SessionSummary(BaseModel):
    """세션 종료 후 종합 분석"""

    session_id: str
    teacher_id: str
    session_date: datetime

    # 참석 통계
    total_students: int
    attended_students: int
    attendance_rate: float

    # 학습 성과
    average_quiz_accuracy: float
    average_response_time_ms: int
    total_chat_messages: int
    total_questions: int

    # 문제점 분석
    confusion_hotspots: List[StudentWeakness]

    # AI 추천
    recommendations: List[str]
    concepts_to_review: List[str]
    students_needing_support: List[str]

    model_config = ConfigDict(from_attributes=True)


class StudentLearningPath(BaseModel):
    """학생 개별 학습 경로"""

    student_id: str
    student_name: str

    # 진도
    completed_topics: List[str]
    current_topic: str
    next_topics: List[str]

    # 학습 분석
    strengths: List[str]
    improvement_areas: List[str]

    # AI 추천
    focus_areas: List[str]
    suggested_resources: List[str]

    # 동료 비교
    class_average_accuracy: float
    student_accuracy: float
    rank_percentage: float  # 상위 몇 %

    model_config = ConfigDict(from_attributes=True)
