"""
AIRClass 참여도 계산 엔진 테스트
EngagementCalculator 모든 점수 계산 메서드 검증
"""

import pytest
from datetime import datetime
import sys

sys.path.insert(0, "/Users/hwansi/Project/AirClass/backend")

from engagement import EngagementCalculator


class TestAttentionScore:
    """주의집중도 점수 계산 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_perfect_attention_score(self, calculator):
        """완벽한 주의집중도: 100% 퀴즈 참여, 1초 응답, 50분 시청"""
        score = calculator._calculate_latency_score(1000)  # 1초 = 0.8점

        attention = calculator.calculate_attention_score(
            quiz_participation_rate=1.0,
            avg_response_latency_ms=1000,
            screen_time_minutes=48,
            max_possible_time=50,
        )

        assert 0.8 <= attention <= 1.0, (
            f"완벽한 주의 점수는 0.8~1.0 사이여야 함, 득점: {attention}"
        )
        print(f"✅ Perfect attention score: {attention:.3f}")

    def test_poor_attention_score(self, calculator):
        """낮은 주의집중도: 0% 참여, 15초 응답, 5분 시청"""
        attention = calculator.calculate_attention_score(
            quiz_participation_rate=0.0,
            avg_response_latency_ms=15000,
            screen_time_minutes=5,
            max_possible_time=50,
        )

        assert 0.0 <= attention < 0.3, (
            f"낮은 주의 점수는 0.3 미만이어야 함, 득점: {attention}"
        )
        print(f"✅ Poor attention score: {attention:.3f}")

    def test_moderate_attention_score(self, calculator):
        """중간 정도의 주의집중도"""
        attention = calculator.calculate_attention_score(
            quiz_participation_rate=0.6,
            avg_response_latency_ms=3500,
            screen_time_minutes=30,
            max_possible_time=50,
        )

        assert 0.4 <= attention <= 0.7, (
            f"중간 주의 점수는 0.4~0.7 사이여야 함, 득점: {attention}"
        )
        print(f"✅ Moderate attention score: {attention:.3f}")

    def test_attention_score_bounds(self, calculator):
        """주의 점수는 항상 0~1 사이"""
        # 극단적인 값들
        scores = [
            calculator.calculate_attention_score(2.0, -5000, 100, 50),  # 초과값
            calculator.calculate_attention_score(-1.0, 50000, -10, 50),  # 음수
        ]

        for score in scores:
            assert 0.0 <= score <= 1.0, f"점수가 범위를 벗어남: {score}"
        print(f"✅ Attention scores within bounds: {scores}")


class TestLatencyScore:
    """응답 속도 점수 계산 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_excellent_latency(self, calculator):
        """우수한 응답 속도 (0-1초) = 1.0점"""
        score = calculator._calculate_latency_score(500)
        assert score == 1.0
        print(f"✅ Excellent latency (500ms): {score}")

    def test_good_latency(self, calculator):
        """좋은 응답 속도 (1-3초) = 0.8점"""
        score = calculator._calculate_latency_score(2000)
        assert score == 0.8
        print(f"✅ Good latency (2000ms): {score}")

    def test_normal_latency(self, calculator):
        """보통 응답 속도 (3-5초) = 0.6점"""
        score = calculator._calculate_latency_score(4000)
        assert score == 0.6
        print(f"✅ Normal latency (4000ms): {score}")

    def test_slow_latency(self, calculator):
        """느린 응답 속도 (5-10초) = 0.4점"""
        score = calculator._calculate_latency_score(7000)
        assert score == 0.4
        print(f"✅ Slow latency (7000ms): {score}")

    def test_very_slow_latency(self, calculator):
        """매우 느린 응답 속도 (10초+) = 0.2점"""
        score = calculator._calculate_latency_score(20000)
        assert score == 0.2
        print(f"✅ Very slow latency (20000ms): {score}")


