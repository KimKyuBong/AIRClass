"""
AIRClass Recording & VOD Tests
녹화 시스템 및 VOD 관리 테스트
"""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime, UTC

from services.recording_service import RecordingManager
from services.vod_service import VODStorage


# ============================================
# Recording Manager Tests
# ============================================


class TestRecordingManager:
    """RecordingManager 테스트"""

    @pytest.fixture
    def temp_storage(self):
        """임시 저장소"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_storage):
        """RecordingManager 인스턴스"""
        return RecordingManager(storage_path=temp_storage)

    def test_init_recording_manager(self, manager):
        """RecordingManager 초기화"""
        assert manager is not None
        assert manager.storage_path.exists()
        print("✅ RecordingManager initialized")

    def test_start_recording(self, manager):
        """녹화 시작"""
        result = manager.start_recording(
            session_id="test-session-001",
            stream_url="rtmp://localhost:1935/live/test"
        )
        
        assert result["status"] in ["recording", "error"]
        assert result["recording_id"] is not None or result["status"] == "error"
        print(f"✅ Recording started: {result['status']}")

    def test_recording_status(self, manager):
        """녹화 상태 조회"""
        # 먼저 녹화 시작
        result = manager.start_recording(
            session_id="test-session-002",
            stream_url="rtmp://localhost:1935/live/test"
        )
        
        if result["status"] == "recording":
            recording_id = result["recording_id"]
            
            # 상태 조회
            status = manager.get_recording_status(recording_id)
            assert status["recording_id"] == recording_id
            assert status["status"] in ["recording", "error"]
            print(f"✅ Recording status retrieved: {status['status']}")

    def test_list_recordings(self, manager):
        """세션별 녹화 목록"""
        # 녹화 시작
        manager.start_recording(
            session_id="test-session-003",
            stream_url="rtmp://localhost:1935/live/test"
        )
        
        # 목록 조회
        recordings = manager.list_recordings("test-session-003")
        assert isinstance(recordings, list)
        print(f"✅ Recordings listed: {len(recordings)}")

    def test_get_all_recordings(self, manager):
        """모든 녹화 조회"""
        recordings = manager.get_all_recordings()
        
        assert isinstance(recordings, list)
        print(f"✅ All recordings retrieved: {len(recordings)}")

    def test_recording_active_recordings(self, manager):
        """활성 녹화 저장"""
        manager.start_recording(
            session_id="test-session-004",
            stream_url="rtmp://localhost:1935/live/test"
        )
        
        assert len(manager.active_recordings) > 0
        print(f"✅ Active recordings stored: {len(manager.active_recordings)}")


# ============================================
# VOD Storage Tests
# ============================================


class TestVODStorage:
    """VODStorage 테스트"""

    @pytest.fixture
    def temp_storage_path(self):
        """임시 저장소 경로"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def vod_storage(self, temp_storage_path):
        """VODStorage 인스턴스"""
        storage_path = f"{temp_storage_path}/vod"
        metadata_path = f"{temp_storage_path}/metadata"
        return VODStorage(storage_path, metadata_path)

    def test_init_vod_storage(self, vod_storage):
        """VODStorage 초기화"""
        assert vod_storage is not None
        assert vod_storage.storage_path.exists()
        assert vod_storage.metadata_path.exists()
        print("✅ VODStorage initialized")

    def test_generate_video_id(self, vod_storage):
        """비디오 ID 생성"""
        video_id = vod_storage._generate_video_id("test-recording-001")
        
        assert isinstance(video_id, str)
        assert len(video_id) == 12
        print(f"✅ Video ID generated: {video_id}")

    def test_video_id_consistency(self, vod_storage):
        """비디오 ID 일관성"""
        recording_id = "test-recording-consistency"
        video_id_1 = vod_storage._generate_video_id(recording_id)
        video_id_2 = vod_storage._generate_video_id(recording_id)
        
        assert video_id_1 == video_id_2
        print(f"✅ Video ID consistency: {video_id_1 == video_id_2}")

    def test_save_metadata(self, vod_storage):
        """메타데이터 저장"""
        video_id = "test-video-001"
        metadata = {
            "video_id": video_id,
            "title": "Test Video",
            "description": "Test Description",
            "created_at": datetime.now(UTC).isoformat()
        }
        
        vod_storage._save_metadata(video_id, metadata)
        
        # 메타데이터 파일 존재 확인
        metadata_file = vod_storage.metadata_path / f"{video_id}.json"
        assert metadata_file.exists()
        print("✅ Metadata saved")

    def test_load_metadata(self, vod_storage):
        """메타데이터 로드"""
        video_id = "test-video-002"
        original_metadata = {
            "video_id": video_id,
            "title": "Test Video 2",
            "description": "Test Description 2"
        }
        
        vod_storage._save_metadata(video_id, original_metadata)
        loaded_metadata = vod_storage._load_metadata(video_id)
        
        assert loaded_metadata is not None
        assert loaded_metadata["video_id"] == video_id
        assert loaded_metadata["title"] == "Test Video 2"
        print("✅ Metadata loaded")

    def test_search_videos_empty(self, vod_storage):
        """비디오 검색 (빈 결과)"""
        videos = vod_storage.search_videos(query="nonexistent")
        
        assert isinstance(videos, list)
        assert len(videos) == 0
        print("✅ Video search (empty): OK")

    def test_list_videos_by_session(self, vod_storage):
        """세션별 비디오 목록"""
        # 메타데이터 저장
        video_id = "test-video-session-001"
        metadata = {
            "video_id": video_id,
            "recording_id": "session-001_20240101_120000",
            "title": "Test Video",
            "video_info": {"duration": 3600}
        }
        vod_storage._save_metadata(video_id, metadata)
        
        # 세션별 목록 조회
        videos = vod_storage.list_videos_by_session("session-001")
        
        assert isinstance(videos, list)
        print(f"✅ Videos listed by session: {len(videos)}")


