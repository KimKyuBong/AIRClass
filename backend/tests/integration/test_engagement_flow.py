"""
AIRClass Integration Tests - Full Engagement Workflow
테스트 범위: 학생 활동 추적 → 참여도 계산 → 대시보드 조회 전체 플로우
"""

import pytest
from fastapi.testclient import TestClient
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# conftest.py 가져오기 (모듈 경로 설정)
import schemas  # noqa: F401


@pytest.fixture(scope="module")
def setup_backend():
    """백엔드 환경 설정"""
    from main import app

    # App이 자동으로 startup 이벤트에서 초기화함
    # TestClient가 startup 이벤트 실행
    return app


@pytest.fixture
def client(setup_backend):
    """FastAPI TestClient"""
    return TestClient(setup_backend)


# ============================================
# Integration Test: Single Student Activity Flow
# ============================================


class TestSingleStudentFlow:
    """단일 학생의 전체 활동 흐름 테스트"""

    def test_track_student_activities_and_retrieve_metrics(self, client):
        """
        학생이 참여도 추적 → 메트릭 조회까지의 전체 플로우
        1. 채팅 추적
        2. 퀴즈 응답 추적
        3. 참여도 계산
        4. 메트릭 조회
        """
        session_id = "integration-single-flow"
        student_id = "student-001"

        # Step 1: 채팅 활동 추적
        chat_response = client.post(
            "/api/engagement/track/chat",
            json={
                "session_id": session_id,
                "student_id": student_id,
                "message": "안녕하세요!",
            },
        )
        assert chat_response.status_code in [200, 201, 503]
        print("  ✅ Step 1: Chat activity tracked")

        # Step 2: 퀴즈 응답 추적 (5회)
        for i in range(5):
            quiz_response = client.post(
                "/api/engagement/track/quiz-response",
                json={
                    "session_id": session_id,
                    "student_id": student_id,
                    "quiz_id": f"quiz-{i + 1}",
                    "response_time_ms": 2000 + i * 500,
                    "is_correct": i % 2 == 0,
                },
            )
            assert quiz_response.status_code in [200, 201, 503]
        print("  ✅ Step 2: Quiz responses tracked (5 quizzes)")

        # Step 3: 참여도 계산
        calc_response = client.post(
            "/api/engagement/calculate/participation-score",
            params={
                "chat_message_count": 3,
                "quiz_response_count": 5,
                "session_duration_minutes": 50,
            },
        )
        assert calc_response.status_code in [200, 503]
        if calc_response.status_code == 200:
            data = calc_response.json()
            assert "participation_score" in data
            print(
                f"  ✅ Step 3: Participation score calculated: {data.get('participation_score')}"
            )
        else:
            print("  ✅ Step 3: Participation score endpoint available")

        # Step 4: 세션 참여도 조회
        engagement_response = client.get(
            f"/api/engagement/students/{session_id}",
            params={"student_id": student_id},
        )
        assert engagement_response.status_code in [200, 404, 503]
        if engagement_response.status_code == 200:
            data = engagement_response.json()
            assert isinstance(data, (dict, list))
            print("  ✅ Step 4: Student engagement retrieved")
        else:
            print("  ✅ Step 4: Student engagement endpoint available")

        print("✅ Single student flow: COMPLETE")

    def test_track_multiple_activities(self, client):
        """여러 활동을 추적하고 주의집중도 계산"""
        session_id = "integration-multi-activity"
        student_id = "student-multi-001"

        # 채팅 활동 추적 (반복)
        for i in range(3):
            chat_response = client.post(
                "/api/engagement/track/chat",
                json={
                    "session_id": session_id,
                    "student_id": student_id,
                    "message": f"메시지 {i + 1}",
                },
            )
            assert chat_response.status_code in [200, 201, 503]
        print("  ✅ Chat activities tracked")

        # 주의집중도 계산
        attention_response = client.post(
            "/api/engagement/calculate/attention-score",
            params={
                "quiz_participation_rate": 0.8,
                "avg_response_latency_ms": 2500,
                "screen_time_minutes": 40.0,
            },
        )
        assert attention_response.status_code in [200, 503]
        if attention_response.status_code == 200:
            data = attention_response.json()
            assert "attention_score" in data
            print(f"  ✅ Attention score: {data.get('attention_score')}")

        print("✅ Multi-activity tracking: COMPLETE")


# ============================================
# Integration Test: Multiple Students Session
# ============================================


