"""
AIRClass AI Analysis Test Suite
Vision, NLP, and Feedback module tests
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import tempfile

# Import modules
from ai_vision import VisionAnalyzer, init_vision_analyzer, get_vision_analyzer
from ai_nlp import (
    NLPAnalyzer,
    init_nlp_analyzer,
    get_nlp_analyzer,
    SentimentType,
    IntentType,
)
from ai_feedback import (
    FeedbackGenerator,
    init_feedback_generator,
    get_feedback_generator,
    FeedbackType,
)


# ============================================
# Vision Analyzer Tests
# ============================================


class TestVisionAnalyzer:
    """VisionAnalyzer 테스트"""

    def setup_method(self):
        """테스트 전 설정"""
        self.analyzer = VisionAnalyzer()
        self.session_id = "test_session_001"

    def test_init_vision_analyzer(self):
        """VisionAnalyzer 초기화 테스트"""
        assert self.analyzer is not None
        assert isinstance(self.analyzer, VisionAnalyzer)

    def test_analyze_screenshot(self):
        """스크린샷 분석 테스트"""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            screenshot_path = f.name

        try:
            analysis = self.analyzer.analyze_screenshot(
                self.session_id, screenshot_path
            )

            assert analysis is not None
            assert analysis.analysis_id is not None
            assert analysis.session_id == self.session_id
            assert analysis.content_type in [
                "code",
                "quiz",
                "discussion",
                "diagram",
                "lecture",
            ]
            assert 0.0 <= analysis.complexity_score <= 1.0
            assert 0.0 <= analysis.engagement_potential <= 1.0
            assert len(analysis.recommendations) > 0

        finally:
            Path(screenshot_path).unlink(missing_ok=True)

    def test_extract_visual_elements(self):
        """시각적 요소 추출 테스트"""
        elements = self.analyzer._extract_visual_elements("dummy_path.jpg")

        assert isinstance(elements, list)
        assert len(elements) > 0
        for elem in elements:
            assert hasattr(elem, "type")
            assert hasattr(elem, "confidence")
            assert hasattr(elem, "bounds")

    def test_extract_text(self):
        """텍스트 추출 테스트"""
        text = self.analyzer._extract_text("dummy_path.jpg")

        assert isinstance(text, str)
        assert len(text) > 0

    def test_classify_content_type(self):
        """콘텐츠 타입 분류 테스트"""
        text = "def calculate_average(numbers): return sum(numbers) / len(numbers)"
        elements = self.analyzer._extract_visual_elements("dummy_path.jpg")

        content_type = self.analyzer._classify_content_type(elements, text)

        assert content_type in ["code", "quiz", "discussion", "diagram", "lecture"]

    def test_calculate_complexity(self):
        """복잡도 계산 테스트"""
        text = "고급 프로그래밍 개념에 대한 설명"
        elements = self.analyzer._extract_visual_elements("dummy_path.jpg")

        score = self.analyzer._calculate_complexity(elements, text, "code")

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_get_analysis(self):
        """분석 결과 조회 테스트"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            screenshot_path = f.name

        try:
            analysis = self.analyzer.analyze_screenshot(
                self.session_id, screenshot_path
            )
            retrieved = self.analyzer.get_analysis(analysis.analysis_id)

            assert retrieved is not None
            assert retrieved.analysis_id == analysis.analysis_id

        finally:
            Path(screenshot_path).unlink(missing_ok=True)

    def test_list_analyses(self):
        """분석 결과 목록 테스트"""
        analyses = self.analyzer.list_analyses(self.session_id)

        assert isinstance(analyses, list)


# ============================================
# NLP Analyzer Tests
# ============================================


