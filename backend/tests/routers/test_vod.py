"""
VOD Router Tests
비디오 재생 및 관리 API 테스트
"""

import pytest
from httpx import AsyncClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC


# ============================================
# Mock Setup
# ============================================


@pytest.fixture(autouse=True)
async def vod_override(app, mock_vod_storage):
    """VOD 의존성 주입 오버라이드 - 모든 테스트에서 자동 적용"""
    from routers import vod

    app.dependency_overrides[vod.get_storage] = lambda: mock_vod_storage
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_vod_storage():
    """VODStorage 모킹"""
    storage = Mock()

    # get_video_info 모킹
    storage.get_video_info.return_value = {
        "video_id": "test_video_123",
        "title": "Test Video",
        "description": "Test Description",
        "teacher_name": "John Doe",
        "student_count": 30,
        "duration_seconds": 3600,
        "width": 1920,
        "height": 1080,
        "codec": "h264",
        "bitrate_kbps": 2500,
        "fps": 30,
        "created_at": datetime.now(UTC).isoformat(),
        "available_resolutions": ["720p", "480p"],
        "thumbnail": "/storage/vod/test_video_123_thumb.jpg",
    }

    # list_videos_by_session 모킹
    storage.list_videos_by_session.return_value = [
        {
            "video_id": "test_video_1",
            "title": "Session Video 1",
            "duration_seconds": 1800,
            "teacher_name": "John Doe",
            "created_at": datetime.now(UTC).isoformat(),
            "thumbnail": "/storage/vod/test_video_1_thumb.jpg",
        }
    ]

    # search_videos 모킹
    storage.search_videos.return_value = [
        {
            "video_id": "test_video_search",
            "title": "Search Result Video",
            "teacher_name": "Jane Smith",
            "duration_seconds": 2400,
            "created_at": datetime.now(UTC).isoformat(),
            "thumbnail": "/storage/vod/test_video_search_thumb.jpg",
        }
    ]

    # delete_video 모킹
    storage.delete_video.return_value = {
        "video_id": "test_video_123",
        "status": "deleted",
        "deleted_at": datetime.now(UTC).isoformat(),
    }

    return storage


# ============================================
# Health Check Tests
# ============================================