class TestParticipationScore:
    """참여도 점수 계산 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_high_participation(self, calculator):
        """높은 참여: 채팅 10개, 퀴즈 10개"""
        score = calculator.calculate_participation_score(
            chat_message_count=10,
            quiz_response_count=10,
            session_duration_minutes=45,
        )

        # 채팅: 10*5=50 → cap 40, 퀴즈: 10*5=50, 세션: 10
        # 총 40+50+10 = 100 (최대)
        assert score == 100, f"높은 참여 점수는 100이어야 함, 득점: {score}"
        print(f"✅ High participation score: {score}")

    def test_no_participation(self, calculator):
        """참여 없음: 채팅 0개, 퀴즈 0개, 세션 미참석"""
        score = calculator.calculate_participation_score(
            chat_message_count=0,
            quiz_response_count=0,
            session_duration_minutes=0,
        )

        assert score == 0, f"참여 없을 때 점수는 0이어야 함, 득점: {score}"
        print(f"✅ No participation score: {score}")

    def test_moderate_participation(self, calculator):
        """중간 참여: 채팅 5개, 퀴즈 5개"""
        score = calculator.calculate_participation_score(
            chat_message_count=5,
            quiz_response_count=5,
            session_duration_minutes=40,
        )

        # 채팅: 5*5=25, 퀴즈: 5*5=25, 세션: 10 = 60
        assert 50 <= score <= 70, f"중간 참여 점수는 50~70 범위여야 함, 득점: {score}"
        print(f"✅ Moderate participation score: {score}")

    def test_participation_score_never_exceeds_100(self, calculator):
        """참여 점수는 항상 100을 초과하지 않음"""
        score = calculator.calculate_participation_score(
            chat_message_count=100,  # 극단적 값
            quiz_response_count=100,
            session_duration_minutes=50,
        )

        assert score <= 100, f"참여 점수가 100을 초과함: {score}"
        print(f"✅ Participation never exceeds 100: {score}")


class TestQuizAccuracy:
    """정답률 계산 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_perfect_accuracy(self, calculator):
        """완벽한 정답률: 10/10"""
        accuracy = calculator.calculate_quiz_accuracy(
            correct_responses=10,
            total_responses=10,
        )

        assert accuracy == 1.0, f"완벽한 정답률은 1.0이어야 함, 득점: {accuracy}"
        print(f"✅ Perfect accuracy: {accuracy}")

    def test_zero_accuracy(self, calculator):
        """0% 정답률: 0/10"""
        accuracy = calculator.calculate_quiz_accuracy(
            correct_responses=0,
            total_responses=10,
        )

        assert accuracy == 0.0, f"0% 정답률은 0.0이어야 함, 득점: {accuracy}"
        print(f"✅ Zero accuracy: {accuracy}")

    def test_partial_accuracy(self, calculator):
        """부분 정답률: 7/10"""
        accuracy = calculator.calculate_quiz_accuracy(
            correct_responses=7,
            total_responses=10,
        )

        assert accuracy == 0.7, f"7/10 정답률은 0.7이어야 함, 득점: {accuracy}"
        print(f"✅ Partial accuracy (70%): {accuracy}")

    def test_no_responses(self, calculator):
        """응답 없음: 0/0"""
        accuracy = calculator.calculate_quiz_accuracy(
            correct_responses=0,
            total_responses=0,
        )

        assert accuracy == 0.0, f"응답 없을 때는 0.0이어야 함, 득점: {accuracy}"
        print(f"✅ No responses accuracy: {accuracy}")


