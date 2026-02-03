"""
Recording Router Tests
녹화 관리 API 테스트
"""

import pytest
from httpx import AsyncClient
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, UTC


# ============================================
# Mock Setup
# ============================================


@pytest.fixture
def mock_recording_manager():
    """RecordingManager 모킹"""
    manager = Mock()

    # start_recording 모킹
    manager.start_recording.return_value = {
        "recording_id": "test_session_20250203_120000",
        "status": "recording",
        "file_path": "/storage/vod/test_session_20250203_120000.mp4",
        "started_at": datetime.now(UTC).isoformat(),
    }

    # stop_recording 모킹
    manager.stop_recording.return_value = {
        "recording_id": "test_session_20250203_120000",
        "status": "completed",
        "file_path": "/storage/vod/test_session_20250203_120000.mp4",
        "duration_seconds": 120,
        "file_size_mb": 50.5,
    }

    # get_recording_status 모킹
    manager.get_recording_status.return_value = {
        "recording_id": "test_session_20250203_120000",
        "status": "recording",
        "file_size_mb": 25.3,
        "started_at": datetime.now(UTC).isoformat(),
    }

    # list_recordings 모킹
    manager.list_recordings.return_value = [
        {
            "recording_id": "test_session_20250203_120000",
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
            "duration_seconds": 120,
            "file_size_mb": 50.5,
        }
    ]

    # get_all_recordings 모킹
    manager.get_all_recordings.return_value = [
        {
            "recording_id": "test_session_20250203_120000",
            "session_id": "test_session",
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
        }
    ]

    # delete_recording 모킹
    manager.delete_recording.return_value = {
        "recording_id": "test_session_20250203_120000",
        "status": "deleted",
        "deleted_at": datetime.now(UTC).isoformat(),
    }

    return manager


# ============================================
# Health Check Tests
# ============================================