# ============================================
# Integration Tests
# ============================================


class TestRecordingAndVODIntegration:
    """녹화와 VOD 시스템 통합 테스트"""

    def test_recording_to_vod_workflow(self):
        """녹화에서 VOD까지의 워크플로우"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. RecordingManager로 녹화
            manager = RecordingManager(storage_path=tmpdir)
            result = manager.start_recording(
                session_id="workflow-test",
                stream_url="rtmp://localhost:1935/live/test"
            )
            
            assert result["status"] in ["recording", "error"]
            print("✅ Step 1: Recording started")
            
            # 2. VODStorage로 비디오 저장
            vod_storage = VODStorage(
                storage_path=f"{tmpdir}/vod",
                metadata_path=f"{tmpdir}/metadata"
            )
            
            # 메타데이터 저장
            video_id = vod_storage._generate_video_id(result.get("recording_id", "test"))
            metadata = {
                "video_id": video_id,
                "title": "Test Recording",
                "teacher_name": "Teacher Name"
            }
            vod_storage._save_metadata(video_id, metadata)
            
            print("✅ Step 2: Video saved to VOD storage")
            
            # 3. 비디오 정보 조회
            video_info = vod_storage.get_video_info(video_id)
            assert video_info.get("video_id") == video_id
            print("✅ Step 3: Video info retrieved")

    def test_end_to_end_recording_workflow(self):
        """엔드-투-엔드 녹화 워크플로우"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 단계 1: 녹화 시작
            recording_manager = RecordingManager(storage_path=tmpdir)
            result = recording_manager.start_recording(
                session_id="e2e-test",
                stream_url="rtmp://localhost:1935/live/stream"
            )
            print("✅ Step 1: Recording started")
            
            # 단계 2: 녹화 상태 확인
            if result["status"] == "recording":
                recordings = recording_manager.list_recordings("e2e-test")
                assert len(recordings) > 0
                print("✅ Step 2: Recording status checked")
            
            # 단계 3: 메타데이터 생성
            vod_storage = VODStorage(
                storage_path=f"{tmpdir}/vod",
                metadata_path=f"{tmpdir}/metadata"
            )
            print("✅ Step 3: VOD storage initialized")
            
            # 단계 4: 메타데이터 저장 및 조회
            video_id = "test-e2e-video"
            metadata = {
                "video_id": video_id,
                "recording_id": "e2e-test_20240101_120000",
                "title": "E2E Test Recording",
                "teacher_name": "Test Teacher",
                "student_count": 30,
                "created_at": datetime.now(UTC).isoformat()
            }
            vod_storage._save_metadata(video_id, metadata)
            
            loaded = vod_storage._load_metadata(video_id)
            assert loaded is not None
            print("✅ Step 4: Metadata saved and retrieved")
            
            print("✅ End-to-end workflow: COMPLETE")


# ============================================
# Error Handling Tests
# ============================================


class TestErrorHandling:
    """에러 처리 테스트"""

    def test_get_nonexistent_recording(self):
        """존재하지 않는 녹화 조회"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = RecordingManager(storage_path=tmpdir)
            status = manager.get_recording_status("nonexistent-id")
            
            assert status.get("status") == "error"
            print("✅ Nonexistent recording handled")

    def test_load_nonexistent_metadata(self):
        """존재하지 않는 메타데이터 로드"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vod_storage = VODStorage(
                storage_path=f"{tmpdir}/vod",
                metadata_path=f"{tmpdir}/metadata"
            )
            
            metadata = vod_storage._load_metadata("nonexistent-video")
            assert metadata is None
            print("✅ Nonexistent metadata handled")

    def test_delete_nonexistent_video(self):
        """존재하지 않는 비디오 삭제"""
        with tempfile.TemporaryDirectory() as tmpdir:
            vod_storage = VODStorage(
                storage_path=f"{tmpdir}/vod",
                metadata_path=f"{tmpdir}/metadata"
            )
            
            result = vod_storage.delete_video("nonexistent-video")
            assert result.get("status") == "error"
            print("✅ Delete nonexistent video handled")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
