"""
AIRClass Feedback Generation Module
AI 기반 학생 피드백 및 교사 인사이트 생성
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """피드백 타입"""

    CORRECTION = "correction"  # 오류 지적
    ENCOURAGEMENT = "encouragement"  # 격려
    CLARIFICATION = "clarification"  # 명확화
    EXTENSION = "extension"  # 심화 학습
    REINFORCEMENT = "reinforcement"  # 강화
    WARNING = "warning"  # 주의


class PriorityLevel(str, Enum):
    """우선순위"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class StudentFeedback:
    """학생 피드백"""

    feedback_id: str
    session_id: str
    student_id: str
    topic: str
    feedback_type: FeedbackType
    message: str
    explanation: str  # 상세 설명
    examples: List[str]  # 예시 또는 참고자료
    resources: List[Dict]  # 추천 학습 자료 {"title": "...", "url": "..."}
    timestamp: str
    priority: PriorityLevel


@dataclass
class TeacherInsight:
    """교사 인사이트"""

    insight_id: str
    session_id: str

    # 전체 클래스 지표
    class_engagement_level: str  # "high", "medium", "low"
    average_understanding_level: str  # "excellent", "good", "fair", "poor"
    class_sentiment: str  # "positive", "neutral", "negative"

    # 주의 필요 학생들
    struggling_students: List[
        Dict
    ]  # {"student_id": "...", "topics": [...], "priority": ...}
    high_performers: List[str]  # 우수 학생 ID 목록

    # 학습 흐름 분석
    pacing_assessment: str  # "too_fast", "appropriate", "too_slow"
    engagement_peaks: List[Dict]  # {"time": "...", "event": "...", "engagement": 0.8}

    # 콘텐츠 효율성
    most_confusing_topics: List[str]  # 학생들이 가장 어려워하는 주제
    well_understood_topics: List[str]  # 잘 이해된 주제

    # 교사 추천
    recommendations: List[str]

    timestamp: str


@dataclass
class GroupFeedback:
    """그룹 피드백"""

    group_id: str
    session_id: str
    group_size: int
    focus_topic: str

    # 그룹 수행도
    group_performance: str  # "excellent", "good", "fair", "poor"
    collaboration_quality: str  # "excellent", "good", "fair", "poor"

    # 그룹 내 문제
    issues: List[str]

    # 추천사항
    recommendations: List[str]

    timestamp: str


