"""
AIRClass Recording Manager
실시간 스트림 녹화 및 VOD 관리
"""

import logging
import subprocess
import os
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class RecordingManager:
    """실시간 스트림 녹화 관리"""

    def __init__(self, storage_path: str = "/storage/vod"):
        """
        초기화
        
        Args:
            storage_path: VOD 저장 경로
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.active_recordings: Dict[str, dict] = {}
        
        logger.info(f"💾 RecordingManager initialized: {storage_path}")

    def start_recording(
        self,
        session_id: str,
        stream_url: str,
        output_format: str = "mp4"
    ) -> Dict:
        """
        스트림 녹화 시작
        
        Args:
            session_id: 세션 ID
            stream_url: RTMP/WebRTC 스트림 URL
            output_format: 출력 형식 (mp4, mkv, avi)
            
        Returns:
            {recording_id, status, file_path, started_at}
        """
        try:
            recording_id = f"{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            file_path = self.storage_path / f"{recording_id}.{output_format}"
            
            # ffmpeg 명령어 구성
            cmd = [
                "ffmpeg",
                "-i", stream_url,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-rtbufsize", "100M",
                str(file_path)
            ]
            
            # ffmpeg 프로세스 시작
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 녹화 정보 저장
            self.active_recordings[recording_id] = {
                "session_id": session_id,
                "stream_url": stream_url,
                "file_path": str(file_path),
                "process": process,
                "started_at": datetime.utcnow(),
                "status": "recording",
                "output_format": output_format
            }
            
            logger.info(f"🎬 Recording started: {recording_id}")
            
            return {
                "recording_id": recording_id,
                "status": "recording",
                "file_path": str(file_path),
                "started_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            return {
                "recording_id": None,
                "status": "error",
                "error": str(e)
            }

    def stop_recording(self, recording_id: str) -> Dict:
        """
        스트림 녹화 중지
        
        Args:
            recording_id: 녹화 ID
            
        Returns:
            {status, file_path, duration_seconds}
        """
        try:
            if recording_id not in self.active_recordings:
                raise ValueError(f"Recording not found: {recording_id}")
            
            recording = self.active_recordings[recording_id]
            process = recording["process"]
            
            # ffmpeg 프로세스 종료
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            file_path = Path(recording["file_path"])
            
            # 파일 정보 조회
            duration = self._get_video_duration(str(file_path))
            file_size = file_path.stat().st_size if file_path.exists() else 0
            
            # 녹화 정보 업데이트
            recording["status"] = "completed"
            recording["ended_at"] = datetime.utcnow()
            recording["duration_seconds"] = duration
            recording["file_size_bytes"] = file_size
            
            logger.info(f"✅ Recording stopped: {recording_id}")
            
            return {
                "recording_id": recording_id,
                "status": "completed",
                "file_path": str(file_path),
                "duration_seconds": duration,
                "file_size_mb": round(file_size / 1024 / 1024, 2) if file_size > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stop recording: {e}")
            return {
                "recording_id": recording_id,
                "status": "error",
                "error": str(e)
            }

    def get_recording_status(self, recording_id: str) -> Dict:
        """
        녹화 상태 조회
        
        Args:
            recording_id: 녹화 ID
            
        Returns:
            {status, file_size_mb, duration_seconds}
        """
        try:
            if recording_id not in self.active_recordings:
                raise ValueError(f"Recording not found: {recording_id}")
            
            recording = self.active_recordings[recording_id]
            file_path = Path(recording["file_path"])
            
            status = recording["status"]
            file_size = file_path.stat().st_size if file_path.exists() else 0
            
            result = {
                "recording_id": recording_id,
                "status": status,
                "file_size_mb": round(file_size / 1024 / 1024, 2) if file_size > 0 else 0,
                "started_at": recording["started_at"].isoformat()
            }
            
            if status == "completed" and "duration_seconds" in recording:
                result["duration_seconds"] = recording["duration_seconds"]
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get recording status: {e}")
            return {
                "recording_id": recording_id,
                "status": "error",
                "error": str(e)
            }

    def list_recordings(self, session_id: str) -> List[Dict]:
        """
        세션별 녹화 목록
        
        Args:
            session_id: 세션 ID
            
        Returns:
            [{recording_id, status, created_at, duration_seconds}]
        """
        try:
            recordings = []
            
            for recording_id, recording in self.active_recordings.items():
                if recording["session_id"] == session_id:
                    item = {
                        "recording_id": recording_id,
                        "status": recording["status"],
                        "created_at": recording["started_at"].isoformat()
                    }
                    
                    if "duration_seconds" in recording:
                        item["duration_seconds"] = recording["duration_seconds"]
                    
                    if "file_size_bytes" in recording:
                        item["file_size_mb"] = round(recording["file_size_bytes"] / 1024 / 1024, 2)
                    
                    recordings.append(item)
            
            return recordings
            
        except Exception as e:
            logger.error(f"❌ Failed to list recordings: {e}")
            return []

    def delete_recording(self, recording_id: str) -> Dict:
        """
        녹화 파일 삭제
        
        Args:
            recording_id: 녹화 ID
            
        Returns:
            {status, deleted_at}
        """
        try:
            if recording_id not in self.active_recordings:
                raise ValueError(f"Recording not found: {recording_id}")
            
            recording = self.active_recordings[recording_id]
            file_path = Path(recording["file_path"])
            
            # 녹화 중인 경우 먼저 중지
            if recording["status"] == "recording":
                self.stop_recording(recording_id)
            
            # 파일 삭제
            if file_path.exists():
                file_path.unlink()
                logger.info(f"🗑️ Recording deleted: {recording_id}")
            
            # 메모리에서 제거
            del self.active_recordings[recording_id]
            
            return {
                "recording_id": recording_id,
                "status": "deleted",
                "deleted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to delete recording: {e}")
            return {
                "recording_id": recording_id,
                "status": "error",
                "error": str(e)
            }

    def _get_video_duration(self, file_path: str) -> int:
        """
        비디오 파일의 지속시간 조회 (초 단위)
        
        Args:
            file_path: 비디오 파일 경로
            
        Returns:
            지속시간 (초)
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            duration = int(float(result.stdout.strip()))
            return duration
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get video duration: {e}")
            return 0

    def get_all_recordings(self) -> List[Dict]:
        """
        모든 녹화 조회
        
        Returns:
            [{recording_id, session_id, status, created_at}]
        """
        recordings = []
        
        for recording_id, recording in self.active_recordings.items():
            item = {
                "recording_id": recording_id,
                "session_id": recording["session_id"],
                "status": recording["status"],
                "created_at": recording["started_at"].isoformat()
            }
            recordings.append(item)
        
        return recordings


# 전역 인스턴스
_recording_manager = None


async def init_recording_manager() -> Optional[RecordingManager]:
    """RecordingManager 초기화"""
    global _recording_manager
    
    try:
        import os
        storage_path = os.getenv("VOD_STORAGE_PATH", "/storage/vod")
        _recording_manager = RecordingManager(storage_path)
        
        logger.info("✅ RecordingManager initialized successfully")
        return _recording_manager
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize RecordingManager: {e}")
        return None


def get_recording_manager() -> Optional[RecordingManager]:
    """RecordingManager 인스턴스 반환"""
    return _recording_manager
