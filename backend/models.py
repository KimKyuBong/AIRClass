"""
AIRClass Data Models
MongoDB 스키마 정의 및 Pydantic 모델
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
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


# ============================================
# Session Models (수업 세션)
# ============================================

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

    class Config:
        from_attributes = True


# ============================================
# Quiz Models (퀴즈)
# ============================================

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
    published_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    total_responses: int = 0
    correct_count: int = 0

    class Config:
        from_attributes = True


# ============================================
# Quiz Response Models (퀴즈 응답)
# ============================================

class QuizResponseBase(BaseModel):
    """퀴즈 응답 기본 모델"""
    session_id: str
    quiz_id: str
    student_id: str
    selected_option_id: str

class QuizResponseCreate(QuizResponseBase):
    """퀴즈 응답 생성 요청"""
    response_time_ms: int  # 응답 시간 (밀리초)

class QuizResponse(QuizResponseBase):
    """퀴즈 응답 조회 응답"""
    is_correct: bool
    response_time_ms: int
    responded_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Student Engagement Models (학생 참여도)
# ============================================

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

    class Config:
        from_attributes = True


# ============================================
# Chat Analytics Models (채팅 분석)
# ============================================

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

    class Config:
        from_attributes = True


# ============================================
# Screenshot Analysis Models (스크린샷 분석)
# ============================================

class ScreenshotAnalysis(BaseModel):
    """스크린샷 분석 결과"""
    session_id: str
    screenshot_id: str
    screenshot_time: datetime
    
    # AI 분석 결과
    summary: str  # 3줄 요약
    concepts: List[str]  # 추출된 개념
    learning_objectives: List[str]  # 학습 목표
    
    # 저장 위치
    file_path: str
    thumbnail_path: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================
# Learning Analytics Models (학습 분석)
# ============================================

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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


# ============================================
# API Request/Response Models
# ============================================

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

class ChatMessageRequest(BaseModel):
    """채팅 메시지 요청"""
    session_id: str
    user_id: str
    user_name: str
    message: str
    user_type: UserType

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
