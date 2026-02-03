"""
AIRClass 혼동도 감지 테스트
Confusion Detection 알고리즘 검증
"""

import pytest
import sys

sys.path.insert(0, "/Users/hwansi/Project/AirClass/backend")

from services.engagement_service import EngagementCalculator


class TestConfusionDetection:
    """혼동 상태 감지 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_no_confusion_high_accuracy_low_chat(self, calculator):
        """혼동 없음: 높은 정답률 + 낮은 채팅"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.9,  # 90% 맞음
            chat_activity_high=False,  # 채팅 활동 적음
            confusion_indicators=[],
        )

        assert is_confused is False, f"높은 정답률에서 혼동 감지되면 안됨"
        assert confidence < 0.5, f"신뢰도가 0.5 이상이면 안됨"
        print(
            f"✅ No confusion (high accuracy): is_confused={is_confused}, confidence={confidence:.2f}"
        )

    def test_clear_confusion_low_accuracy_high_chat(self, calculator):
        """명백한 혼동: 낮은 정답률 + 높은 채팅"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.1,  # 10% 맞음 (매우 낮음)
            chat_activity_high=True,  # 채팅 활동 많음
            confusion_indicators=[],
        )

        assert is_confused is True or confidence >= 0.5, (
            f"낮은 정답률 + 높은 채팅에서 혼동/높은 신뢰도 필요"
        )
        assert confidence > 0.4, f"신뢰도가 충분해야 함: {confidence}"
        print(
            f"✅ Clear confusion detected: is_confused={is_confused}, confidence={confidence:.2f}"
        )

    def test_confusion_with_indicators(self, calculator):
        """지표 포함 혼동 감지"""
        indicators = ["같은 문제에서 여러 번 틀림", "개념 이해 못한 것 같음"]
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.4,
            chat_activity_high=True,
            confusion_indicators=indicators,
        )

        assert is_confused is True, f"지표가 있으면 혼동을 감지해야 함"
        assert confidence > 0.6, f"지표가 있으면 신뢰도가 충분히 높아야 함 (실제: {confidence:.2f})"
        print(
            f"✅ Confusion with indicators: confidence={confidence:.2f}, indicators={len(indicators)}"
        )

    def test_borderline_confusion_case(self, calculator):
        """경계선 케이스"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.5,  # 정확히 50%
            chat_activity_high=True,  # 채팅 활동 있음
            confusion_indicators=[],
        )

        assert 0.4 <= confidence <= 0.6, f"경계선 케이스 신뢰도는 0.4~0.6 범위여야 함"
        print(
            f"✅ Borderline case: is_confused={is_confused}, confidence={confidence:.2f}"
        )

    def test_multiple_indicators_increase_confidence(self, calculator):
        """지표가 많을수록 신뢰도 증가"""
        # 지표 없을 때
        _, conf_no_indicators = calculator.detect_confusion(
            quiz_accuracy=0.3,
            chat_activity_high=False,
            confusion_indicators=[],
        )

        # 지표 많을 때
        indicators = ["지표1", "지표2", "지표3"]
        _, conf_with_indicators = calculator.detect_confusion(
            quiz_accuracy=0.3,
            chat_activity_high=False,
            confusion_indicators=indicators,
        )

        assert conf_with_indicators > conf_no_indicators, (
            f"지표가 많을수록 신뢰도가 높아야 함"
        )
        print(
            f"✅ More indicators → higher confidence: {conf_no_indicators:.2f} → {conf_with_indicators:.2f}"
        )

    def test_confidence_always_between_0_and_1(self, calculator):
        """신뢰도는 항상 0~1 사이"""
        test_cases = [
            (0.0, False, []),  # 최악
            (1.0, True, ["a", "b", "c", "d", "e"]),  # 최고
            (0.5, False, ["x"]),  # 중간
        ]

        for accuracy, chat_high, indicators in test_cases:
            _, confidence = calculator.detect_confusion(accuracy, chat_high, indicators)
            assert 0.0 <= confidence <= 1.0, f"신뢰도가 범위를 벗어남: {confidence}"

        print(f"✅ Confidence always within bounds")

    def test_confusion_detection_decision_threshold(self, calculator):
        """혼동 판단 기준값은 0.5"""
        # 신뢰도 0.4: 혼동 아님
        is_confused_low, conf_low = calculator.detect_confusion(
            quiz_accuracy=0.45,
            chat_activity_high=False,
            confusion_indicators=[],
        )

        # 신뢰도 0.6: 혼동 있음
        is_confused_high, conf_high = calculator.detect_confusion(
            quiz_accuracy=0.1,
            chat_activity_high=True,
            confusion_indicators=["indicator"],
        )

        if conf_low <= 0.5:
            assert is_confused_low is False
        if conf_high > 0.5:
            assert is_confused_high is True

        print(
            f"✅ Decision threshold at 0.5: low={is_confused_low}, high={is_confused_high}"
        )