class FeedbackGenerator:
    """피드백 생성기"""

    def __init__(self):
        """초기화"""
        self.feedback_cache: Dict[str, StudentFeedback] = {}
        self.insight_cache: Dict[str, TeacherInsight] = {}
        self.group_feedback_cache: Dict[str, GroupFeedback] = {}

        logger.info("📝 FeedbackGenerator initialized")

    def generate_student_feedback(
        self,
        session_id: str,
        student_id: str,
        topic: str,
        content_analysis: Dict,
        message_analysis: Dict,
        performance_data: Dict,
    ) -> StudentFeedback:
        """
        학생 피드백 생성

        Args:
            session_id: 세션 ID
            student_id: 학생 ID
            topic: 주제
            content_analysis: 콘텐츠 분석 데이터
            message_analysis: 메시지 분석 데이터
            performance_data: 성과 데이터 (점수, 응답 시간 등)

        Returns:
            StudentFeedback: 생성된 피드백
        """
        try:
            feedback_id = f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 1. 피드백 타입 결정
            feedback_type = self._determine_feedback_type(
                message_analysis, performance_data
            )

            # 2. 피드백 메시지 생성
            message = self._generate_feedback_message(
                feedback_type, topic, message_analysis, performance_data
            )

            # 3. 상세 설명 생성
            explanation = self._generate_explanation(
                feedback_type, topic, content_analysis
            )

            # 4. 예시 생성
            examples = self._generate_examples(topic, feedback_type)

            # 5. 학습 자료 추천
            resources = self._recommend_resources(topic, feedback_type)

            # 6. 우선순위 결정
            priority = self._determine_priority(feedback_type, performance_data)

            feedback = StudentFeedback(
                feedback_id=feedback_id,
                session_id=session_id,
                student_id=student_id,
                topic=topic,
                feedback_type=feedback_type,
                message=message,
                explanation=explanation,
                examples=examples,
                resources=resources,
                timestamp=datetime.now().isoformat(),
                priority=priority,
            )

            self.feedback_cache[feedback_id] = feedback

            logger.info(f"✅ Student feedback generated: {feedback_id}")
            return feedback

        except Exception as e:
            logger.error(f"❌ Failed to generate student feedback: {e}")
            raise

    def _determine_feedback_type(
        self, message_analysis: Dict, performance_data: Dict
    ) -> FeedbackType:
        """피드백 타입 결정"""
        try:
            # 성능 데이터 확인
            is_correct = performance_data.get("is_correct", False)
            response_time = performance_data.get("response_time", 0)
            attempt_count = performance_data.get("attempt_count", 1)

            # 학생 감정 확인
            sentiment = message_analysis.get("sentiment", "neutral")
            is_confused = message_analysis.get("learning_indicator") == "confused"

            # 타입 결정 로직
            if not is_correct and attempt_count > 2:
                return FeedbackType.CORRECTION  # 오류 지적
            elif is_confused:
                return FeedbackType.CLARIFICATION  # 명확화
            elif is_correct and response_time < 5:  # 빠른 정답
                return FeedbackType.EXTENSION  # 심화
            elif is_correct:
                return FeedbackType.REINFORCEMENT  # 강화
            elif response_time > 30:  # 너무 오래 걸림
                return FeedbackType.WARNING  # 주의
            else:
                return FeedbackType.ENCOURAGEMENT  # 격려

        except Exception as e:
            logger.warning(f"⚠️ Failed to determine feedback type: {e}")
            return FeedbackType.ENCOURAGEMENT

    def _generate_feedback_message(
        self,
        feedback_type: FeedbackType,
        topic: str,
        message_analysis: Dict,
        performance_data: Dict,
    ) -> str:
        """피드백 메시지 생성"""
        try:
            messages = {
                FeedbackType.CORRECTION: f"'{topic}' 관련 오류를 찾았습니다. 다시 한 번 검토해주세요.",
                FeedbackType.ENCOURAGEMENT: f"좋은 시도입니다! '{topic}'에 대해 계속 학습하면 더 좋아질 거예요.",
                FeedbackType.CLARIFICATION: f"'{topic}'이 어렵게 느껴지나요? 다시 설명해드릴게요.",
                FeedbackType.EXTENSION: f"완벽합니다! '{topic}'에 대한 심화 학습을 시도해볼까요?",
                FeedbackType.REINFORCEMENT: f"'{topic}'을 잘 이해하셨네요! 다른 관련 문제도 풀어보세요.",
                FeedbackType.WARNING: f"'{topic}'에 시간이 오래 걸렸습니다. 개념을 정확히 이해했는지 확인해주세요.",
            }
            return messages.get(feedback_type, "피드백입니다.")

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate feedback message: {e}")
            return "학습을 계속해주세요."

    def _generate_explanation(
        self, feedback_type: FeedbackType, topic: str, content_analysis: Dict
    ) -> str:
        """상세 설명 생성"""
        try:
            base_explanation = f"'{topic}'에 관해서 다음을 고려해보세요:\n"

            if feedback_type == FeedbackType.CORRECTION:
                return (
                    base_explanation
                    + f"- 정답의 핵심은 '{topic}'의 정의를 정확히 적용하는 것입니다.\n- 예시를 통해 다시 학습해보세요.\n- 유사한 문제 10개를 추가로 풀어보는 것을 권장합니다."
                )

            elif feedback_type == FeedbackType.CLARIFICATION:
                return (
                    base_explanation
                    + f"- '{topic}'의 기본 개념부터 차근차근 설명하겠습니다.\n- 이전 수업의 선행 개념을 먼저 복습해보세요.\n- 더 자세한 설명 영상을 참고하세요."
                )

            elif feedback_type == FeedbackType.EXTENSION:
                return (
                    base_explanation
                    + f"- '{topic}'에서 한 단계 더 나아가 고급 응용을 배워보세요.\n- 실제 프로젝트에서 이를 어떻게 사용하는지 살펴보세요.\n- 관련된 심화 주제를 탐구해보세요."
                )

            elif feedback_type == FeedbackType.REINFORCEMENT:
                return (
                    base_explanation
                    + f"- '{topic}'의 다양한 변형 문제를 풀어보세요.\n- 다른 학생에게 이 개념을 설명해보세요.\n- 실제 예시에 적용해보세요."
                )

            else:
                return (
                    base_explanation
                    + "- 기본 개념을 다시 한 번 정리해보세요.\n- 천천히 접근해보세요.\n- 필요하면 도움을 요청하세요."
                )

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate explanation: {e}")
            return "더 자세한 학습이 필요합니다."

    def _generate_examples(self, topic: str, feedback_type: FeedbackType) -> List[str]:
        """예시 생성"""
        try:
            examples = {
                "functions": [
                    "def greet(name): return f'Hello {name}'",
                    "def add(a, b): return a + b",
                    "def calculate_average(numbers): return sum(numbers) / len(numbers)",
                ],
                "data_structures": [
                    "students = ['Alice', 'Bob', 'Charlie']",
                    "student_scores = {'Alice': 85, 'Bob': 90}",
                    "matrix = [[1, 2], [3, 4]]",
                ],
                "algorithms": [
                    "정렬: 배열을 오름차순으로 정렬",
                    "탐색: 배열에서 원하는 값 찾기",
                    "재귀: 자신을 호출하는 함수",
                ],
            }
            return examples.get(topic, ["더 많은 예시는 학습 자료에서 확인하세요"])[:3]

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate examples: {e}")
            return []

    def _recommend_resources(
        self, topic: str, feedback_type: FeedbackType
    ) -> List[Dict]:
        """학습 자료 추천"""
        try:
            resources = [
                {
                    "title": f"{topic} 기초 가이드",
                    "url": f"/resources/{topic}/basics",
                    "type": "guide",
                },
                {
                    "title": f"{topic} 실습 문제",
                    "url": f"/resources/{topic}/exercises",
                    "type": "exercises",
                },
                {
                    "title": f"{topic} 설명 영상",
                    "url": f"/resources/{topic}/video",
                    "type": "video",
                },
            ]

            if feedback_type == FeedbackType.EXTENSION:
                resources.append(
                    {
                        "title": f"{topic} 심화 강좌",
                        "url": f"/resources/{topic}/advanced",
                        "type": "advanced",
                    }
                )

            return resources

        except Exception as e:
            logger.warning(f"⚠️ Failed to recommend resources: {e}")
            return []

    def _determine_priority(
        self, feedback_type: FeedbackType, performance_data: Dict
    ) -> PriorityLevel:
        """우선순위 결정"""
        try:
            attempt_count = performance_data.get("attempt_count", 1)

            if feedback_type == FeedbackType.WARNING or attempt_count > 5:
                return PriorityLevel.CRITICAL
            elif feedback_type == FeedbackType.CORRECTION or attempt_count > 2:
                return PriorityLevel.HIGH
            elif feedback_type == FeedbackType.CLARIFICATION:
                return PriorityLevel.MEDIUM
            else:
                return PriorityLevel.LOW

        except Exception as e:
            logger.warning(f"⚠️ Failed to determine priority: {e}")
            return PriorityLevel.MEDIUM

    def generate_teacher_insight(
        self,
        session_id: str,
        class_data: Dict,
        message_analytics: List[Dict],
        performance_analytics: Dict,
    ) -> TeacherInsight:
        """
        교사 인사이트 생성

        Args:
            session_id: 세션 ID
            class_data: 클래스 데이터
            message_analytics: 메시지 분석 목록
            performance_analytics: 성과 분석

        Returns:
            TeacherInsight: 교사 인사이트
        """
        try:
            insight_id = (
                f"insight_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            # 클래스 참여도 평가
            engagement_level = self._evaluate_class_engagement(message_analytics)

            # 평균 이해도 평가
            understanding_level = self._evaluate_class_understanding(message_analytics)

            # 클래스 감정 분석
            sentiment = self._analyze_class_sentiment(message_analytics)

            # 주의 필요 학생 식별
            struggling_students = self._identify_struggling_students(
                message_analytics, performance_analytics
            )

            # 우수 학생 식별
            high_performers = self._identify_high_performers(message_analytics)

            # 진도 평가
            pacing = self._assess_pacing(message_analytics)

            # 참여 피크 분석
            engagement_peaks = self._analyze_engagement_peaks(message_analytics)

            # 혼란스러운 주제 식별
            confusing_topics = self._identify_confusing_topics(message_analytics)

            # 잘 이해된 주제 식별
            well_understood = self._identify_well_understood_topics(message_analytics)

            # 교사 추천사항
            recommendations = self._generate_teacher_recommendations(
                struggling_students, confusing_topics, pacing
            )

            insight = TeacherInsight(
                insight_id=insight_id,
                session_id=session_id,
                class_engagement_level=engagement_level,
                average_understanding_level=understanding_level,
                class_sentiment=sentiment,
                struggling_students=struggling_students,
                high_performers=high_performers,
                pacing_assessment=pacing,
                engagement_peaks=engagement_peaks,
                most_confusing_topics=confusing_topics,
                well_understood_topics=well_understood,
                recommendations=recommendations,
                timestamp=datetime.now().isoformat(),
            )

            self.insight_cache[insight_id] = insight

            logger.info(f"✅ Teacher insight generated: {insight_id}")
            return insight

        except Exception as e:
            logger.error(f"❌ Failed to generate teacher insight: {e}")
            raise

    def _evaluate_class_engagement(self, message_analytics: List[Dict]) -> str:
        """클래스 참여도 평가"""
        try:
            if not message_analytics:
                return "low"

            message_count = len(message_analytics)
            question_count = sum(
                1 for m in message_analytics if m.get("intent") == "question"
            )

            participation_rate = (
                question_count / len(message_analytics) if message_analytics else 0
            )

            if participation_rate > 0.4 and message_count > 50:
                return "high"
            elif participation_rate > 0.2 or message_count > 20:
                return "medium"
            else:
                return "low"

        except Exception as e:
            logger.warning(f"⚠️ Failed to evaluate engagement: {e}")
            return "medium"

    def _evaluate_class_understanding(self, message_analytics: List[Dict]) -> str:
        """평균 이해도 평가"""
        try:
            if not message_analytics:
                return "fair"

            confusion_count = sum(
                1
                for m in message_analytics
                if m.get("learning_indicator") == "confused"
            )
            understanding_count = sum(
                1
                for m in message_analytics
                if m.get("learning_indicator") == "understands"
            )

            ratio = (
                understanding_count / len(message_analytics) if message_analytics else 0
            )
            confusion_ratio = (
                confusion_count / len(message_analytics) if message_analytics else 0
            )

            if ratio > 0.6:
                return "excellent"
            elif ratio > 0.4:
                return "good"
            elif confusion_ratio < 0.3:
                return "fair"
            else:
                return "poor"

        except Exception as e:
            logger.warning(f"⚠️ Failed to evaluate understanding: {e}")
            return "fair"

    def _analyze_class_sentiment(self, message_analytics: List[Dict]) -> str:
        """클래스 감정 분석"""
        try:
            if not message_analytics:
                return "neutral"

            positive_count = sum(
                1 for m in message_analytics if m.get("sentiment") == "positive"
            )
            negative_count = sum(
                1 for m in message_analytics if m.get("sentiment") == "negative"
            )

            if positive_count > len(message_analytics) * 0.5:
                return "positive"
            elif negative_count > len(message_analytics) * 0.3:
                return "negative"
            else:
                return "neutral"

        except Exception as e:
            logger.warning(f"⚠️ Failed to analyze sentiment: {e}")
            return "neutral"

    def _identify_struggling_students(
        self, message_analytics: List[Dict], performance_analytics: Dict
    ) -> List[Dict]:
        """주의 필요 학생 식별"""
        try:
            struggling = {}

            for msg in message_analytics:
                student_id = msg.get("user_id", "unknown")

                if student_id not in struggling:
                    struggling[student_id] = {
                        "student_id": student_id,
                        "topics": [],
                        "confusion_count": 0,
                    }

                if msg.get("learning_indicator") == "confused":
                    struggling[student_id]["confusion_count"] += 1
                    keywords = msg.get("keywords", [])
                    struggling[student_id]["topics"].extend(keywords)

            # 혼란도가 높은 학생만 반환
            result = [s for s in struggling.values() if s["confusion_count"] > 2]

            for student in result:
                student["topics"] = list(set(student["topics"]))[:3]
                student["priority"] = (
                    "high" if student["confusion_count"] > 5 else "medium"
                )

            return result[:10]

        except Exception as e:
            logger.warning(f"⚠️ Failed to identify struggling students: {e}")
            return []

    def _identify_high_performers(self, message_analytics: List[Dict]) -> List[str]:
        """우수 학생 식별"""
        try:
            student_quality = {}

            for msg in message_analytics:
                student_id = msg.get("user_id", "unknown")
                quality = msg.get("quality_score", 0.5)

                if student_id not in student_quality:
                    student_quality[student_id] = {"count": 0, "total": 0}

                student_quality[student_id]["total"] += quality
                student_quality[student_id]["count"] += 1

            # 평균 품질이 0.7 이상인 학생
            high_performers = [
                sid
                for sid, data in student_quality.items()
                if data["count"] >= 2 and data["total"] / data["count"] > 0.7
            ]

            return high_performers[:5]

        except Exception as e:
            logger.warning(f"⚠️ Failed to identify high performers: {e}")
            return []

    def _assess_pacing(self, message_analytics: List[Dict]) -> str:
        """진도 평가"""
        try:
            if not message_analytics:
                return "appropriate"

            confusion_count = sum(
                1
                for m in message_analytics
                if m.get("learning_indicator") == "confused"
            )
            confusion_ratio = confusion_count / len(message_analytics)

            if confusion_ratio > 0.5:
                return "too_fast"
            elif confusion_ratio < 0.1 and len(message_analytics) < 20:
                return "too_slow"
            else:
                return "appropriate"

        except Exception as e:
            logger.warning(f"⚠️ Failed to assess pacing: {e}")
            return "appropriate"

    def _analyze_engagement_peaks(self, message_analytics: List[Dict]) -> List[Dict]:
        """참여 피크 분석"""
        try:
            peaks = []

            # 메시지 활동 피크 식별
            for i, msg in enumerate(message_analytics):
                if (
                    msg.get("intent") == "question"
                    and msg.get("quality_score", 0) > 0.7
                ):
                    peaks.append(
                        {
                            "time": msg.get("timestamp", ""),
                            "event": "high_quality_question",
                            "engagement": min(msg.get("quality_score", 0.5) + 0.2, 1.0),
                        }
                    )

            return peaks[:5]

        except Exception as e:
            logger.warning(f"⚠️ Failed to analyze engagement peaks: {e}")
            return []

    def _identify_confusing_topics(self, message_analytics: List[Dict]) -> List[str]:
        """혼란스러운 주제 식별"""
        try:
            topic_confusion = {}

            for msg in message_analytics:
                if msg.get("learning_indicator") == "confused":
                    keywords = msg.get("keywords", [])
                    for keyword in keywords:
                        topic_confusion[keyword] = topic_confusion.get(keyword, 0) + 1

            # 혼란 횟수가 많은 주제순 정렬
            sorted_topics = sorted(
                topic_confusion.items(), key=lambda x: x[1], reverse=True
            )

            return [topic for topic, count in sorted_topics[:5]]

        except Exception as e:
            logger.warning(f"⚠️ Failed to identify confusing topics: {e}")
            return []

    def _identify_well_understood_topics(
        self, message_analytics: List[Dict]
    ) -> List[str]:
        """잘 이해된 주제 식별"""
        try:
            topic_understanding = {}

            for msg in message_analytics:
                if msg.get("learning_indicator") == "understands":
                    keywords = msg.get("keywords", [])
                    for keyword in keywords:
                        topic_understanding[keyword] = (
                            topic_understanding.get(keyword, 0) + 1
                        )

            sorted_topics = sorted(
                topic_understanding.items(), key=lambda x: x[1], reverse=True
            )

            return [topic for topic, count in sorted_topics[:5]]

        except Exception as e:
            logger.warning(f"⚠️ Failed to identify well understood topics: {e}")
            return []

    def _generate_teacher_recommendations(
        self, struggling_students: List[Dict], confusing_topics: List[str], pacing: str
    ) -> List[str]:
        """교사 추천사항 생성"""
        try:
            recommendations = []

            if struggling_students:
                recommendations.append(
                    f"{len(struggling_students)}명의 학생이 추가 지원이 필요합니다. 개별 피드백을 제공해주세요."
                )

            if confusing_topics:
                recommendations.append(
                    f"'{confusing_topics[0]}'이(가) 학생들에게 어렵습니다. 다음 수업에서 이 부분을 다시 설명해주세요."
                )

            if pacing == "too_fast":
                recommendations.append(
                    "진도가 빨라 보입니다. 더 많은 예시와 연습 시간을 확보해주세요."
                )
            elif pacing == "too_slow":
                recommendations.append(
                    "진도를 조금 더 빠르게 가도 괜찮을 것 같습니다. 심화 내용을 추가해보세요."
                )

            return (
                recommendations
                if recommendations
                else ["다음 수업을 위해 현재 진행 상황을 검토해주세요."]
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate recommendations: {e}")
            return []

    def get_feedback(self, feedback_id: str) -> Optional[StudentFeedback]:
        """피드백 조회"""
        return self.feedback_cache.get(feedback_id)

    def get_insight(self, insight_id: str) -> Optional[TeacherInsight]:
        """인사이트 조회"""
        return self.insight_cache.get(insight_id)


# 전역 인스턴스
_feedback_generator = None


async def init_feedback_generator() -> FeedbackGenerator:
    """FeedbackGenerator 초기화"""
    global _feedback_generator

    try:
        _feedback_generator = FeedbackGenerator()
        logger.info("✅ FeedbackGenerator initialized successfully")
        return _feedback_generator

    except Exception as e:
        logger.error(f"❌ Failed to initialize FeedbackGenerator: {e}")
        raise


def get_feedback_generator() -> Optional[FeedbackGenerator]:
    """FeedbackGenerator 인스턴스 반환"""
    return _feedback_generator