class TestOverallEngagementScore:
    """종합 참여도 점수 계산 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_perfect_overall_score(self, calculator):
        """완벽한 종합 점수"""
        score = calculator.calculate_overall_engagement_score(
            attention_score=1.0,  # 100%
            participation_score=100,  # 100점
            quiz_accuracy=1.0,  # 100%
        )

        assert score == 100.0, f"완벽한 종합 점수는 100.0이어야 함, 득점: {score}"
        print(f"✅ Perfect overall score: {score}")

    def test_poor_overall_score(self, calculator):
        """낮은 종합 점수"""
        score = calculator.calculate_overall_engagement_score(
            attention_score=0.0,
            participation_score=0,
            quiz_accuracy=0.0,
        )

        assert score == 0.0, f"낮은 종합 점수는 0.0이어야 함, 득점: {score}"
        print(f"✅ Poor overall score: {score}")

    def test_moderate_overall_score(self, calculator):
        """중간 정도의 종합 점수"""
        score = calculator.calculate_overall_engagement_score(
            attention_score=0.6,  # 60점 상당
            participation_score=60,  # 60점
            quiz_accuracy=0.7,  # 70점 상당
        )

        # 0.4*60 + 0.4*60 + 0.2*70 = 24+24+14 = 62
        expected = 62.0
        assert abs(score - expected) < 0.1, (
            f"중간 점수는 약 {expected}여야 함, 득점: {score}"
        )
        print(f"✅ Moderate overall score: {score:.1f} (expected ~{expected})")

    def test_weighted_calculation(self, calculator):
        """가중평균 올바름: 40% 집중, 40% 참여, 20% 정답률"""
        score = calculator.calculate_overall_engagement_score(
            attention_score=0.5,  # 50점 상당
            participation_score=50,  # 50점
            quiz_accuracy=0.5,  # 50점 상당
        )

        # 0.4*50 + 0.4*50 + 0.2*50 = 20+20+10 = 50
        assert abs(score - 50.0) < 0.1, f"가중평균이 50.0이어야 함, 득점: {score}"
        print(f"✅ Weighted calculation: {score:.1f}")

    def test_overall_score_bounds(self, calculator):
        """종합 점수는 항상 0~100 사이"""
        scores = [
            calculator.calculate_overall_engagement_score(2.0, 200, 2.0),  # 초과값
            calculator.calculate_overall_engagement_score(-1.0, -100, -1.0),  # 음수
        ]

        for score in scores:
            assert 0.0 <= score <= 100.0, f"종합 점수가 범위를 벗어남: {score}"
        print(f"✅ Overall scores within bounds: {scores}")


class TestEngagementLevelInterpretation:
    """참여도 레벨 해석 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_excellent_level(self, calculator):
        """우수 레벨: 80-100점"""
        result = calculator.interpret_engagement_level(90)

        assert result["level"] == "excellent", f"90점은 excellent여야 함"
        assert result["color"] == "green", f"우수는 초록색이어야 함"
        assert len(result["recommendations"]) > 0, f"권장사항이 있어야 함"
        print(f"✅ Excellent level (90): {result['level']}, color: {result['color']}")

    def test_good_level(self, calculator):
        """좋은 레벨: 60-79점"""
        result = calculator.interpret_engagement_level(70)

        assert result["level"] == "good"
        assert result["color"] == "blue"
        print(f"✅ Good level (70): {result['level']}, color: {result['color']}")

    def test_moderate_level(self, calculator):
        """보통 레벨: 40-59점"""
        result = calculator.interpret_engagement_level(50)

        assert result["level"] == "moderate"
        assert result["color"] == "yellow"
        print(f"✅ Moderate level (50): {result['level']}, color: {result['color']}")

    def test_low_level(self, calculator):
        """낮은 레벨: 0-39점"""
        result = calculator.interpret_engagement_level(30)

        assert result["level"] == "low"
        assert result["color"] == "red"
        print(f"✅ Low level (30): {result['level']}, color: {result['color']}")

    def test_all_level_have_recommendations(self, calculator):
        """모든 레벨이 권장사항을 포함"""
        scores = [90, 70, 50, 30]

        for score in scores:
            result = calculator.interpret_engagement_level(score)
            assert "recommendations" in result, f"{score}점에 권장사항이 없음"
            assert len(result["recommendations"]) > 0, f"{score}점 권장사항이 비어있음"

        print(f"✅ All levels have recommendations")


class TestTrendAnalysis:
    """참여도 추세 분석 테스트"""

    @pytest.fixture
    def calculator(self):
        return EngagementCalculator()

    def test_increasing_trend(self, calculator):
        """증가 추세 감지"""
        scores = [30, 40, 50, 60, 70]
        trend = calculator.analyze_trend(scores)

        assert trend["trend_direction"] == "increasing", f"증가 추세를 감지하지 못함"
        print(f"✅ Increasing trend detected: {trend['trend_direction']}")

    def test_decreasing_trend(self, calculator):
        """감소 추세 감지"""
        scores = [80, 70, 60, 50, 40]
        trend = calculator.analyze_trend(scores)

        assert trend["trend_direction"] == "decreasing", f"감소 추세를 감지하지 못함"
        print(f"✅ Decreasing trend detected: {trend['trend_direction']}")

    def test_stable_trend(self, calculator):
        """안정적인 추세"""
        scores = [50, 50, 50, 50, 50]
        trend = calculator.analyze_trend(scores)

        assert trend["trend_direction"] in ["increasing", "decreasing", "stable"]
        assert trend["trend_strength"] < 0.1  # 거의 변화 없음
        print(f"✅ Stable trend: {trend}")

    def test_average_calculation(self, calculator):
        """평균값 올바름"""
        scores = [30, 50, 70]
        trend = calculator.analyze_trend(scores)

        expected_avg = 50.0
        assert abs(trend["average"] - expected_avg) < 0.1
        print(f"✅ Average calculation correct: {trend['average']}")

    def test_single_score_trend(self, calculator):
        """단일 점수 추세"""
        scores = [75]
        trend = calculator.analyze_trend(scores)

        assert trend["average"] == 75.0
        print(f"✅ Single score trend: {trend}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