@pytest.mark.asyncio
async def test_health_check_success(async_client: AsyncClient, mock_vod_storage):
    """VOD 시스템 헬스체크 성공 테스트"""
    # Health check는 get_vod_storage()를 직접 호출하므로 별도 패치 필요
    with patch("routers.vod.get_vod_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_storage_not_initialized(async_client: AsyncClient):
    """VODStorage 미초기화 헬스체크 테스트"""
    with patch("routers.vod.get_vod_storage", return_value=None):
        response = await async_client.get("/api/vod/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "reason" in data


# ============================================
# Get Video Info Tests
# ============================================


@pytest.mark.asyncio
async def test_get_video_info_success(async_client: AsyncClient):
    """비디오 정보 조회 성공 테스트"""
    response = await async_client.get("/api/vod/test_video_123/info")

    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "test_video_123"
    assert data["title"] == "Test Video"
    assert data["duration_seconds"] == 3600
    assert "available_resolutions" in data
    assert "720p" in data["available_resolutions"]


@pytest.mark.asyncio
async def test_get_video_info_not_found(async_client: AsyncClient, mock_vod_storage):
    """존재하지 않는 비디오 정보 조회 테스트"""
    mock_vod_storage.get_video_info.return_value = {
        "video_id": "nonexistent",
        "status": "error",
        "error": "Video not found",
    }

    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/nonexistent/info")

        assert response.status_code == 404


# ============================================
# List Videos Tests
# ============================================


@pytest.mark.asyncio
async def test_list_session_vods_success(async_client: AsyncClient):
    """세션별 VOD 목록 조회 성공 테스트"""
    response = await async_client.get("/api/vod/session/test_session")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "video_id" in data[0]
        assert "title" in data[0]
        assert "duration_seconds" in data[0]


@pytest.mark.asyncio
async def test_list_session_vods_with_pagination(async_client: AsyncClient):
    """페이지네이션 포함 세션 VOD 목록 조회 테스트"""
    response = await async_client.get("/api/vod/session/test_session?limit=5&offset=10")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_session_vods_empty(async_client: AsyncClient, mock_vod_storage):
    """빈 세션 VOD 목록 조회 테스트"""
    mock_vod_storage.list_videos_by_session.return_value = []

    response = await async_client.get("/api/vod/session/empty_session")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


# ============================================
# Video Stream Tests
# ============================================


@pytest.mark.asyncio
async def test_stream_video_success(async_client: AsyncClient, mock_vod_storage):
    """비디오 스트림 성공 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/test_video_123/stream")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "streaming"
        assert data["video_id"] == "test_video_123"
        assert "resolution" in data


@pytest.mark.asyncio
async def test_stream_video_with_resolution(
    async_client: AsyncClient, mock_vod_storage
):
    """특정 해상도로 비디오 스트림 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get(
            "/api/vod/test_video_123/stream?resolution=480p"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["resolution"] == "480p"


@pytest.mark.asyncio
async def test_stream_video_with_time_range(
    async_client: AsyncClient, mock_vod_storage
):
    """시간 범위 지정 비디오 스트림 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get(
            "/api/vod/test_video_123/stream?start=60&end=120"
        )

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_stream_video_not_found(async_client: AsyncClient, mock_vod_storage):
    """존재하지 않는 비디오 스트림 테스트"""
    # 404를 반환하도록 설정
    mock_vod_storage.get_video_info.return_value = {
        "status": "error",
        "error": "Video not found",
    }

    response = await async_client.get("/api/vod/nonexistent/stream")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_thumbnail_not_found_video(
    async_client: AsyncClient, mock_vod_storage
):
    """존재하지 않는 비디오의 썸네일 조회 테스트"""
    # 404를 반환하도록 설정
    mock_vod_storage.get_video_info.return_value = {
        "status": "error",
        "error": "Video not found",
    }

    response = await async_client.get("/api/vod/nonexistent/thumbnail")
    assert response.status_code == 404


# ============================================
# Thumbnail Tests (이미 위에 test_get_thumbnail_not_found_video 존재)
# ============================================


# ============================================
# Search Videos Tests
# ============================================


@pytest.mark.asyncio
async def test_search_videos_by_query(async_client: AsyncClient, mock_vod_storage):
    """검색어로 비디오 검색 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/search?query=test")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_videos_by_teacher(async_client: AsyncClient, mock_vod_storage):
    """교사명으로 비디오 검색 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/search?teacher_name=John+Doe")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_videos_by_date_range(async_client: AsyncClient, mock_vod_storage):
    """날짜 범위로 비디오 검색 테스트"""
    date_from = "2025-01-01T00:00:00Z"
    date_to = "2025-12-31T23:59:59Z"

    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get(
            f"/api/vod/search?date_from={date_from}&date_to={date_to}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_videos_with_limit(async_client: AsyncClient, mock_vod_storage):
    """결과 제한 포함 비디오 검색 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/search?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_search_videos_empty_result(async_client: AsyncClient, mock_vod_storage):
    """빈 검색 결과 테스트"""
    mock_vod_storage.search_videos.return_value = []

    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/search?query=nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


# ============================================
# Delete Video Tests
# ============================================


@pytest.mark.asyncio
async def test_delete_video_success(async_client: AsyncClient, mock_vod_storage):
    """비디오 삭제 성공 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.delete("/api/vod/test_video_123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["video_id"] == "test_video_123"
        assert "deleted_at" in data


@pytest.mark.asyncio
async def test_delete_video_not_found(async_client: AsyncClient, mock_vod_storage):
    """존재하지 않는 비디오 삭제 테스트"""
    mock_vod_storage.delete_video.return_value = {
        "video_id": "nonexistent",
        "status": "error",
        "error": "Video not found",
    }

    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.delete("/api/vod/nonexistent")

        assert response.status_code == 400


# ============================================
# Chapters Management Tests
# ============================================


@pytest.mark.asyncio
async def test_add_chapter_success(async_client: AsyncClient, mock_vod_storage):
    """챕터 추가 성공 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.post(
            "/api/vod/test_video_123/chapters",
            params={
                "start_time": 60,
                "title": "Chapter 1",
                "description": "Introduction",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["start_time"] == 60
        assert data["title"] == "Chapter 1"
        assert "chapter_id" in data


@pytest.mark.asyncio
async def test_add_chapter_without_description(
    async_client: AsyncClient, mock_vod_storage
):
    """설명 없이 챕터 추가 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.post(
            "/api/vod/test_video_123/chapters",
            params={"start_time": 120, "title": "Chapter 2"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"


@pytest.mark.asyncio
async def test_get_chapters_success(async_client: AsyncClient, mock_vod_storage):
    """챕터 목록 조회 성공 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/test_video_123/chapters")

        assert response.status_code == 200
        data = response.json()
        assert "video_id" in data
        assert "chapters" in data
        assert isinstance(data["chapters"], list)


@pytest.mark.asyncio
async def test_get_chapters_empty(async_client: AsyncClient, mock_vod_storage):
    """빈 챕터 목록 조회 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        response = await async_client.get("/api/vod/test_video_123/chapters")

        assert response.status_code == 200
        data = response.json()
        assert len(data["chapters"]) == 0


# ============================================
# Integration Tests
# ============================================


@pytest.mark.asyncio
async def test_video_lifecycle(async_client: AsyncClient, mock_vod_storage):
    """비디오 전체 라이프사이클 테스트 (정보 조회 → 스트림 → 챕터 추가 → 삭제)"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        video_id = "test_video_lifecycle"

        # 1. 비디오 정보 조회
        info_response = await async_client.get(f"/api/vod/{video_id}/info")
        assert info_response.status_code == 200

        # 2. 비디오 스트림
        stream_response = await async_client.get(f"/api/vod/{video_id}/stream")
        assert stream_response.status_code == 200

        # 3. 챕터 추가
        chapter_response = await async_client.post(
            f"/api/vod/{video_id}/chapters",
            params={"start_time": 30, "title": "Test Chapter"},
        )
        assert chapter_response.status_code == 200

        # 4. 챕터 목록 조회
        chapters_response = await async_client.get(f"/api/vod/{video_id}/chapters")
        assert chapters_response.status_code == 200

        # 5. 비디오 삭제
        delete_response = await async_client.delete(f"/api/vod/{video_id}")
        assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_search_and_filter_workflow(async_client: AsyncClient, mock_vod_storage):
    """검색 및 필터링 워크플로우 테스트"""
    with patch("routers.vod.get_storage", return_value=mock_vod_storage):
        # 1. 전체 검색
        all_response = await async_client.get("/api/vod/search")
        assert all_response.status_code == 200

        # 2. 제목으로 검색
        title_response = await async_client.get("/api/vod/search?query=test")
        assert title_response.status_code == 200

        # 3. 교사명으로 검색
        teacher_response = await async_client.get(
            "/api/vod/search?teacher_name=John+Doe"
        )
        assert teacher_response.status_code == 200

        # 4. 날짜 범위로 검색
        date_response = await async_client.get(
            "/api/vod/search?date_from=2025-01-01T00:00:00Z"
        )
        assert date_response.status_code == 200
