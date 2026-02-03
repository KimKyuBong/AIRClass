"""
AIRClass Engagement Tracking Engine
학생 참여도 계산 및 추적 시스템
"""

import logging
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime, timedelta, UTC
from models import StudentEngagement, EngagementMetrics, ActivityType

logger = logging.getLogger(__name__)


class EngagementCalculator:
    """학생 참여도 계산 엔진"""

    # ============================================
    # Score Configuration (0-100 scale)
    # ============================================

    # Attention Score 계산 가중치 (0-1)
    ATTENTION_WEIGHTS = {
        "quiz_participation": 0.4,  # 퀴즈 응답 여부 (40%)
        "response_latency": 0.3,  # 빠른 응답 (30%)
        "screen_time": 0.3,  # 화면 시청 시간 (30%)
    }

    # Participation Score 계산
    PARTICIPATION_MULTIPLIER = 10  # 1 activity = 10 points, max 100

    # Quiz Accuracy (직접 점수, 0-1 사이)
    # 자동 계산: correct_responses / total_responses

    # Response Latency 기준 (밀리초)
    LATENCY_THRESHOLDS = {
        "excellent": (0, 1000),  # 0-1초: 1.0점
        "good": (1000, 3000),  # 1-3초: 0.8점
        "normal": (3000, 5000),  # 3-5초: 0.6점
        "slow": (5000, 10000),  # 5-10초: 0.4점
        "very_slow": (10000, float("inf")),  # 10초+: 0.2점
    }

    def __init__(self):
        """engagement calculator 초기화"""
        logger.info("📊 EngagementCalculator initialized")

    # ============================================
    # Main Calculation Methods
    # ============================================

    def calculate_attention_score(
        self,
        quiz_participation_rate: float,
        avg_response_latency_ms: int,
        screen_time_minutes: float,
        max_possible_time: float,
    ) -> float:
        """
        Attention Score 계산 (0-1)

        Args:
            quiz_participation_rate: 퀴즈 응답률 (0-1)
            avg_response_latency_ms: 평균 응답 시간 (밀리초)
            screen_time_minutes: 총 시청 시간 (분)
            max_possible_time: 최대 가능 시간 (분, 예: 50분 수업)

        Returns:
            float: 주의집중도 점수 (0-1)
        """
        # 1. Quiz Participation 점수
        quiz_score = quiz_participation_rate  # 0-1

        # 2. Response Latency 점수
        latency_score = self._calculate_latency_score(avg_response_latency_ms)

        # 3. Screen Time 점수
        screen_time_score = min(screen_time_minutes / max_possible_time, 1.0)

        # 가중평균
        attention_score = (
            quiz_score * self.ATTENTION_WEIGHTS["quiz_participation"]
            + latency_score * self.ATTENTION_WEIGHTS["response_latency"]
            + screen_time_score * self.ATTENTION_WEIGHTS["screen_time"]
        )

        return min(max(attention_score, 0.0), 1.0)

    def _calculate_latency_score(self, latency_ms: int) -> float:
        """응답 속도 기반 점수 계산 (0-1)"""
        for threshold, (min_ms, max_ms) in self.LATENCY_THRESHOLDS.items():
            if min_ms <= latency_ms <= max_ms:
                score_map = {
                    "excellent": 1.0,
                    "good": 0.8,
                    "normal": 0.6,
                    "slow": 0.4,
                    "very_slow": 0.2,
                }
                return score_map[threshold]
        return 0.0

    def calculate_participation_score(
        self,
        chat_message_count: int,
        quiz_response_count: int,
        session_duration_minutes: float,
    ) -> int:
        """
        Participation Score 계산 (0-100)

        활동 기반 점수:
        - 채팅 메시지 1개 = 5점
        - 퀴즈 응답 1개 = 5점
        - 세션 참석 = 10점

        Args:
            chat_message_count: 채팅 메시지 수
            quiz_response_count: 퀴즈 응답 수
            session_duration_minutes: 세션 참석 시간

        Returns:
            int: 참여 점수 (0-100)
        """
        score = 0

        # 세션 참석 기본 점수
        if session_duration_minutes > 0:
            score += 10

        # 채팅 활동 점수 (최대 40점)
        chat_score = min(chat_message_count * 5, 40)
        score += chat_score

        # 퀴즈 활동 점수 (최대 50점)
        quiz_score = min(quiz_response_count * 5, 50)
        score += quiz_score

        return min(score, 100)

    def calculate_quiz_accuracy(
        self,
        correct_responses: int,
        total_responses: int,
    ) -> float:
        """
        Quiz Accuracy 계산 (0-1)

        Args:
            correct_responses: 정답 개수
            total_responses: 총 응답 개수

        Returns:
            float: 정답률 (0-1)
        """
        if total_responses == 0:
            return 0.0
        return min(max(correct_responses / total_responses, 0.0), 1.0)

    def calculate_overall_engagement_score(
        self,
        attention_score: float,
        participation_score: int,
        quiz_accuracy: float,
    ) -> float:
        """
        총 참여도 점수 계산 (0-100)

        가중평균:
        - Attention Score (40%)
        - Participation Score (40%)
        - Quiz Accuracy (20%)

        Args:
            attention_score: 주의집중도 (0-1)
            participation_score: 참여 점수 (0-100)
            quiz_accuracy: 정답률 (0-1)

        Returns:
            float: 종합 참여도 점수 (0-100)
        """
        overall = (
            (attention_score * 100) * 0.4
            + participation_score * 0.4
            + (quiz_accuracy * 100) * 0.2
        )

        return min(max(overall, 0.0), 100.0)

    # ============================================
    # Confusion Detection
    # ============================================

    def detect_confusion(
        self,
        quiz_accuracy: float,
        chat_activity_high: bool,
        confusion_indicators: List[str],
    ) -> Tuple[bool, float]:
        """
        혼동도 감지 (혼동 상태 여부 + 확신도)

        혼동 지표:
        1. 낮은 정답률 (< 70%) - 점수가 낮을수록 혼란도 높음
        2. 높은 채팅 활동 - 질문이 많음
        3. 명시적 혼동 지표 (반복 질문, 실수 패턴)

        Args:
            quiz_accuracy: 정답률 (0-1)
            chat_activity_high: 채팅 활동 많음 여부
            confusion_indicators: 혼동 지표 리스트

        Returns:
            (bool, float): (혼동 상태 여부, 확신도 0-1)
        """
        # 지표·채팅 신호가 전혀 없으면 혼동 없음으로 간주 (기본값 0.0)
        if not confusion_indicators and not chat_activity_high:
            return False, 0.0

        confidence = 0.0

        # 1. Quiz accuracy factor (점수가 낮을수록 혼란 가능성 높음)
        # 70% 미만일 때 혼란 신호로 판단
        if quiz_accuracy < 0.7:
            # 0% = 0.4 confidence, 70% = 0.0 confidence (선형 스케일)
            accuracy_factor = (0.7 - quiz_accuracy) / 0.7
            confidence += accuracy_factor * 0.4  # 최대 0.4

        # 2. Chat activity factor (질문이 많으면 혼란 신호)
        if chat_activity_high:
            confidence += 0.3  # 채팅 활동 높으면 +0.3 (강한 혼란 신호)

        # 3. Explicit confusion indicators (명시적 혼동 패턴)
        if confusion_indicators:
            # 각 지표당 0.1씩 추가 (최대 0.4)
            indicator_boost = min(len(confusion_indicators) * 0.1, 0.4)
            confidence += indicator_boost

        # Clamp confidence to [0, 1]
        confidence = min(max(confidence, 0.0), 1.0)

        # Decision threshold: > 0.5 = confused
        is_confused = confidence > 0.5

        return is_confused, confidence

    # ============================================
    # Engagement Trend Analysis
    # ============================================

    def analyze_trend(
        self,
        recent_scores: List[float],
        window_minutes: int = 10,
    ) -> Dict[str, Any]:
        """
        참여도 추세 분석 (최근 N분 기준)

        Args:
            recent_scores: 최근 참여도 점수들 (시간순)
            window_minutes: 분석 윈도우 (기본 10분)

        Returns:
            Dict: trend_direction, trend_strength 등
        """
        if len(recent_scores) < 2:
            return {
                "trend_direction": "stable",
                "trend_strength": 0.0,
                "average": recent_scores[-1] if recent_scores else 0.0,
            }

        # 선형 회귀로 추세 계산
        first_half_avg = sum(recent_scores[: len(recent_scores) // 2]) / max(
            len(recent_scores) // 2, 1
        )
        second_half_avg = sum(recent_scores[len(recent_scores) // 2 :]) / max(
            len(recent_scores) - len(recent_scores) // 2, 1
        )

        trend_direction = (
            "increasing" if second_half_avg > first_half_avg else "decreasing"
        )
        trend_strength = abs(second_half_avg - first_half_avg) / 100.0

        return {
            "trend_direction": trend_direction,
            "trend_strength": min(trend_strength, 1.0),
            "average": sum(recent_scores) / len(recent_scores),
            "recent": recent_scores[-1],
            "previous": recent_scores[-2] if len(recent_scores) >= 2 else None,
        }

    # ============================================
    # Score Interpretation
    # ============================================

    @staticmethod
    def interpret_engagement_level(score: float) -> Dict[str, Any]:
        """
        참여도 점수 해석

        Args:
            score: 참여도 점수 (0-100)

        Returns:
            Dict: level, description, recommendations
        """
        if score >= 80:
            return {
                "level": "excellent",
                "description": "학생이 매우 높은 참여도를 보이고 있습니다",
                "color": "green",
                "recommendations": ["지속적인 참여 유지", "심화 학습 제공 고려"],
            }
        elif score >= 60:
            return {
                "level": "good",
                "description": "학생이 양호한 참여도를 보이고 있습니다",
                "color": "blue",
                "recommendations": ["현재 상태 유지", "추가 과제 제시 고려"],
            }
        elif score >= 40:
            return {
                "level": "moderate",
                "description": "학생의 참여도가 보통 수준입니다",
                "color": "yellow",
                "recommendations": ["참여 독려", "개념 재설명", "개별 확인"],
            }
        else:
            return {
                "level": "low",
                "description": "학생의 참여도가 낮습니다",
                "color": "red",
                "recommendations": ["즉시 개입 필요", "일대일 상담", "과제 재설정"],
            }


class EngagementTracker:
    """실시간 학생 참여도 추적기"""

    def __init__(self, db_manager):
        """
        Args:
            db_manager: DatabaseManager 인스턴스
        """
        self.db_manager = db_manager
        self.calculator = EngagementCalculator()
        self.engagement_cache: Dict[
            str, StudentEngagement
        ] = {}  # {session_id:student_id: engagement}

        logger.info("📊 EngagementTracker initialized")

    async def track_activity(
        self,
        session_id: str,
        student_id: str,
        student_name: str,
        node_name: str,
        activity_type: ActivityType,
        activity_data: Dict,
    ) -> Optional[StudentEngagement]:
        """
        학생 활동 기록 및 참여도 업데이트

        Args:
            session_id: 세션 ID
            student_id: 학생 ID
            student_name: 학생 이름
            node_name: 노드 이름
            activity_type: 활동 타입 (CHAT, QUIZ_RESPONSE, PRESENCE)
            activity_data: 활동 데이터 (예: response_time_ms, is_correct 등)

        Returns:
            Optional[StudentEngagement]: 업데이트된 참여도 객체
        """
        try:
            # 기존 참여도 조회
            cache_key = f"{session_id}:{student_id}"
            engagement = self.engagement_cache.get(cache_key)

            if not engagement:
                # DB에서 조회
                engagements = await self.db_manager.get_session_engagement(session_id)
                for eng in engagements:
                    if eng.student_id == student_id:
                        engagement = eng
                        break

            if not engagement:
                # 새 참여도 객체 생성
                engagement = StudentEngagement(
                    session_id=session_id,
                    student_id=student_id,
                    student_name=student_name,
                    node_name=node_name,
                    metrics=EngagementMetrics(),
                    updated_at=datetime.now(UTC),
                )

            # 활동 타입별 처리
            if activity_type == ActivityType.CHAT:
                engagement.metrics.chat_message_count += 1

            elif activity_type == ActivityType.QUIZ_RESPONSE:
                engagement.metrics.participation_count += 1
                if "response_time_ms" in activity_data:
                    # 평균 응답 시간 계산
                    prev_latency = engagement.metrics.response_latency_ms
                    new_latency = activity_data["response_time_ms"]
                    engagement.metrics.response_latency_ms = int(
                        (prev_latency + new_latency) / 2
                    )

                if "is_correct" in activity_data:
                    # Quiz accuracy 업데이트
                    if activity_data["is_correct"]:
                        correct_count = int(
                            engagement.metrics.quiz_accuracy
                            * engagement.metrics.participation_count
                        )
                        correct_count += 1
                    else:
                        correct_count = int(
                            engagement.metrics.quiz_accuracy
                            * (engagement.metrics.participation_count - 1)
                        )

                    engagement.metrics.quiz_accuracy = (
                        correct_count / engagement.metrics.participation_count
                        if engagement.metrics.participation_count > 0
                        else 0.0
                    )

            elif activity_type == ActivityType.PRESENCE:
                # Screen time 기록 (별도 처리)
                pass

            # 마지막 활동 시간 업데이트
            engagement.metrics.last_activity_time = datetime.now(UTC)
            engagement.updated_at = datetime.now(UTC)

            # 캐시 업데이트
            self.engagement_cache[cache_key] = engagement

            # DB 저장
            await self.db_manager.update_student_engagement(engagement)

            logger.debug(
                f"✅ Engagement tracked: {student_id} ({activity_type}) - score: {engagement.metrics.quiz_accuracy:.2f}"
            )

            return engagement

        except Exception as e:
            logger.error(f"❌ Failed to track activity: {e}")
            return None

    async def calculate_session_engagement(
        self,
        session_id: str,
        session_duration_minutes: float,
    ) -> Dict[str, Any]:
        """
        세션 전체 참여도 통계 계산

        Args:
            session_id: 세션 ID
            session_duration_minutes: 세션 진행 시간

        Returns:
            Dict: 세션별 참여도 통계
        """
        try:
            engagements = await self.db_manager.get_session_engagement(session_id)

            if not engagements:
                return {
                    "session_id": session_id,
                    "total_students": 0,
                    "average_score": 0.0,
                    "students_by_level": {},
                }

            scores = []
            students_by_level = {"excellent": 0, "good": 0, "moderate": 0, "low": 0}

            for engagement in engagements:
                # 종합 점수 계산
                overall_score = self.calculator.calculate_overall_engagement_score(
                    attention_score=engagement.metrics.attention_score,
                    participation_score=self.calculator.calculate_participation_score(
                        engagement.metrics.chat_message_count,
                        engagement.metrics.participation_count,
                        session_duration_minutes,
                    ),
                    quiz_accuracy=engagement.metrics.quiz_accuracy,
                )

                scores.append(overall_score)

                # 레벨 분류
                interpretation = self.calculator.interpret_engagement_level(
                    overall_score
                )
                students_by_level[interpretation["level"]] += 1

            return {
                "session_id": session_id,
                "total_students": len(engagements),
                "average_score": sum(scores) / len(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0,
                "min_score": min(scores) if scores else 0.0,
                "students_by_level": students_by_level,
                "engagement_details": [
                    {
                        "student_id": eng.student_id,
                        "student_name": eng.student_name,
                        "score": scores[i],
                        "level": self.calculator.interpret_engagement_level(scores[i])[
                            "level"
                        ],
                    }
                    for i, eng in enumerate(engagements)
                ],
            }

        except Exception as e:
            logger.error(f"❌ Failed to calculate session engagement: {e}")
            return {}

    async def clear_cache(self):
        """캐시 초기화"""
        self.engagement_cache.clear()
        logger.info("🧹 Engagement cache cleared")


# 전역 인스턴스
engagement_tracker = None


async def init_engagement_tracker(db_manager) -> Optional[EngagementTracker]:
    """EngagementTracker 초기화"""
    global engagement_tracker

    try:
        engagement_tracker = EngagementTracker(db_manager)
        logger.info("✅ EngagementTracker initialized successfully")
        return engagement_tracker
    except Exception as e:
        logger.error(f"❌ Failed to initialize EngagementTracker: {e}")
        engagement_tracker = None
        return None


def get_engagement_tracker() -> Optional[EngagementTracker]:
    """EngagementTracker 인스턴스 반환"""
    return engagement_tracker
