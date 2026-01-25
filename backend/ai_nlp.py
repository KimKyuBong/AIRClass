"""
AIRClass NLP Module
채팅 및 음성 내용의 자연어 처리
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentType(str, Enum):
    """감정 타입"""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CONFUSED = "confused"


class IntentType(str, Enum):
    """사용자 의도"""

    QUESTION = "question"
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    OPINION = "opinion"
    GREETING = "greeting"
    FEEDBACK = "feedback"
    OTHER = "other"


@dataclass
class TokenAnalysis:
    """토큰 분석 결과"""

    token: str
    part_of_speech: str  # "NOUN", "VERB", "ADJ", etc.
    lemma: str
    entity_type: Optional[str] = None  # NER: "PERSON", "ORG", "CONCEPT", etc.


@dataclass
class ChatMessage:
    """채팅 메시지 분석"""

    message_id: str
    session_id: str
    user_id: str
    user_type: str  # "teacher", "student"
    content: str
    timestamp: str

    # 감정 분석
    sentiment: SentimentType
    sentiment_score: float  # -1.0 (negative) to 1.0 (positive)

    # 의도 분석
    intent: IntentType
    intent_confidence: float  # 0.0-1.0

    # 언어 분석
    language: str  # "ko", "en", etc.
    tokens: List[TokenAnalysis]
    keywords: List[str]  # 주요 키워드
    entities: List[Dict]  # 명명된 엔티티

    # 교육적 분석
    learning_indicator: Optional[
        str
    ]  # "understands", "confused", "asking_deep_question"
    topic_relevance: float  # 0.0-1.0
    response_required: bool  # 교사 응답 필요 여부

    # 메타데이터
    quality_score: float  # 0.0-1.0 (학습에 도움이 되는 정도)


@dataclass
class ConversationSummary:
    """대화 요약"""

    session_id: str
    summary: str
    main_topics: List[str]
    key_questions: List[str]
    student_understanding_level: str  # "excellent", "good", "fair", "poor"
    engagement_level: str  # "high", "medium", "low"
    areas_needing_review: List[str]


class NLPAnalyzer:
    """자연어 처리 분석기"""

    def __init__(self):
        """초기화"""
        self.message_cache: Dict[str, ChatMessage] = {}
        self.conversation_history: Dict[str, List[ChatMessage]] = {}

        # 키워드 데이터베이스 (실제로는 더 큼)
        self.keywords_by_topic = {
            "functions": ["def", "함수", "function", "parameter", "return", "호출"],
            "data_structures": ["list", "dict", "array", "배열", "자료구조", "배열"],
            "algorithms": [
                "algorithm",
                "알고리즘",
                "loop",
                "반복",
                "recursive",
                "정렬",
            ],
            "web": ["html", "css", "javascript", "웹", "서버", "클라이언트"],
            "database": ["database", "sql", "mongodb", "데이터베이스", "쿼리"],
        }

        logger.info("🗣️ NLPAnalyzer initialized")

    def analyze_message(
        self,
        session_id: str,
        message_id: str,
        user_id: str,
        user_type: str,
        content: str,
    ) -> ChatMessage:
        """
        채팅 메시지 분석

        Args:
            session_id: 세션 ID
            message_id: 메시지 ID
            user_id: 사용자 ID
            user_type: 사용자 타입 (teacher, student)
            content: 메시지 내용

        Returns:
            ChatMessage: 분석된 메시지
        """
        try:
            # 1. 기본 처리
            content_lower = content.lower()

            # 2. 감정 분석
            sentiment, sentiment_score = self._analyze_sentiment(content)

            # 3. 의도 분석
            intent, intent_confidence = self._analyze_intent(content)

            # 4. 토큰화 및 분석
            tokens = self._tokenize_and_analyze(content)

            # 5. 키워드 추출
            keywords = self._extract_keywords(tokens, content)

            # 6. 엔티티 인식
            entities = self._extract_entities(tokens)

            # 7. 언어 감지
            language = self._detect_language(content)

            # 8. 학습 지표 분석
            learning_indicator = self._identify_learning_indicator(
                content, sentiment, intent
            )

            # 9. 주제 관련성 계산
            topic_relevance = self._calculate_topic_relevance(keywords, content)

            # 10. 교사 응답 필요 여부
            response_required = self._evaluate_response_required(
                intent, user_type, sentiment
            )

            # 11. 품질 점수
            quality_score = self._calculate_quality_score(
                intent, sentiment_score, topic_relevance
            )

            # 메시지 생성
            message = ChatMessage(
                message_id=message_id,
                session_id=session_id,
                user_id=user_id,
                user_type=user_type,
                content=content,
                timestamp=datetime.now().isoformat(),
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                intent=intent,
                intent_confidence=intent_confidence,
                language=language,
                tokens=tokens,
                keywords=keywords,
                entities=entities,
                learning_indicator=learning_indicator,
                topic_relevance=topic_relevance,
                response_required=response_required,
                quality_score=quality_score,
            )

            # 캐시에 저장
            self.message_cache[message_id] = message

            # 대화 히스토리 추가
            if session_id not in self.conversation_history:
                self.conversation_history[session_id] = []
            self.conversation_history[session_id].append(message)

            logger.info(f"✅ Message analyzed: {message_id}")
            return message

        except Exception as e:
            logger.error(f"❌ Failed to analyze message: {e}")
            raise

    def _analyze_sentiment(self, content: str) -> Tuple[SentimentType, float]:
        """감정 분석"""
        try:
            # 실제 구현에서는 감정 분석 모델 사용 (VADER, BERT 등)
            content_lower = content.lower()

            positive_words = [
                "좋다",
                "좋아",
                "훌륭하다",
                "excellent",
                "great",
                "good",
                "완벽",
                "좋은",
                "감사",
            ]
            negative_words = [
                "싫다",
                "싫어",
                "나쁘다",
                "못",
                "안",
                "어렵다",
                "모르겠다",
                "이상하다",
            ]
            confused_words = [
                "뭐",
                "뭔데",
                "뭐지",
                "이게",
                "모르",
                "이해",
                "어떻게",
                "왜",
            ]

            pos_count = sum(1 for word in positive_words if word in content_lower)
            neg_count = sum(1 for word in negative_words if word in content_lower)
            conf_count = sum(1 for word in confused_words if word in content_lower)

            if conf_count > 0:
                return SentimentType.CONFUSED, -0.3
            elif pos_count > neg_count:
                score = min(0.3 + (pos_count * 0.1), 1.0)
                return SentimentType.POSITIVE, score
            elif neg_count > pos_count:
                score = max(-0.3 - (neg_count * 0.1), -1.0)
                return SentimentType.NEGATIVE, score
            else:
                return SentimentType.NEUTRAL, 0.0

        except Exception as e:
            logger.warning(f"⚠️ Sentiment analysis failed: {e}")
            return SentimentType.NEUTRAL, 0.0

    def _analyze_intent(self, content: str) -> Tuple[IntentType, float]:
        """의도 분석"""
        try:
            content_lower = content.lower()

            # 질문 감지
            if "?" in content or any(
                w in content_lower
                for w in ["뭐", "뭐야", "무엇", "어떻게", "왜", "언제", "어디", "누가"]
            ):
                return IntentType.QUESTION, 0.9

            # 답변 패턴 (숫자, 예/아니오 등)
            if any(
                w in content_lower
                for w in ["네", "아니요", "맞다", "그렇다", "답", "정답"]
            ):
                return IntentType.ANSWER, 0.85

            # 명확히 요청 ("다시 설명해주세요")
            if any(
                w in content_lower for w in ["다시", "설명", "명확", "다시", "설명해"]
            ):
                return IntentType.CLARIFICATION, 0.8

            # 의견 ("생각", "의견", "나는")
            if any(
                w in content_lower for w in ["생각", "의견", "나는", "내 생각", "저는"]
            ):
                return IntentType.OPINION, 0.75

            # 인사말
            if any(
                w in content_lower
                for w in ["안녕", "안녕하세요", "hi", "hello", "좋아"]
            ):
                return IntentType.GREETING, 0.95

            # 피드백
            if any(
                w in content_lower for w in ["의견", "제안", "좋다", "싫다", "피드백"]
            ):
                return IntentType.FEEDBACK, 0.7

            return IntentType.OTHER, 0.5

        except Exception as e:
            logger.warning(f"⚠️ Intent analysis failed: {e}")
            return IntentType.OTHER, 0.5

    def _tokenize_and_analyze(self, content: str) -> List[TokenAnalysis]:
        """토큰화 및 분석"""
        try:
            # 실제 구현에서는 KoNLPy, spaCy 등을 사용
            # 현재는 간단한 토크나이저 사용
            tokens = content.split()
            analyzed = []

            for token in tokens[:20]:  # 처음 20개만
                analysis = TokenAnalysis(
                    token=token,
                    part_of_speech="NOUN",  # 모의 값
                    lemma=token.lower(),
                    entity_type=None,
                )
                analyzed.append(analysis)

            return analyzed

        except Exception as e:
            logger.warning(f"⚠️ Tokenization failed: {e}")
            return []

    def _extract_keywords(self, tokens: List[TokenAnalysis], content: str) -> List[str]:
        """키워드 추출"""
        try:
            keywords = []
            content_lower = content.lower()

            # 주제별 키워드 매칭
            for topic, keywords_list in self.keywords_by_topic.items():
                for keyword in keywords_list:
                    if keyword.lower() in content_lower:
                        keywords.append(keyword)

            # 중복 제거 및 상위 5개만
            return list(set(keywords))[:5]

        except Exception as e:
            logger.warning(f"⚠️ Keyword extraction failed: {e}")
            return []

    def _extract_entities(self, tokens: List[TokenAnalysis]) -> List[Dict]:
        """엔티티 추출 (NER)"""
        try:
            # 실제 구현에서는 NER 모델 사용
            entities = []

            # 개념 기반 엔티티 감지 (모의)
            concept_keywords = ["함수", "데이터", "알고리즘", "변수"]

            for token in tokens:
                if token.token in concept_keywords:
                    entities.append(
                        {"text": token.token, "type": "CONCEPT", "confidence": 0.8}
                    )

            return entities

        except Exception as e:
            logger.warning(f"⚠️ Entity extraction failed: {e}")
            return []

    def _detect_language(self, content: str) -> str:
        """언어 감지"""
        try:
            # 간단한 한글 감지
            korean_chars = sum(
                1 for c in content if ord(c) >= 0xAC00 and ord(c) <= 0xD7A3
            )
            if korean_chars > len(content) * 0.3:
                return "ko"
            return "en"

        except Exception as e:
            logger.warning(f"⚠️ Language detection failed: {e}")
            return "ko"  # 기본값

    def _identify_learning_indicator(
        self, content: str, sentiment: SentimentType, intent: IntentType
    ) -> Optional[str]:
        """학습 지표 식별"""
        try:
            content_lower = content.lower()

            # 이해도 확인
            if any(
                w in content_lower
                for w in ["알겠습니다", "이해됐", "알았어", "맞다", "그렇군요"]
            ):
                return "understands"

            # 혼란도 확인
            if sentiment == SentimentType.CONFUSED or any(
                w in content_lower for w in ["모르겠다", "이해가", "뭐지", "설명해"]
            ):
                return "confused"

            # 깊이 있는 질문
            if intent == IntentType.QUESTION and any(
                w in content_lower for w in ["왜", "어떻게", "그러면"]
            ):
                return "asking_deep_question"

            return None

        except Exception as e:
            logger.warning(f"⚠️ Learning indicator identification failed: {e}")
            return None

    def _calculate_topic_relevance(self, keywords: List[str], content: str) -> float:
        """주제 관련성 계산"""
        try:
            if not keywords:
                return 0.5  # 중립

            # 키워드 개수 기반 점수
            score = min(len(keywords) * 0.25, 1.0)

            # 키워드 반복 횟수 고려
            content_lower = content.lower()
            for keyword in keywords:
                count = content_lower.count(keyword.lower())
                if count > 1:
                    score = min(score + 0.1, 1.0)

            return score

        except Exception as e:
            logger.warning(f"⚠️ Topic relevance calculation failed: {e}")
            return 0.5

    def _evaluate_response_required(
        self, intent: IntentType, user_type: str, sentiment: SentimentType
    ) -> bool:
        """교사 응답 필요 여부 평가"""
        try:
            # 학생의 질문은 항상 응답 필요
            if user_type == "student" and intent == IntentType.QUESTION:
                return True

            # 혼란도가 높으면 응답 필요
            if sentiment == SentimentType.CONFUSED:
                return True

            # 깊이 있는 질문
            if user_type == "student" and intent == IntentType.OPINION:
                return True

            return False

        except Exception as e:
            logger.warning(f"⚠️ Response evaluation failed: {e}")
            return False

    def _calculate_quality_score(
        self, intent: IntentType, sentiment_score: float, topic_relevance: float
    ) -> float:
        """품질 점수 계산"""
        try:
            score = 0.0

            # 의도 기반 점수
            intent_scores = {
                IntentType.QUESTION: 0.7,
                IntentType.ANSWER: 0.6,
                IntentType.CLARIFICATION: 0.8,
                IntentType.OPINION: 0.5,
                IntentType.GREETING: 0.2,
                IntentType.FEEDBACK: 0.5,
                IntentType.OTHER: 0.3,
            }
            score += intent_scores.get(intent, 0.3)

            # 긍정적 감정 추가 점수
            if sentiment_score > 0.5:
                score += 0.15

            # 주제 관련성 추가
            score += topic_relevance * 0.15

            return min(score, 1.0)

        except Exception as e:
            logger.warning(f"⚠️ Quality score calculation failed: {e}")
            return 0.5

    def summarize_conversation(self, session_id: str) -> ConversationSummary:
        """대화 요약"""
        try:
            messages = self.conversation_history.get(session_id, [])

            if not messages:
                raise ValueError(f"No conversation found for session: {session_id}")

            # 주요 토픽 추출
            all_keywords = []
            for msg in messages:
                all_keywords.extend(msg.keywords)
            main_topics = list(set(all_keywords))[:5]

            # 주요 질문 추출
            key_questions = [
                msg.content
                for msg in messages
                if msg.intent == IntentType.QUESTION and len(msg.content) > 10
            ][:5]

            # 학생 이해도 평가
            understanding_indicators = [
                msg.learning_indicator for msg in messages if msg.learning_indicator
            ]
            if "confused" in understanding_indicators:
                understanding = "poor"
            elif "asks_deep_question" in understanding_indicators:
                understanding = "excellent"
            elif "understands" in understanding_indicators:
                understanding = "good"
            else:
                understanding = "fair"

            # 참여도 평가
            student_messages = [m for m in messages if m.user_type == "student"]
            if len(student_messages) > len(messages) * 0.4:
                engagement = "high"
            elif len(student_messages) > len(messages) * 0.2:
                engagement = "medium"
            else:
                engagement = "low"

            # 복습 필요 영역
            confused_messages = [
                m for m in messages if m.sentiment == SentimentType.CONFUSED
            ]
            areas_needing_review = []
            for msg in confused_messages:
                areas_needing_review.extend(msg.keywords)
            areas_needing_review = list(set(areas_needing_review))[:3]

            summary = ConversationSummary(
                session_id=session_id,
                summary=f"총 {len(messages)}개의 메시지가 있었고, 주요 토픽은 {', '.join(main_topics)}입니다.",
                main_topics=main_topics,
                key_questions=key_questions,
                student_understanding_level=understanding,
                engagement_level=engagement,
                areas_needing_review=areas_needing_review,
            )

            logger.info(f"✅ Conversation summarized: {session_id}")
            return summary

        except Exception as e:
            logger.error(f"❌ Failed to summarize conversation: {e}")
            raise

    def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """메시지 조회"""
        return self.message_cache.get(message_id)

    def list_messages_by_session(self, session_id: str) -> List[ChatMessage]:
        """세션별 메시지 목록"""
        return self.conversation_history.get(session_id, [])


# 전역 인스턴스
_nlp_analyzer = None


async def init_nlp_analyzer() -> NLPAnalyzer:
    """NLPAnalyzer 초기화"""
    global _nlp_analyzer

    try:
        _nlp_analyzer = NLPAnalyzer()
        logger.info("✅ NLPAnalyzer initialized successfully")
        return _nlp_analyzer

    except Exception as e:
        logger.error(f"❌ Failed to initialize NLPAnalyzer: {e}")
        raise


def get_nlp_analyzer() -> Optional[NLPAnalyzer]:
    """NLPAnalyzer 인스턴스 반환"""
    return _nlp_analyzer