@pytest.mark.asyncio
async def test_health_check_success(async_client: AsyncClient, mock_recording_manager):
    """녹화 시스템 헬스체크 성공 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.get("/api/recording/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_manager_not_initialized(async_client: AsyncClient):
    """RecordingManager 미초기화 헬스체크 테스트"""
    with patch("routers.recording.get_recording_manager", return_value=None):
        response = await async_client.get("/api/recording/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "reason" in data


# ============================================
# Start Recording Tests
# ============================================


@pytest.mark.asyncio
async def test_start_recording_success(
    async_client: AsyncClient, mock_recording_manager
):
    """녹화 시작 성공 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.post(
            "/api/recording/start",
            params={
                "session_id": "test_session",
                "stream_url": "rtmp://localhost/live/test",
                "output_format": "mp4",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recording"
        assert "recording_id" in data
        assert "file_path" in data
        assert "started_at" in data


@pytest.mark.asyncio
async def test_start_recording_default_format(
    async_client: AsyncClient, mock_recording_manager
):
    """기본 형식으로 녹화 시작 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.post(
            "/api/recording/start",
            params={
                "session_id": "test_session",
                "stream_url": "rtmp://localhost/live/test",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recording"


@pytest.mark.asyncio
async def test_start_recording_manager_error(
    async_client: AsyncClient, mock_recording_manager
):
    """RecordingManager 에러 시 녹화 시작 테스트"""
    mock_recording_manager.start_recording.return_value = {
        "status": "error",
        "error": "Failed to start ffmpeg",
    }

    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.post(
            "/api/recording/start",
            params={
                "session_id": "test_session",
                "stream_url": "rtmp://localhost/live/test",
            },
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_start_recording_manager_not_initialized(async_client: AsyncClient):
    """RecordingManager 미초기화 시 녹화 시작 테스트"""
    with patch("routers.recording.get_recording_manager", return_value=None):
        response = await async_client.post(
            "/api/recording/start",
            params={
                "session_id": "test_session",
                "stream_url": "rtmp://localhost/live/test",
            },
        )

        assert response.status_code == 503


# ============================================
# Stop Recording Tests
# ============================================


@pytest.mark.asyncio
async def test_stop_recording_success(
    async_client: AsyncClient, mock_recording_manager
):
    """녹화 중지 성공 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.post(
            "/api/recording/stop",
            params={"recording_id": "test_session_20250203_120000"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["recording_id"] == "test_session_20250203_120000"
        assert "duration_seconds" in data
        assert "file_size_mb" in data


@pytest.mark.asyncio
async def test_stop_recording_not_found(
    async_client: AsyncClient, mock_recording_manager
):
    """존재하지 않는 녹화 중지 테스트"""
    mock_recording_manager.stop_recording.return_value = {
        "status": "error",
        "error": "Recording not found",
    }

    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.post(
            "/api/recording/stop", params={"recording_id": "nonexistent_recording"}
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_stop_recording_manager_not_initialized(async_client: AsyncClient):
    """RecordingManager 미초기화 시 녹화 중지 테스트"""
    with patch("routers.recording.get_recording_manager", return_value=None):
        response = await async_client.post(
            "/api/recording/stop",
            params={"recording_id": "test_session_20250203_120000"},
        )

        assert response.status_code == 503


# ============================================
# Get Recording Status Tests
# ============================================


@pytest.mark.asyncio
async def test_get_recording_status_success(
    async_client: AsyncClient, mock_recording_manager
):
    """녹화 상태 조회 성공 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.get(
            "/api/recording/test_session_20250203_120000/status"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recording_id"] == "test_session_20250203_120000"
        assert data["status"] == "recording"
        assert "file_size_mb" in data
        assert "started_at" in data


@pytest.mark.asyncio
async def test_get_recording_status_not_found(
    async_client: AsyncClient, mock_recording_manager
):
    """존재하지 않는 녹화 상태 조회 테스트"""
    mock_recording_manager.get_recording_status.return_value = {
        "status": "error",
        "error": "Recording not found",
    }

    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.get("/api/recording/nonexistent_recording/status")

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_recording_status_manager_not_initialized(async_client: AsyncClient):
    """RecordingManager 미초기화 시 녹화 상태 조회 테스트"""
    with patch("routers.recording.get_recording_manager", return_value=None):
        response = await async_client.get(
            "/api/recording/test_session_20250203_120000/status"
        )

        assert response.status_code == 503


# ============================================
# List Recordings Tests
# ============================================


@pytest.mark.asyncio
async def test_list_session_recordings_success(
    async_client: AsyncClient, mock_recording_manager
):
    """세션별 녹화 목록 조회 성공 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.get("/api/recording/session/test_session")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "recording_id" in data[0]
            assert "status" in data[0]
            assert "created_at" in data[0]


@pytest.mark.asyncio
async def test_list_session_recordings_empty(
    async_client: AsyncClient, mock_recording_manager
):
    """빈 세션 녹화 목록 조회 테스트"""
    mock_recording_manager.list_recordings.return_value = []

    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.get("/api/recording/session/empty_session")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


@pytest.mark.asyncio
async def test_list_session_recordings_manager_not_initialized(
    async_client: AsyncClient,
):
    """RecordingManager 미초기화 시 세션 녹화 목록 조회 테스트"""
    with patch("routers.recording.get_recording_manager", return_value=None):
        response = await async_client.get("/api/recording/session/test_session")

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_list_all_recordings_success(
    async_client: AsyncClient, mock_recording_manager
):
    """전체 녹화 목록 조회 성공 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.get("/api/recording")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "recording_id" in data[0]
            assert "session_id" in data[0]
            assert "status" in data[0]
            assert "created_at" in data[0]


@pytest.mark.asyncio
async def test_list_all_recordings_empty(
    async_client: AsyncClient, mock_recording_manager
):
    """빈 전체 녹화 목록 조회 테스트"""
    mock_recording_manager.get_all_recordings.return_value = []

    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.get("/api/recording")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


@pytest.mark.asyncio
async def test_list_all_recordings_manager_not_initialized(async_client: AsyncClient):
    """RecordingManager 미초기화 시 전체 녹화 목록 조회 테스트"""
    with patch("routers.recording.get_recording_manager", return_value=None):
        response = await async_client.get("/api/recording")

        assert response.status_code == 503


# ============================================
# Delete Recording Tests
# ============================================


@pytest.mark.asyncio
async def test_delete_recording_success(
    async_client: AsyncClient, mock_recording_manager
):
    """녹화 삭제 성공 테스트"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.delete(
            "/api/recording/test_session_20250203_120000"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["recording_id"] == "test_session_20250203_120000"
        assert "deleted_at" in data


@pytest.mark.asyncio
async def test_delete_recording_not_found(
    async_client: AsyncClient, mock_recording_manager
):
    """존재하지 않는 녹화 삭제 테스트"""
    mock_recording_manager.delete_recording.return_value = {
        "status": "error",
        "error": "Recording not found",
    }

    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        response = await async_client.delete("/api/recording/nonexistent_recording")

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_recording_manager_not_initialized(async_client: AsyncClient):
    """RecordingManager 미초기화 시 녹화 삭제 테스트"""
    with patch("routers.recording.get_recording_manager", return_value=None):
        response = await async_client.delete(
            "/api/recording/test_session_20250203_120000"
        )

        assert response.status_code == 503


# ============================================
# Integration Tests
# ============================================


@pytest.mark.asyncio
async def test_recording_lifecycle(async_client: AsyncClient, mock_recording_manager):
    """녹화 전체 라이프사이클 테스트 (시작 → 상태 조회 → 중지 → 삭제)"""
    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        # 1. 녹화 시작
        start_response = await async_client.post(
            "/api/recording/start",
            params={
                "session_id": "lifecycle_test",
                "stream_url": "rtmp://localhost/live/test",
            },
        )
        assert start_response.status_code == 200
        recording_id = start_response.json()["recording_id"]

        # 2. 상태 조회
        status_response = await async_client.get(
            f"/api/recording/{recording_id}/status"
        )
        assert status_response.status_code == 200

        # 3. 녹화 중지
        stop_response = await async_client.post(
            "/api/recording/stop", params={"recording_id": recording_id}
        )
        assert stop_response.status_code == 200

        # 4. 삭제
        delete_response = await async_client.delete(f"/api/recording/{recording_id}")
        assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_multiple_recordings_same_session(
    async_client: AsyncClient, mock_recording_manager
):
    """같은 세션에 여러 녹화 생성 테스트"""
    mock_recording_manager.list_recordings.return_value = [
        {
            "recording_id": "test_session_20250203_120000",
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
            "duration_seconds": 120,
        },
        {
            "recording_id": "test_session_20250203_130000",
            "status": "recording",
            "created_at": datetime.now(UTC).isoformat(),
        },
    ]

    with patch(
        "routers.recording.get_recording_manager", return_value=mock_recording_manager
    ):
        # 세션별 녹화 목록 조회
        response = await async_client.get("/api/recording/session/test_session")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