class TestNLPAnalyzer:
    """NLPAnalyzer 테스트"""

    def setup_method(self):
        """테스트 전 설정"""
        self.analyzer = NLPAnalyzer()
        self.session_id = "test_session_001"

    def test_init_nlp_analyzer(self):
        """NLPAnalyzer 초기화 테스트"""
        assert self.analyzer is not None
        assert isinstance(self.analyzer, NLPAnalyzer)

    def test_analyze_message(self):
        """메시지 분석 테스트"""
        message = self.analyzer.analyze_message(
            session_id=self.session_id,
            message_id="msg_001",
            user_id="student_001",
            user_type="student",
            content="이게 뭐지?",
        )

        assert message is not None
        assert message.message_id == "msg_001"
        assert message.session_id == self.session_id
        assert isinstance(message.sentiment, SentimentType)
        assert isinstance(message.intent, IntentType)
        assert -1.0 <= message.sentiment_score <= 1.0
        assert 0.0 <= message.intent_confidence <= 1.0
        assert 0.0 <= message.quality_score <= 1.0

    def test_analyze_sentiment_positive(self):
        """긍정 감정 분석 테스트"""
        sentiment, score = self.analyzer._analyze_sentiment("정말 좋아요! 훌륭해요!")

        assert sentiment == SentimentType.POSITIVE
        assert score > 0.3

    def test_analyze_sentiment_negative(self):
        """부정 감정 분석 테스트"""
        sentiment, score = self.analyzer._analyze_sentiment("이건 너무 어렵고 안 돼요")

        assert sentiment == SentimentType.NEGATIVE
        assert score < -0.3

    def test_analyze_sentiment_confused(self):
        """혼란 감정 분석 테스트"""
        sentiment, score = self.analyzer._analyze_sentiment("뭐? 뭐지? 이건 뭐에요?")

        assert sentiment == SentimentType.CONFUSED

    def test_analyze_intent_question(self):
        """질문 의도 분석 테스트"""
        intent, confidence = self.analyzer._analyze_intent("이건 왜 이렇게 돼요?")

        assert intent == IntentType.QUESTION
        assert confidence > 0.8

    def test_analyze_intent_answer(self):
        """답변 의도 분석 테스트"""
        intent, confidence = self.analyzer._analyze_intent("네, 맞습니다")

        assert intent == IntentType.ANSWER
        assert confidence > 0.8

    def test_extract_keywords(self):
        """키워드 추출 테스트"""
        content = "파이썬의 함수와 데이터 구조에 대해 배우고 있습니다"
        tokens = self.analyzer._tokenize_and_analyze(content)

        keywords = self.analyzer._extract_keywords(tokens, content)

        assert isinstance(keywords, list)

    def test_summarize_conversation(self):
        """대화 요약 테스트"""
        # 여러 메시지 분석
        for i in range(3):
            self.analyzer.analyze_message(
                session_id=self.session_id,
                message_id=f"msg_{i:03d}",
                user_id=f"user_{i}",
                user_type="student" if i % 2 == 0 else "teacher",
                content=f"메시지 내용 {i}",
            )

        summary = self.analyzer.summarize_conversation(self.session_id)

        assert summary is not None
        assert summary.session_id == self.session_id
        assert isinstance(summary.main_topics, list)
        assert isinstance(summary.student_understanding_level, str)

    def test_get_message(self):
        """메시지 조회 테스트"""
        msg = self.analyzer.analyze_message(
            session_id=self.session_id,
            message_id="msg_test",
            user_id="user_test",
            user_type="student",
            content="테스트 메시지",
        )

        retrieved = self.analyzer.get_message("msg_test")

        assert retrieved is not None
        assert retrieved.message_id == "msg_test"


# ============================================
# Feedback Generator Tests
# ============================================


