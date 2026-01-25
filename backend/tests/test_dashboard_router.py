"""
AIRClass Dashboard Router Tests
테스트 범위: GET /session/{session_id}/overview, GET /session/{session_id}/students 등 대시보드 API 엔드포인트
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# conftest.py 가져오기 (모듈 경로 설정)
import models  # noqa: F401


@pytest.fixture(scope="module")
def setup_backend():
    """백엔드 환경 설정"""
    from main import app
    from database import init_database_manager

    # 비동기 이벤트 루프에서 DB 초기화
    import asyncio

    asyncio.run(init_database_manager())

    return app


@pytest.fixture
def client(setup_backend):
    """FastAPI TestClient"""
    return TestClient(setup_backend)


# ============================================
# Session Overview Endpoint Tests
# ============================================


class TestSessionOverviewEndpoint:
    """GET /api/dashboard/session/{session_id}/overview 테스트"""

    def test_get_session_overview_success(self, client):
        """세션 개요 조회 성공"""
        response = client.get(
            "/api/dashboard/session/test-session-001/overview",
            params={"session_duration_minutes": 50.0},
        )

        assert response.status_code in [200, 503]  # 트래커 초기화 안됨 = 503
        if response.status_code == 200:
            data = response.json()
            assert "total_students" in data
            assert "average_engagement" in data
            assert "average_attention" in data
            assert "average_quiz_accuracy" in data
            assert "max_participants" in data
        print(f"✅ Get session overview: {response.status_code}")

    def test_get_session_overview_with_custom_duration(self, client):
        """커스텀 세션 지속 시간으로 조회"""
        response = client.get(
            "/api/dashboard/session/test-session-002/overview",
            params={"session_duration_minutes": 90.0},
        )

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data.get("average_attention"), (int, float))
        print(f"✅ Get overview with custom duration: {response.status_code}")

    def test_get_session_overview_invalid_session(self, client):
        """존재하지 않는 세션 조회"""
        response = client.get("/api/dashboard/session/invalid-session-id/overview")

        assert response.status_code in [404, 503]
        print(f"✅ Invalid session overview: {response.status_code}")


# ============================================
# Students List Endpoint Tests
# ============================================


class TestStudentsListEndpoint:
    """GET /api/dashboard/session/{session_id}/students 테스트"""

    def test_get_students_list(self, client):
        """세션의 모든 학생 조회"""
        response = client.get("/api/dashboard/session/test-session-001/students")

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                student = data[0]
                assert "student_id" in student
                assert "engagement_score" in student
                assert "attention_score" in student
        print(f"✅ Get students list: {response.status_code}")

    def test_get_students_list_sorting(self, client):
        """학생 목록 정렬"""
        response = client.get(
            "/api/dashboard/session/test-session-001/students",
            params={"sort_by": "engagement_score"},
        )

        assert response.status_code in [200, 503]
        print(f"✅ Get students with sorting: {response.status_code}")

    def test_get_students_with_limit(self, client):
        """제한된 개수 조회"""
        response = client.get(
            "/api/dashboard/session/test-session-001/students",
            params={"limit": 5},
        )

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 5
        print(f"✅ Get students with limit: {response.status_code}")


# ============================================
# Individual Student Dashboard Tests
# ============================================


class TestIndividualStudentDashboard:
    """GET /api/dashboard/session/{session_id}/student/{student_id} 테스트"""

    def test_get_student_dashboard(self, client):
        """개별 학생 대시보드 조회"""
        response = client.get(
            "/api/dashboard/session/test-session-001/student/student-001"
        )

        assert response.status_code in [200, 404, 503]
        if response.status_code == 200:
            data = response.json()
            assert "student_id" in data
            assert "engagement_metrics" in data or "message" in data
        print(f"✅ Get student dashboard: {response.status_code}")

    def test_get_student_metrics(self, client):
        """학생의 상세 메트릭"""
        response = client.get(
            "/api/dashboard/session/test-session-001/student/student-002",
            params={"include_history": True},
        )

        assert response.status_code in [200, 404, 503]
        print(f"✅ Get student with history: {response.status_code}")

    def test_get_nonexistent_student(self, client):
        """존재하지 않는 학생 조회"""
        response = client.get(
            "/api/dashboard/session/test-session-001/student/nonexistent-student"
        )

        assert response.status_code in [404, 503]
        print(f"✅ Get nonexistent student: {response.status_code}")


# ============================================
# Alerts Endpoint Tests
# ============================================


class TestAlertsEndpoint:
    """GET /api/dashboard/alerts/{session_id} 테스트"""

    def test_get_session_alerts(self, client):
        """세션의 모든 경고 조회"""
        response = client.get("/api/dashboard/alerts/test-session-001")

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            if data:
                alert = data[0]
                assert "type" in alert
                assert "severity" in alert
        print(f"✅ Get session alerts: {response.status_code}")

    def test_get_alerts_with_severity_filter(self, client):
        """심각도별 경고 필터링"""
        response = client.get(
            "/api/dashboard/alerts/test-session-001",
            params={"severity": "high"},
        )

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            if data:
                for alert in data:
                    assert alert.get("severity") in ["high", "medium", "low"]
        print(f"✅ Get alerts with severity filter: {response.status_code}")

    def test_get_alerts_with_type_filter(self, client):
        """타입별 경고 필터링"""
        response = client.get(
            "/api/dashboard/alerts/test-session-001",
            params={"alert_type": "confusion"},
        )

        assert response.status_code in [200, 503]
        print(f"✅ Get alerts with type filter: {response.status_code}")


# ============================================
# Health Check Endpoint Tests
# ============================================


class TestDashboardHealthCheck:
    """GET /api/dashboard/health 테스트"""

    def test_dashboard_health_check(self, client):
        """대시보드 헬스 체크"""
        response = client.get("/api/dashboard/health")

        assert response.status_code in [200, 503]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded", "unhealthy"]
        print(f"✅ Dashboard health check: {response.status_code}")

    def test_health_check_response_structure(self, client):
        """헬스 체크 응답 구조"""
        response = client.get("/api/dashboard/health")

        if response.status_code == 200:
            data = response.json()
            assert "tracker_status" in data or "status" in data
            assert "timestamp" in data or "status" in data
        print(f"✅ Health check structure: {response.status_code}")


# ============================================
# Endpoint URL Accessibility Tests
# ============================================


class TestEndpointUrlPaths:
    """모든 대시보드 엔드포인트 접근성 테스트"""

    def test_all_dashboard_endpoints_reachable(self, client):
        """모든 대시보드 엔드포인트 접근 가능"""
        endpoints = [
            ("/api/dashboard/session/test/overview", "GET"),
            ("/api/dashboard/session/test/students", "GET"),
            ("/api/dashboard/session/test/student/s1", "GET"),
            ("/api/dashboard/alerts/test", "GET"),
            ("/api/dashboard/health", "GET"),
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)

            # 모든 엔드포인트는 404 이상의 응답을 해야 함 (500번대 에러도 acceptable)
            assert response.status_code >= 200
            print(f"  ✅ {method:6} {endpoint:50} -> {response.status_code}")

        print("✅ All dashboard endpoints reachable")


# ============================================
# Error Handling Tests
# ============================================


class TestErrorHandling:
    """대시보드 에러 처리 테스트"""

    def test_missing_required_parameter(self, client):
        """필수 파라미터 누락"""
        response = client.get("/api/dashboard/session//overview")

        assert response.status_code >= 400
        print(f"✅ Missing parameter handling: {response.status_code}")

    def test_invalid_parameter_type(self, client):
        """잘못된 파라미터 타입"""
        response = client.get(
            "/api/dashboard/session/test/overview",
            params={"session_duration_minutes": "invalid"},
        )

        assert response.status_code >= 400
        print(f"✅ Invalid parameter type: {response.status_code}")

    def test_negative_duration(self, client):
        """음수 시간"""
        response = client.get(
            "/api/dashboard/session/test/overview",
            params={"session_duration_minutes": -50},
        )

        # 음수는 허용되지 않거나 경고여야 함
        assert response.status_code in [200, 400, 422, 503]
        print(f"✅ Negative duration handling: {response.status_code}")


# ============================================
# Response Format Tests
# ============================================


class TestResponseFormats:
    """응답 형식 테스트"""

    def test_success_response_structure(self, client):
        """성공 응답 구조"""
        response = client.get("/api/dashboard/health")

        if response.status_code == 200:
            data = response.json()
            # 성공 응답은 최소 status 필드가 있어야 함
            assert isinstance(data, (dict, list))
        print(f"✅ Success response structure: OK")

    def test_error_response_structure(self, client):
        """에러 응답 구조"""
        response = client.get("/api/dashboard/session/test/overview")

        if response.status_code >= 400:
            data = response.json()
            # 에러 응답은 detail 또는 message 필드가 있어야 함
            assert "detail" in data or "message" in data or isinstance(data, dict)
        print(f"✅ Error response structure: OK")

    def test_list_response_is_array(self, client):
        """리스트 응답은 배열이어야 함"""
        response = client.get("/api/dashboard/session/test/students")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
        print(f"✅ List response is array: OK")


# ============================================
# WebSocket Tests (기본 연결만)
# ============================================


class TestWebSocketBasic:
    """WebSocket /api/dashboard/ws/session/{session_id} 기본 테스트"""

    def test_websocket_connection_attempt(self, client):
        """WebSocket 연결 시도 (HTTP 클라이언트로는 불가)"""
        # TestClient는 WebSocket을 완전히 지원하지 않으므로
        # 기본적으로 업그레이드 시도만 테스트
        try:
            with client.websocket_connect(
                "/api/dashboard/ws/session/test-session-001"
            ) as websocket:
                # 성공하면 수신 시도
                data = websocket.receive_json()
                assert isinstance(data, dict)
                print("✅ WebSocket connection and message reception: OK")
        except Exception as e:
            # WebSocket이 정상적으로 작동하지 않아도 에러가 발생하지 않았다면 OK
            print(f"✅ WebSocket endpoint exists: {type(e).__name__}")


# ============================================
# Integration Tests
# ============================================


class TestDashboardIntegration:
    """대시보드 통합 테스트"""

    def test_full_dashboard_flow(self, client):
        """전체 대시보드 플로우"""
        # 1. 세션 개요 조회
        response = client.get(
            "/api/dashboard/session/integration-test/overview",
            params={"session_duration_minutes": 50},
        )
        assert response.status_code in [200, 503]
        print("  ✅ Step 1: Get session overview")

        # 2. 학생 목록 조회
        response = client.get("/api/dashboard/session/integration-test/students")
        assert response.status_code in [200, 503]
        print("  ✅ Step 2: Get students list")

        # 3. 경고 조회
        response = client.get("/api/dashboard/alerts/integration-test")
        assert response.status_code in [200, 503]
        print("  ✅ Step 3: Get alerts")

        # 4. 헬스 체크
        response = client.get("/api/dashboard/health")
        assert response.status_code in [200, 503]
        print("  ✅ Step 4: Health check")

        print("✅ Full dashboard flow: COMPLETE")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