class TestConfusionPatterns:
    """혼동 패턴 인식 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_pattern_low_accuracy_high_chat(self, calculator):
        """패턴: 낮은 정답률 + 높은 채팅 (전형적인 혼동)"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.25,
            chat_activity_high=True,
            confusion_indicators=[],
        )

        assert is_confused is True
        assert confidence > 0.5
        print(f"✅ Pattern recognized: low accuracy + high chat")

    def test_pattern_high_participation_low_accuracy(self, calculator):
        """패턴: 많은 활동 + 낮은 성과"""
        # 높은 채팅 활동이지만 정답률이 낮음
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.3,
            chat_activity_high=True,
            confusion_indicators=["반복되는 질문", "개념 이해 안 됨"],
        )

        assert is_confused is True
        assert confidence > 0.6
        print(f"✅ Pattern: High participation + low accuracy")

    def test_pattern_silent_failure(self, calculator):
        """패턴: 조용한 실패 (활동은 적지만 정답 못함)"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.2,
            chat_activity_high=False,
            confusion_indicators=["침묵", "응답 안 함"],
        )

        # 지표가 있으면 혼동으로 감지할 수 있음
        assert confidence > 0.3
        print(f"✅ Pattern: Silent failure detected with confidence {confidence:.2f}")


class TestEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_zero_accuracy_high_activity(self, calculator):
        """0% 정답률 + 높은 활동"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.0,
            chat_activity_high=True,
            confusion_indicators=[],
        )

        assert is_confused is True
        assert confidence > 0.5
        print(f"✅ Zero accuracy + high activity: confidence={confidence:.2f}")

    def test_perfect_accuracy_no_indicators(self, calculator):
        """100% 정답률 = 혼동 없음"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=1.0,
            chat_activity_high=False,
            confusion_indicators=[],
        )

        assert is_confused is False
        assert confidence < 0.5
        print(f"✅ Perfect accuracy: no confusion detected")

    def test_empty_indicators_list(self, calculator):
        """빈 지표 리스트"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.5,
            chat_activity_high=False,
            confusion_indicators=[],
        )

        assert confidence == 0.0  # 지표 없으면 기본값
        print(f"✅ Empty indicators: confidence={confidence}")

    def test_many_indicators(self, calculator):
        """많은 지표"""
        indicators = [f"지표{i}" for i in range(10)]
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.5,
            chat_activity_high=False,
            confusion_indicators=indicators,
        )

        assert confidence > 0.5
        assert confidence <= 1.0
        print(f"✅ Many indicators (10): confidence={confidence:.2f}")

    def test_conflicting_signals(self, calculator):
        """상충하는 신호: 높은 정답률 + 높은 채팅"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.9,  # 좋음
            chat_activity_high=True,  # 높음 (나쁜 신호)
            confusion_indicators=[],
        )

        # 정답률이 높으면 혼동으로 보지 않아야 함
        assert is_confused is False or confidence < 0.5
        print(f"✅ Conflicting signals: confidence={confidence:.2f}")


class TestConfusionRecommendations:
    """혼동 상태에서의 권장사항 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_severe_confusion_recommendations(self, calculator):
        """심각한 혼동 감지 시 권장사항"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.1,  # 매우 낮음
            chat_activity_high=True,
            confusion_indicators=["개념 이해 못함", "질문 반복"],
        )

        assert is_confused is True
        assert confidence > 0.75
        print(f"✅ Severe confusion (confidence={confidence:.2f})")

        # 점수로 변환하여 권장사항 확인
        overall_score = confidence * 100  # 신뢰도를 점수로 변환 (임시)
        if overall_score < 50:
            print(f"   권장: 개념 재설명, 일대일 상담, 진도 조절")

    def test_mild_confusion_recommendations(self, calculator):
        """약한 혼동 감지 시 권장사항"""
        is_confused, confidence = calculator.detect_confusion(
            quiz_accuracy=0.5,
            chat_activity_high=False,
            confusion_indicators=[],
        )

        print(f"✅ Mild confusion (confidence={confidence:.2f})")
        if 0.4 <= confidence <= 0.6:
            print(f"   권장: 추가 과제, 참여 독려")


class TestConfusionStatistics:
    """혼동 통계 및 분포 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_confusion_rate_calculation(self, calculator):
        """혼동 학생 비율 계산"""
        test_students = [
            (0.9, False),  # 정상
            (0.8, False),  # 정상
            (0.3, True),  # 혼동
            (0.4, True),  # 혼동
            (0.2, True),  # 혼동
        ]

        confused_count = 0
        for accuracy, high_chat in test_students:
            is_confused, _ = calculator.detect_confusion(accuracy, high_chat, [])
            if is_confused:
                confused_count += 1

        confusion_rate = confused_count / len(test_students)
        print(
            f"✅ Confusion rate: {confusion_rate:.1%} ({confused_count}/{len(test_students)})"
        )
        assert 0 <= confusion_rate <= 1.0

    def test_confidence_distribution(self, calculator):
        """신뢰도 분포"""
        confidences = []

        for accuracy in [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]:
            for chat in [True, False]:
                _, conf = calculator.detect_confusion(accuracy, chat, [])
                confidences.append(conf)

        avg_confidence = sum(confidences) / len(confidences)
        max_confidence = max(confidences)
        min_confidence = min(confidences)

        print(f"✅ Confidence distribution:")
        print(f"   Average: {avg_confidence:.2f}")
        print(f"   Range: {min_confidence:.2f} - {max_confidence:.2f}")

        assert min_confidence >= 0.0
        assert max_confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
