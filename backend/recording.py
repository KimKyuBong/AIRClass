"""
AIRClass Recording Manager
Main 노드: RTMP 스트림을 MP4 + HLS로 자동 녹화
스크린샷: 10초마다 자동 캡처 및 저장
"""

import subprocess
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

logger = logging.getLogger(__name__)


class RecordingManager:
    """Main 노드의 녹화 관리자"""

    def __init__(self, recording_dir: str, screenshot_dir: str, enabled: bool = True):
        self.recording_dir = Path(recording_dir)
        self.screenshot_dir = Path(screenshot_dir)
        self.enabled = enabled
        self.recording_process = None
        self.current_session_id = None

        # 디렉토리 생성
        self.recording_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📹 RecordingManager initialized")
        logger.info(f"   Recording dir: {self.recording_dir}")
        logger.info(f"   Screenshot dir: {self.screenshot_dir}")

    def start_recording(self, session_id: str, stream_url: str = "rtmp://localhost/live/stream") -> bool:
        """
        Main 노드의 RTMP 스트림 녹화 시작
        
        Args:
            session_id: 수업 세션 ID (타임스탬프 기반)
            stream_url: 녹화할 RTMP 스트림 URL
        
        Returns:
            성공 여부
        """
        if not self.enabled:
            logger.warning("⚠️ Recording is disabled")
            return False

        if self.recording_process is not None:
            logger.warning("⚠️ Recording already in progress")
            return False

        try:
            self.current_session_id = session_id
            
            # 녹화 파일 경로
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"class_{session_id}_{timestamp}"
            
            # MP4 녹화 파일 (메인)
            mp4_path = self.recording_dir / f"{filename}.mp4"
            
            # HLS 세그먼트 (재생용)
            hls_dir = self.recording_dir / f"{filename}_hls"
            hls_dir.mkdir(parents=True, exist_ok=True)
            hls_path = hls_dir / "index.m3u8"
            
            # ffmpeg 명령어 구성
            # RTMP 입력 → MP4 + HLS 출력 (동시 처리)
            ffmpeg_cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", stream_url,
                "-c:v", "libx264",
                "-preset", "veryfast",  # 빠른 처리
                "-c:a", "aac",
                "-b:a", "128k",
                "-f", "mp4",
                str(mp4_path),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-c:a", "aac",
                "-b:a", "128k",
                "-f", "hls",
                "-hls_time", "10",
                "-hls_list_size", "0",
                str(hls_path),
            ]
            
            # ffmpeg 프로세스 시작
            self.recording_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )
            
            # 메타데이터 저장
            metadata = {
                "session_id": session_id,
                "start_time": datetime.now().isoformat(),
                "stream_url": stream_url,
                "mp4_file": str(mp4_path),
                "hls_dir": str(hls_dir),
                "status": "recording"
            }
            
            metadata_path = self.recording_dir / f"{filename}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Recording started: {filename}")
            logger.info(f"   MP4: {mp4_path}")
            logger.info(f"   HLS: {hls_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            return False

    def stop_recording(self) -> Optional[dict]:
        """
        녹화 중지 및 메타데이터 업데이트
        
        Returns:
            녹화 정보 딕셔너리 또는 None
        """
        if self.recording_process is None:
            logger.warning("⚠️ No recording in progress")
            return None

        try:
            # ffmpeg 프로세스 종료 (SIGINT)
            self.recording_process.terminate()
            self.recording_process.wait(timeout=30)
            
            logger.info(f"✅ Recording stopped: {self.current_session_id}")
            
            # 메타데이터 업데이트
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"class_{self.current_session_id}_{timestamp}"
            metadata_path = self.recording_dir / f"{filename}.json"
            
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                metadata["status"] = "completed"
                metadata["end_time"] = datetime.now().isoformat()
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                return metadata
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to stop recording: {e}")
            if self.recording_process:
                self.recording_process.kill()
            return None
        finally:
            self.recording_process = None
            self.current_session_id = None

    def capture_screenshot(self) -> Optional[str]:
        """
        현재 RTMP 스트림에서 스크린샷 캡처
        Main 노드의 MediaMTX에서 프레임 추출
        
        Returns:
            저장된 스크린샷 파일 경로 또는 None
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.screenshot_dir / f"screenshot_{timestamp}.jpg"
            
            # ffmpeg: RTMP 입력 → JPG 단일 프레임 추출 (빠름)
            ffmpeg_cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", "rtmp://localhost/live/stream",
                "-frames:v", "1",
                "-f", "image2",
                "-y",
                str(screenshot_path),
            ]
            
            # 5초 타임아웃으로 실행
            result = subprocess.run(
                ffmpeg_cmd,
                timeout=5,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if result.returncode == 0 and screenshot_path.exists():
                logger.debug(f"📸 Screenshot captured: {screenshot_path}")
                return str(screenshot_path)
            else:
                logger.warning(f"⚠️ Screenshot capture failed")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Screenshot capture timeout")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to capture screenshot: {e}")
            return None

    def get_recordings_list(self) -> list:
        """녹화된 모든 파일 목록 조회"""
        try:
            recordings = []
            
            for metadata_file in self.recording_dir.glob("*.json"):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    recordings.append(metadata)
            
            return sorted(recordings, key=lambda x: x["start_time"], reverse=True)
            
        except Exception as e:
            logger.error(f"❌ Failed to get recordings list: {e}")
            return []

    def cleanup_old_recordings(self, keep_days: int = 7) -> int:
        """
        오래된 녹화 파일 자동 삭제
        
        Args:
            keep_days: 유지할 기간 (일)
        
        Returns:
            삭제된 파일 개수
        """
        import time
        
        try:
            deleted_count = 0
            current_time = time.time()
            cutoff_time = current_time - (keep_days * 86400)
            
            for file in self.recording_dir.rglob("*"):
                if file.is_file() and file.stat().st_mtime < cutoff_time:
                    file.unlink()
                    deleted_count += 1
                    logger.info(f"🗑️ Deleted old file: {file}")
            
            logger.info(f"✅ Cleanup completed: {deleted_count} files deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup recordings: {e}")
            return 0


# 전역 인스턴스
recording_manager = None


def init_recording_manager():
    """RecordingManager 초기화 (Main 노드만)"""
    global recording_manager
    
    from config import MODE
    
    if MODE == "main":
        recording_enabled = os.getenv("RECORDING_ENABLED", "true").lower() == "true"
        recording_dir = os.getenv("RECORDING_DIR", "/recordings")
        screenshot_dir = os.getenv("SCREENSHOT_DIR", "/screenshots")
        
        recording_manager = RecordingManager(
            recording_dir=recording_dir,
            screenshot_dir=screenshot_dir,
            enabled=recording_enabled
        )
    else:
        logger.info("⚠️ RecordingManager not initialized (not Main node)")
        recording_manager = None


def get_recording_manager() -> Optional[RecordingManager]:
    """RecordingManager 인스턴스 반환"""
    return recording_manager