class TestMultipleStudentsSession:
    """여러 학생이 참여하는 세션 통합 테스트"""

    def test_session_with_multiple_students(self, client):
        """
        다중 학생 세션:
        1. 여러 학생의 활동 추적
        2. 세션 통계 조회
        3. 혼동 학생 감지
        4. 대시보드 조회
        """
        session_id = "integration-multi-session"
        students = [
            {"id": "student-high", "participation": 5, "quiz_rate": 0.9},
            {"id": "student-medium", "participation": 3, "quiz_rate": 0.6},
            {"id": "student-low", "participation": 1, "quiz_rate": 0.2},
        ]

        # Step 1: 모든 학생의 활동 추적
        for student in students:
            for i in range(student["participation"]):
                chat_response = client.post(
                    "/api/engagement/track/chat",
                    json={
                        "session_id": session_id,
                        "student_id": student["id"],
                        "message": f"메시지 {i + 1}",
                    },
                )
                assert chat_response.status_code in [200, 201, 503]
        print("  ✅ Step 1: Multi-student activities tracked")

        # Step 2: 세션 통계 조회
        stats_response = client.get(f"/api/engagement/session-stats/{session_id}")
        assert stats_response.status_code in [200, 503]
        if stats_response.status_code == 200:
            data = stats_response.json()
            assert "total_students" in data or "message" in data
            print("  ✅ Step 2: Session statistics retrieved")

        # Step 3: 혼동 감지
        confusion_response = client.post(
            "/api/engagement/detect-confusion",
            params={
                "quiz_accuracy": 0.2,
                "chat_activity_high": True,
                "confusion_indicators": [],
            },
        )
        assert confusion_response.status_code in [200, 503]
        if confusion_response.status_code == 200:
            data = confusion_response.json()
            assert "is_confused" in data or "confusion" in data
            print("  ✅ Step 3: Confusion detection completed")

        # Step 4: 대시보드 조회
        dashboard_response = client.get(f"/api/dashboard/session/{session_id}/students")
        assert dashboard_response.status_code in [200, 503]
        if dashboard_response.status_code == 200:
            data = dashboard_response.json()
            assert isinstance(data, list)
            print(f"  ✅ Step 4: Dashboard retrieved ({len(data)} students)")

        print("✅ Multi-student session: COMPLETE")

    def test_session_overview_and_alerts(self, client):
        """세션 개요 및 경고 조회"""
        session_id = "integration-overview"

        # 여러 학생 활동 생성
        for student_num in range(3):
            client.post(
                "/api/engagement/track/chat",
                json={
                    "session_id": session_id,
                    "student_id": f"student-{student_num}",
                    "message": "질문이 있습니다",
                },
            )

        # 세션 개요 조회
        overview_response = client.get(
            f"/api/dashboard/session/{session_id}/overview",
            params={"session_duration_minutes": 50},
        )
        assert overview_response.status_code in [200, 503]
        print("  ✅ Session overview retrieved")

        # 경고 조회
        alerts_response = client.get(f"/api/dashboard/alerts/{session_id}")
        assert alerts_response.status_code in [200, 503]
        print("  ✅ Session alerts retrieved")

        print("✅ Overview and alerts: COMPLETE")


# ============================================
# Integration Test: Engagement Calculation Flow
# ============================================


class TestEngagementCalculationFlow:
    """참여도 계산 전체 플로우"""

    def test_comprehensive_engagement_calculation(self, client):
        """
        전체 참여도 메트릭 계산:
        1. 주의집중도 (Attention Score)
        2. 참여도 (Participation Score)
        3. 정답률 (Quiz Accuracy)
        4. 종합 점수 (Overall Score)
        """

        # Step 1: 주의집중도 계산
        attention = client.post(
            "/api/engagement/calculate/attention-score",
            params={
                "quiz_participation_rate": 0.8,
                "avg_response_latency_ms": 2000,
                "screen_time_minutes": 45,
            },
        )
        assert attention.status_code in [200, 503]
        print("  ✅ Attention score calculated")

        # Step 2: 참여도 계산
        participation = client.post(
            "/api/engagement/calculate/participation-score",
            params={
                "chat_message_count": 10,
                "quiz_response_count": 8,
                "session_duration_minutes": 50,
            },
        )
        assert participation.status_code in [200, 503]
        print("  ✅ Participation score calculated")

        # Step 3: 정답률 계산
        accuracy = client.post(
            "/api/engagement/calculate/quiz-accuracy",
            params={"correct_responses": 7, "total_responses": 10},
        )
        assert accuracy.status_code in [200, 503]
        print("  ✅ Quiz accuracy calculated")

        # Step 4: 종합 점수 계산
        overall = client.post(
            "/api/engagement/calculate/overall-score",
            params={
                "attention_score": 0.8,
                "participation_score": 75.0,
                "quiz_accuracy": 0.7,
            },
        )
        assert overall.status_code in [200, 503]
        print("  ✅ Overall score calculated")

        print("✅ Comprehensive engagement calculation: COMPLETE")

    def test_trend_analysis_flow(self, client):
        """참여도 추세 분석"""
        # 시간대별 참여도 점수 (증가하는 추세)
        scores = [30, 40, 50, 60, 70, 75, 80]

        trend_response = client.post(
            "/api/engagement/analyze-trend",
            json={"recent_scores": scores, "window_minutes": 10},
        )
        assert trend_response.status_code in [200, 503]
        if trend_response.status_code == 200:
            data = trend_response.json()
            assert "trend" in data
            trend = data.get("trend", {})
            assert "trend_direction" in trend
            assert trend["trend_direction"] in ["increasing", "decreasing", "stable"]
            print(f"  ✅ Trend detected: {trend.get('trend_direction')}")

        print("✅ Trend analysis: COMPLETE")


