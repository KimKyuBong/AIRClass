"""
AIRClass Vision Analysis Module
스크린샷 및 비디오 프레임 분석을 통한 교육 콘텐츠 이해
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import base64
import io

logger = logging.getLogger(__name__)


@dataclass
class VisualElement:
    """화면의 시각적 요소"""

    type: str  # "text", "chart", "diagram", "code", "media", "ui"
    confidence: float  # 0.0-1.0
    bounds: Dict  # {"x": int, "y": int, "width": int, "height": int}
    content: Optional[str] = None  # OCR 또는 설명
    properties: Dict = None  # 추가 속성


@dataclass
class ContentAnalysis:
    """콘텐츠 분석 결과"""

    analysis_id: str
    session_id: str
    screenshot_path: str
    timestamp: str

    # 콘텐츠 타입
    content_type: str  # "lecture", "code", "quiz", "discussion", "presentation"
    content_topic: Optional[str]

    # 시각적 요소
    visual_elements: List[VisualElement]

    # 텍스트 내용
    extracted_text: str
    primary_language: str

    # 교육적 지표
    complexity_score: float  # 0.0-1.0 (난이도)
    engagement_potential: float  # 0.0-1.0 (학생 참여도 유도 가능성)

    # 메타데이터
    dominant_colors: List[str]  # 주요 색상 (HEX)
    scene_description: str  # 장면 설명

    # 추천 작업
    recommendations: List[str]


class VisionAnalyzer:
    """스크린샷 및 비디오 프레임 분석"""

    def __init__(self):
        """초기화"""
        self.cache: Dict[str, ContentAnalysis] = {}
        logger.info("💡 VisionAnalyzer initialized")

    def analyze_screenshot(
        self, session_id: str, screenshot_path: str
    ) -> ContentAnalysis:
        """
        스크린샷 분석

        Args:
            session_id: 세션 ID
            screenshot_path: 스크린샷 파일 경로

        Returns:
            ContentAnalysis: 분석 결과
        """
        try:
            screenshot_file = Path(screenshot_path)
            if not screenshot_file.exists():
                raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")

            analysis_id = f"{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 1. 시각적 요소 추출 (OCR, 객체 탐지)
            visual_elements = self._extract_visual_elements(screenshot_path)

            # 2. 텍스트 추출 (OCR)
            extracted_text = self._extract_text(screenshot_path)

            # 3. 콘텐츠 타입 분류
            content_type = self._classify_content_type(visual_elements, extracted_text)

            # 4. 콘텐츠 토픽 식별
            content_topic = self._identify_topic(extracted_text, visual_elements)

            # 5. 복잡도 계산
            complexity_score = self._calculate_complexity(
                visual_elements, extracted_text, content_type
            )

            # 6. 참여도 가능성 평가
            engagement_potential = self._evaluate_engagement(
                content_type, visual_elements, extracted_text
            )

            # 7. 색상 분석
            dominant_colors = self._analyze_colors(screenshot_path)

            # 8. 장면 설명 생성
            scene_description = self._generate_scene_description(
                content_type, visual_elements, extracted_text
            )

            # 9. 추천 작업 생성
            recommendations = self._generate_recommendations(
                content_type, complexity_score, engagement_potential
            )

            # 분석 결과 생성
            analysis = ContentAnalysis(
                analysis_id=analysis_id,
                session_id=session_id,
                screenshot_path=screenshot_path,
                timestamp=datetime.now().isoformat(),
                content_type=content_type,
                content_topic=content_topic,
                visual_elements=visual_elements,
                extracted_text=extracted_text,
                primary_language="ko",  # 한국어 기본값
                complexity_score=complexity_score,
                engagement_potential=engagement_potential,
                dominant_colors=dominant_colors,
                scene_description=scene_description,
                recommendations=recommendations,
            )

            # 캐시에 저장
            self.cache[analysis_id] = analysis

            logger.info(f"✅ Screenshot analyzed: {analysis_id}")
            return analysis

        except Exception as e:
            logger.error(f"❌ Failed to analyze screenshot: {e}")
            raise

    def _extract_visual_elements(self, screenshot_path: str) -> List[VisualElement]:
        """시각적 요소 추출 (모의 구현)"""
        try:
            # 실제 구현에서는 OpenCV, YOLO 등을 사용
            # 현재는 기본 요소들을 시뮬레이션
            elements = []

            # 텍스트 박스 (헤더/제목)
            elements.append(
                VisualElement(
                    type="text",
                    confidence=0.95,
                    bounds={"x": 10, "y": 10, "width": 500, "height": 40},
                    content="슬라이드 제목",
                    properties={"font_size": "large", "weight": "bold"},
                )
            )

            # 코드 블록
            elements.append(
                VisualElement(
                    type="code",
                    confidence=0.85,
                    bounds={"x": 10, "y": 60, "width": 780, "height": 200},
                    content="def calculate_average(numbers):\n    return sum(numbers) / len(numbers)",
                    properties={"language": "python"},
                )
            )

            # UI 컴포넌트
            elements.append(
                VisualElement(
                    type="ui",
                    confidence=0.9,
                    bounds={"x": 10, "y": 270, "width": 780, "height": 30},
                    properties={"element": "button", "text": "실행"},
                )
            )

            return elements

        except Exception as e:
            logger.warning(f"⚠️ Failed to extract visual elements: {e}")
            return []

    def _extract_text(self, screenshot_path: str) -> str:
        """텍스트 추출 (OCR)"""
        try:
            # 실제 구현에서는 Tesseract, PaddleOCR 등을 사용
            # 현재는 모의 데이터 반환
            mock_text = """
            Python 프로그래밍 강의
            
            오늘의 주제: 함수와 데이터 구조
            
            def calculate_average(numbers):
                return sum(numbers) / len(numbers)
            
            # 예제
            grades = [85, 90, 88, 92]
            avg = calculate_average(grades)
            print(f"평균: {avg}")
            
            퀴즈: 다음 코드의 출력값은?
            """
            return mock_text.strip()

        except Exception as e:
            logger.warning(f"⚠️ Failed to extract text: {e}")
            return ""

    def _classify_content_type(
        self, visual_elements: List[VisualElement], extracted_text: str
    ) -> str:
        """콘텐츠 타입 분류"""
        try:
            text_lower = extracted_text.lower()

            # 콘텐츠 타입 감지
            if any(
                keyword in text_lower
                for keyword in ["def ", "class ", "import ", "함수", "코드"]
            ):
                return "code"
            elif any(
                keyword in text_lower for keyword in ["퀴즈", "문제", "선택", "답"]
            ):
                return "quiz"
            elif any(
                keyword in text_lower for keyword in ["토론", "의견", "토의", "발표"]
            ):
                return "discussion"
            elif any(
                keyword in text_lower for keyword in ["그래프", "차트", "다이어그램"]
            ):
                return "diagram"
            elif any(e.type == "code" for e in visual_elements):
                return "code"
            else:
                return "lecture"  # 기본값

        except Exception as e:
            logger.warning(f"⚠️ Failed to classify content type: {e}")
            return "lecture"

    def _identify_topic(
        self, extracted_text: str, visual_elements: List[VisualElement]
    ) -> Optional[str]:
        """콘텐츠 토픽 식별"""
        try:
            # 키워드 기반 토픽 추출 (실제로는 NLP 사용)
            keywords = {
                "함수": "functions",
                "데이터": "data_structures",
                "알고리즘": "algorithms",
                "웹": "web",
                "데이터베이스": "database",
                "보안": "security",
                "네트워크": "networking",
                "머신러닝": "machine_learning",
            }

            text_lower = extracted_text.lower()
            for korean, english in keywords.items():
                if korean in text_lower:
                    return english

            return None

        except Exception as e:
            logger.warning(f"⚠️ Failed to identify topic: {e}")
            return None

    def _calculate_complexity(
        self,
        visual_elements: List[VisualElement],
        extracted_text: str,
        content_type: str,
    ) -> float:
        """복잡도 계산 (0.0-1.0)"""
        try:
            score = 0.0

            # 요소 개수
            element_count = len(visual_elements)
            if element_count > 5:
                score += 0.3
            elif element_count > 3:
                score += 0.15

            # 텍스트 길이
            text_length = len(extracted_text.split())
            if text_length > 200:
                score += 0.3
            elif text_length > 100:
                score += 0.15

            # 콘텐츠 타입별 기본 복잡도
            complexity_by_type = {
                "code": 0.7,
                "diagram": 0.6,
                "lecture": 0.3,
                "quiz": 0.4,
                "discussion": 0.2,
            }
            score += complexity_by_type.get(content_type, 0.3)

            # 정규화 (0.0-1.0)
            return min(score / 1.3, 1.0)

        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate complexity: {e}")
            return 0.5

    def _evaluate_engagement(
        self,
        content_type: str,
        visual_elements: List[VisualElement],
        extracted_text: str,
    ) -> float:
        """참여도 가능성 평가 (0.0-1.0)"""
        try:
            score = 0.5  # 기본값

            # 콘텐츠 타입별 참여도
            engagement_by_type = {
                "quiz": 0.95,  # 높음
                "discussion": 0.85,
                "code": 0.75,
                "diagram": 0.65,
                "lecture": 0.45,
            }
            score = engagement_by_type.get(content_type, 0.5)

            # 상호작용 요소 감지
            has_interactive = any(e.type == "ui" for e in visual_elements)
            if has_interactive:
                score = min(score + 0.15, 1.0)

            # 질문 감지
            if "?" in extracted_text:
                score = min(score + 0.1, 1.0)

            return score

        except Exception as e:
            logger.warning(f"⚠️ Failed to evaluate engagement: {e}")
            return 0.5

    def _analyze_colors(self, screenshot_path: str) -> List[str]:
        """색상 분석"""
        try:
            # 실제 구현에서는 이미지 처리를 사용
            # 현재는 기본 색상 반환
            return ["#3366FF", "#FF6633", "#33FF66", "#FFFF33"]

        except Exception as e:
            logger.warning(f"⚠️ Failed to analyze colors: {e}")
            return ["#000000", "#FFFFFF"]

    def _generate_scene_description(
        self,
        content_type: str,
        visual_elements: List[VisualElement],
        extracted_text: str,
    ) -> str:
        """장면 설명 생성"""
        try:
            descriptions = []

            # 콘텐츠 타입 설명
            type_descriptions = {
                "code": "코드 샘플을 보여주는 프로그래밍 교육 화면",
                "lecture": "교육용 강의 슬라이드",
                "quiz": "학생들의 이해도를 평가하는 퀴즈 화면",
                "diagram": "개념을 설명하는 다이어그램 또는 차트",
                "discussion": "토론 및 참여가 중심인 콘텐츠",
            }
            descriptions.append(type_descriptions.get(content_type, "교육용 콘텐츠"))

            # 요소 개수
            if len(visual_elements) > 5:
                descriptions.append("여러 시각적 요소가 포함되어 있음")

            # 텍스트 양
            word_count = len(extracted_text.split())
            if word_count > 200:
                descriptions.append("상세한 텍스트 설명이 포함됨")
            elif word_count > 50:
                descriptions.append("적당한 양의 텍스트가 포함됨")

            return ", ".join(descriptions)

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate scene description: {e}")
            return "교육용 콘텐츠"

    def _generate_recommendations(
        self, content_type: str, complexity_score: float, engagement_potential: float
    ) -> List[str]:
        """추천 작업 생성"""
        try:
            recommendations = []

            # 복잡도 기반
            if complexity_score > 0.7:
                recommendations.append(
                    "이 콘텐츠는 고급 주제입니다. 사전 학습 자료 제공 권장"
                )
            elif complexity_score < 0.3:
                recommendations.append(
                    "기초 개념을 다루는 내용입니다. 심화 학습 자료 추가 권장"
                )

            # 참여도 기반
            if engagement_potential > 0.8:
                recommendations.append(
                    "학생 상호작용이 많을 것으로 예상되니 토론 시간 충분히 확보"
                )
            elif engagement_potential < 0.5:
                recommendations.append("학생 참여를 높이기 위해 대화형 요소 추가 권장")

            # 콘텐츠 타입별
            if content_type == "code":
                recommendations.append("실습 시간 또는 코드 리뷰 세션 포함 권장")
            elif content_type == "quiz":
                recommendations.append("퀴즈 결과 분석 및 피드백 제공 필요")
            elif content_type == "lecture":
                recommendations.append("주요 포인트 정리 및 요약 제공 권장")

            return recommendations if recommendations else ["일반적인 교육 자료입니다"]

        except Exception as e:
            logger.warning(f"⚠️ Failed to generate recommendations: {e}")
            return []

    def get_analysis(self, analysis_id: str) -> Optional[ContentAnalysis]:
        """분석 결과 조회"""
        return self.cache.get(analysis_id)

    def list_analyses(self, session_id: str) -> List[ContentAnalysis]:
        """세션별 분석 결과 목록"""
        return [
            analysis
            for analysis in self.cache.values()
            if analysis.session_id == session_id
        ]

    def analyze_frame_sequence(
        self, session_id: str, frame_paths: List[str]
    ) -> List[ContentAnalysis]:
        """연속된 프레임 분석 (비디오 프레임)"""
        try:
            analyses = []
            for frame_path in frame_paths:
                analysis = self.analyze_screenshot(session_id, frame_path)
                analyses.append(analysis)

            logger.info(f"✅ Analyzed {len(analyses)} frames")
            return analyses

        except Exception as e:
            logger.error(f"❌ Failed to analyze frame sequence: {e}")
            return []


# 전역 인스턴스
_vision_analyzer = None


async def init_vision_analyzer() -> VisionAnalyzer:
    """VisionAnalyzer 초기화"""
    global _vision_analyzer

    try:
        _vision_analyzer = VisionAnalyzer()
        logger.info("✅ VisionAnalyzer initialized successfully")
        return _vision_analyzer

    except Exception as e:
        logger.error(f"❌ Failed to initialize VisionAnalyzer: {e}")
        raise


def get_vision_analyzer() -> Optional[VisionAnalyzer]:
    """VisionAnalyzer 인스턴스 반환"""
    return _vision_analyzer