class TestFeedbackGenerator:
    """FeedbackGenerator 테스트"""

    def setup_method(self):
        """테스트 전 설정"""
        self.generator = FeedbackGenerator()
        self.session_id = "test_session_001"

    def test_init_feedback_generator(self):
        """FeedbackGenerator 초기화 테스트"""
        assert self.generator is not None
        assert isinstance(self.generator, FeedbackGenerator)

    def test_generate_student_feedback_correction(self):
        """오류 지적 피드백 생성 테스트"""
        feedback = self.generator.generate_student_feedback(
            session_id=self.session_id,
            student_id="student_001",
            topic="functions",
            content_analysis={},
            message_analysis={},
            performance_data={
                "is_correct": False,
                "response_time": 10,
                "attempt_count": 3,
            },
        )

        assert feedback is not None
        assert feedback.feedback_type == FeedbackType.CORRECTION
        assert len(feedback.message) > 0
        assert len(feedback.explanation) > 0
        assert len(feedback.examples) > 0

    def test_generate_student_feedback_encouragement(self):
        """격려 피드백 생성 테스트"""
        feedback = self.generator.generate_student_feedback(
            session_id=self.session_id,
            student_id="student_002",
            topic="data_structures",
            content_analysis={},
            message_analysis={},
            performance_data={
                "is_correct": True,
                "response_time": 15,
                "attempt_count": 2,
            },
        )

        assert feedback is not None
        assert feedback.feedback_type in [
            FeedbackType.ENCOURAGEMENT,
            FeedbackType.REINFORCEMENT,
        ]

    def test_generate_student_feedback_extension(self):
        """심화 피드백 생성 테스트"""
        feedback = self.generator.generate_student_feedback(
            session_id=self.session_id,
            student_id="student_003",
            topic="algorithms",
            content_analysis={},
            message_analysis={},
            performance_data={
                "is_correct": True,
                "response_time": 2,
                "attempt_count": 1,
            },
        )

        assert feedback is not None
        assert feedback.feedback_type == FeedbackType.EXTENSION

    def test_determine_priority(self):
        """우선순위 결정 테스트"""
        # 높은 우선순위
        priority = self.generator._determine_priority(
            FeedbackType.WARNING, {"attempt_count": 6}
        )
        assert priority.value in ["high", "critical"]

    def test_generate_teacher_insight(self):
        """교사 인사이트 생성 테스트"""
        insight = self.generator.generate_teacher_insight(
            session_id=self.session_id,
            class_data={"student_count": 20},
            message_analytics=[],
            performance_analytics={},
        )

        assert insight is not None
        assert insight.session_id == self.session_id
        assert insight.class_engagement_level in ["high", "medium", "low"]
        assert insight.average_understanding_level in [
            "excellent",
            "good",
            "fair",
            "poor",
        ]

    def test_recommend_resources(self):
        """학습 자료 추천 테스트"""
        resources = self.generator._recommend_resources(
            "functions", FeedbackType.CLARIFICATION
        )

        assert isinstance(resources, list)
        assert len(resources) > 0
        for resource in resources:
            assert "title" in resource
            assert "url" in resource
            assert "type" in resource

    def test_get_feedback(self):
        """피드백 조회 테스트"""
        feedback = self.generator.generate_student_feedback(
            session_id=self.session_id,
            student_id="student_test",
            topic="functions",
            content_analysis={},
            message_analysis={},
            performance_data={
                "is_correct": True,
                "response_time": 5,
                "attempt_count": 1,
            },
        )

        retrieved = self.generator.get_feedback(feedback.feedback_id)

        assert retrieved is not None
        assert retrieved.feedback_id == feedback.feedback_id


# ============================================
# Async Initialization Tests
# ============================================


class TestAsyncInitialization:
    """비동기 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_init_vision_analyzer_async(self):
        """VisionAnalyzer 비동기 초기화 테스트"""
        analyzer = await init_vision_analyzer()

        assert analyzer is not None
        assert isinstance(analyzer, VisionAnalyzer)

    @pytest.mark.asyncio
    async def test_init_nlp_analyzer_async(self):
        """NLPAnalyzer 비동기 초기화 테스트"""
        analyzer = await init_nlp_analyzer()

        assert analyzer is not None
        assert isinstance(analyzer, NLPAnalyzer)

    @pytest.mark.asyncio
    async def test_init_feedback_generator_async(self):
        """FeedbackGenerator 비동기 초기화 테스트"""
        generator = await init_feedback_generator()

        assert generator is not None
        assert isinstance(generator, FeedbackGenerator)


# ============================================
# Integration Tests
# ============================================


class TestIntegration:
    """통합 테스트"""

    def setup_method(self):
        """테스트 전 설정"""
        self.session_id = "integration_test_session"
        self.vision = VisionAnalyzer()
        self.nlp = NLPAnalyzer()
        self.feedback = FeedbackGenerator()

    def test_full_workflow(self):
        """전체 워크플로우 테스트"""
        # 1. 메시지 분석
        message = self.nlp.analyze_message(
            session_id=self.session_id,
            message_id="msg_001",
            user_id="student_001",
            user_type="student",
            content="이 함수가 뭐에요?",
        )

        assert message.intent == IntentType.QUESTION

        # 2. 피드백 생성
        feedback = self.feedback.generate_student_feedback(
            session_id=self.session_id,
            student_id="student_001",
            topic="functions",
            content_analysis={"topic": "functions"},
            message_analysis={"learning_indicator": "confused"},
            performance_data={
                "is_correct": False,
                "response_time": 30,
                "attempt_count": 1,
            },
        )

        assert feedback.feedback_type == FeedbackType.CLARIFICATION
        assert len(feedback.resources) > 0

    def test_multi_message_analysis(self):
        """다중 메시지 분석 테스트"""
        messages = ["이게 맞나요?", "네, 맞습니다", "아, 그렇군요", "더 알고 싶어요"]

        for i, msg_content in enumerate(messages):
            message = self.nlp.analyze_message(
                session_id=self.session_id,
                message_id=f"msg_{i:03d}",
                user_id=f"user_{i % 2}",
                user_type="student" if i % 2 == 0 else "teacher",
                content=msg_content,
            )

            assert message is not None
            assert message.intent is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