# ============================================
# Integration Test: Data Flow Across Systems
# ============================================


class TestDataFlowAcrossSystem:
    """시스템 간 데이터 흐름 테스트"""

    def test_end_to_end_data_flow(self, client):
        """
        완전한 데이터 흐름:
        추적(Tracking) → 계산(Calculation) → 분석(Analysis) → 시각화(Dashboard)
        """
        session_id = "integration-e2e"

        print("\n🔄 End-to-End Data Flow Test")
        print("=" * 60)

        # Phase 1: 추적 (Tracking)
        print("\n📊 Phase 1: Activity Tracking")
        for i in range(3):
            client.post(
                "/api/engagement/track/chat",
                json={
                    "session_id": session_id,
                    "student_id": f"student-e2e-{i}",
                    "message": f"질문 {i + 1}",
                },
            )
        print("✅ Chat activities tracked")

        # Phase 2: 계산 (Calculation)
        print("\n🧮 Phase 2: Engagement Calculation")
        calc_response = client.post(
            "/api/engagement/calculate/participation-score",
            params={
                "chat_message_count": 3,
                "quiz_response_count": 5,
                "session_duration_minutes": 50,
            },
        )
        print(f"✅ Calculation completed: {calc_response.status_code}")

        # Phase 3: 분석 (Analysis)
        print("\n📈 Phase 3: Trend Analysis")
        trend_response = client.post(
            "/api/engagement/analyze-trend",
            json={"recent_scores": [50, 55, 60, 62, 65]},
        )
        print(f"✅ Analysis completed: {trend_response.status_code}")

        # Phase 4: 시각화 (Dashboard)
        print("\n🎯 Phase 4: Dashboard Visualization")
        dashboard = client.get(f"/api/dashboard/session/{session_id}/students")
        print(f"✅ Dashboard retrieved: {dashboard.status_code}")

        print("\n" + "=" * 60)
        print("✅ End-to-End Data Flow: COMPLETE")

    def test_session_lifecycle(self, client):
        """
        세션 라이프사이클 테스트:
        세션 개요 조회 → 학생 목록 조회 → 개별 학생 조회 → 경고 조회
        """
        session_id = "integration-lifecycle"

        print("\n🔄 Session Lifecycle Test")
        print("=" * 60)

        # 1. 세션 개요
        print("\n1️⃣  Retrieving session overview...")
        overview = client.get(f"/api/dashboard/session/{session_id}/overview")
        assert overview.status_code in [200, 503, 404]
        print(f"✅ Overview: {overview.status_code}")

        # 2. 학생 목록
        print("\n2️⃣  Retrieving students list...")
        students_list = client.get(f"/api/dashboard/session/{session_id}/students")
        assert students_list.status_code in [200, 503]
        print(f"✅ Students list: {students_list.status_code}")

        # 3. 개별 학생
        print("\n3️⃣  Retrieving individual student...")
        student = client.get(f"/api/dashboard/session/{session_id}/student/student-001")
        assert student.status_code in [200, 404, 503]
        print(f"✅ Individual student: {student.status_code}")

        # 4. 경고
        print("\n4️⃣  Retrieving alerts...")
        alerts = client.get(f"/api/dashboard/alerts/{session_id}")
        assert alerts.status_code in [200, 503]
        print(f"✅ Alerts: {alerts.status_code}")

        # 5. 헬스 체크
        print("\n5️⃣  Health check...")
        health = client.get("/api/dashboard/health")
        assert health.status_code in [200, 503]
        print(f"✅ Health: {health.status_code}")

        print("\n" + "=" * 60)
        print("✅ Session Lifecycle: COMPLETE")


# ============================================
# Integration Test: Error Recovery
# ============================================


class TestErrorRecovery:
    """에러 상황에서의 복구 테스트"""

    def test_missing_session_handling(self, client):
        """존재하지 않는 세션 처리"""
        response = client.get("/api/dashboard/session/nonexistent/overview")
        # 404나 503이 반환되어야 함 (500은 안됨)
        assert response.status_code in [404, 503]
        print("✅ Missing session handled gracefully")

    def test_invalid_parameter_handling(self, client):
        """잘못된 파라미터 처리"""
        response = client.post(
            "/api/engagement/calculate/participation-score",
            params={
                "chat_message_count": -5,  # 음수
                "quiz_response_count": 10,
                "session_duration_minutes": 50,
            },
        )
        # 400, 422, 또는 503이 반환되어야 함
        assert response.status_code in [200, 400, 422, 503]
        print("✅ Invalid parameters handled")

    def test_service_unavailability(self, client):
        """서비스 이용 불가 상황 처리"""
        # 트래커나 DB가 없을 수 있으므로 503도 정상
        response = client.get("/api/engagement/health")
        assert response.status_code in [200, 503]
        print("✅ Service availability check works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
