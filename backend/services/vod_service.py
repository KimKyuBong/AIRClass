"""
AIRClass VOD Storage Manager
비디오 저장소 및 메타데이터 관리
"""

import logging
import subprocess
import json
from datetime import datetime, UTC
from typing import Optional, Dict, List
from pathlib import Path
import hashlib

from models import SessionBase

logger = logging.getLogger(__name__)


class VODStorage:
    """VOD 저장소 관리"""

    def __init__(self, storage_path: str = "/storage/vod", metadata_path: str = "/storage/vod_metadata"):
        """
        초기화
        
        Args:
            storage_path: 비디오 저장 경로
            metadata_path: 메타데이터 저장 경로
        """
        self.storage_path = Path(storage_path)
        self.metadata_path = Path(metadata_path)
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
        
        self.resolutions = ["360p", "480p", "720p", "1080p"]
        
        logger.info(f"💾 VODStorage initialized: {storage_path}")

    def save_video(
        self,
        recording_id: str,
        input_file_path: str,
        title: str = None,
        description: str = None,
        teacher_name: str = None,
        student_count: int = 0,
        session_data: Dict = None
    ) -> Dict:
        """
        비디오 저장 및 처리
        
        Args:
            recording_id: 녹화 ID
            input_file_path: 입력 파일 경로
            title: 제목
            description: 설명
            teacher_name: 교사명
            student_count: 학생 수
            session_data: 세션 데이터
            
        Returns:
            {video_id, status, output_paths, thumbnail, metadata}
        """
        try:
            input_path = Path(input_file_path)
            
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_file_path}")
            
            # 비디오 ID (해시)
            video_id = self._generate_video_id(recording_id)
            
            # 비디오 정보 추출
            video_info = self._extract_video_info(input_file_path)
            
            if not video_info:
                raise ValueError("Failed to extract video information")
            
            # 다양한 해상도로 인코딩
            output_paths = {}
            for resolution in ["720p", "480p"]:  # 360p는 선택사항
                output_file = self.storage_path / f"{video_id}_{resolution}.mp4"
                
                if self._encode_video(input_file_path, str(output_file), resolution):
                    output_paths[resolution] = str(output_file)
                    logger.info(f"✅ Encoded {resolution}: {output_file}")
            
            # 썸네일 생성
            thumbnail_path = self._generate_thumbnail(input_file_path, video_id)
            
            # 메타데이터 저장
            metadata = {
                "video_id": video_id,
                "recording_id": recording_id,
                "title": title or f"Recording {recording_id}",
                "description": description or "",
                "teacher_name": teacher_name or "Unknown",
                "student_count": student_count,
                "created_at": datetime.now(UTC).isoformat(),
                "video_info": video_info,
                "output_paths": output_paths,
                "thumbnail": str(thumbnail_path),
                "session_data": session_data or {}
            }
            
            self._save_metadata(video_id, metadata)
            
            logger.info(f"✅ Video saved: {video_id}")
            
            return {
                "video_id": video_id,
                "status": "completed",
                "output_paths": output_paths,
                "thumbnail": str(thumbnail_path),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save video: {e}")
            return {
                "video_id": None,
                "status": "error",
                "error": str(e)
            }

    def get_video_info(self, video_id: str) -> Dict:
        """
        비디오 정보 조회
        
        Args:
            video_id: 비디오 ID
            
        Returns:
            {video_id, title, duration, codec, resolution, bitrate, created_at}
        """
        try:
            metadata = self._load_metadata(video_id)
            
            if not metadata:
                raise FileNotFoundError(f"Video metadata not found: {video_id}")
            
            video_info = metadata.get("video_info", {})
            
            return {
                "video_id": video_id,
                "title": metadata.get("title", ""),
                "description": metadata.get("description", ""),
                "teacher_name": metadata.get("teacher_name", ""),
                "student_count": metadata.get("student_count", 0),
                "duration_seconds": video_info.get("duration", 0),
                "width": video_info.get("width", 0),
                "height": video_info.get("height", 0),
                "codec": video_info.get("codec", ""),
                "bitrate_kbps": video_info.get("bitrate", 0),
                "fps": video_info.get("fps", 0),
                "created_at": metadata.get("created_at", ""),
                "available_resolutions": list(metadata.get("output_paths", {}).keys()),
                "thumbnail": metadata.get("thumbnail", "")
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get video info: {e}")
            return {
                "video_id": video_id,
                "status": "error",
                "error": str(e)
            }

    def list_videos_by_session(
        self,
        session_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict]:
        """
        세션별 비디오 목록
        
        Args:
            session_id: 세션 ID
            limit: 결과 제한
            offset: 오프셋
            
        Returns:
            [{video_id, title, duration, created_at}]
        """
        try:
            videos = []
            count = 0
            
            for metadata_file in sorted(self.metadata_path.glob("*.json")):
                if count >= limit + offset:
                    break
                
                metadata = self._load_metadata(metadata_file.stem)
                
                if metadata and metadata.get("recording_id", "").startswith(session_id):
                    if count >= offset:
                        video_info = metadata.get("video_info", {})
                        videos.append({
                            "video_id": metadata.get("video_id"),
                            "title": metadata.get("title"),
                            "duration_seconds": video_info.get("duration", 0),
                            "teacher_name": metadata.get("teacher_name"),
                            "created_at": metadata.get("created_at"),
                            "thumbnail": metadata.get("thumbnail")
                        })
                    count += 1
            
            return videos
            
        except Exception as e:
            logger.error(f"❌ Failed to list videos by session: {e}")
            return []

    def delete_video(self, video_id: str) -> Dict:
        """
        비디오 삭제
        
        Args:
            video_id: 비디오 ID
            
        Returns:
            {status, deleted_at}
        """
        try:
            metadata = self._load_metadata(video_id)
            
            if not metadata:
                raise FileNotFoundError(f"Video not found: {video_id}")
            
            # 비디오 파일 삭제
            for output_path in metadata.get("output_paths", {}).values():
                file_path = Path(output_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"🗑️ Deleted: {output_path}")
            
            # 썸네일 삭제
            thumbnail = metadata.get("thumbnail")
            if thumbnail:
                thumb_path = Path(thumbnail)
                if thumb_path.exists():
                    thumb_path.unlink()
            
            # 메타데이터 삭제
            metadata_file = self.metadata_path / f"{video_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            logger.info(f"✅ Video deleted: {video_id}")
            
            return {
                "video_id": video_id,
                "status": "deleted",
                "deleted_at": datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to delete video: {e}")
            return {
                "video_id": video_id,
                "status": "error",
                "error": str(e)
            }

    def search_videos(
        self,
        query: str = None,
        teacher_name: str = None,
        date_from: str = None,
        date_to: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        비디오 검색
        
        Args:
            query: 검색어 (제목, 설명)
            teacher_name: 교사명
            date_from: 시작 날짜 (ISO 형식)
            date_to: 종료 날짜 (ISO 형식)
            limit: 결과 제한
            
        Returns:
            [{video_id, title, teacher_name, created_at}]
        """
        try:
            results = []
            count = 0
            
            for metadata_file in sorted(self.metadata_path.glob("*.json"), reverse=True):
                if count >= limit:
                    break
                
                metadata = self._load_metadata(metadata_file.stem)
                
                if not metadata:
                    continue
                
                # 필터 적용
                if query:
                    title = metadata.get("title", "").lower()
                    description = metadata.get("description", "").lower()
                    query_lower = query.lower()
                    if query_lower not in title and query_lower not in description:
                        continue
                
                if teacher_name:
                    if metadata.get("teacher_name", "") != teacher_name:
                        continue
                
                if date_from:
                    created = metadata.get("created_at", "")
                    if created < date_from:
                        continue
                
                if date_to:
                    created = metadata.get("created_at", "")
                    if created > date_to:
                        continue
                
                video_info = metadata.get("video_info", {})
                results.append({
                    "video_id": metadata.get("video_id"),
                    "title": metadata.get("title"),
                    "teacher_name": metadata.get("teacher_name"),
                    "duration_seconds": video_info.get("duration", 0),
                    "created_at": metadata.get("created_at"),
                    "thumbnail": metadata.get("thumbnail")
                })
                count += 1
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search videos: {e}")
            return []

    # ============================================
    # Private Methods
    # ============================================

    def _generate_video_id(self, recording_id: str) -> str:
        """비디오 ID 생성"""
        hash_obj = hashlib.sha256(recording_id.encode())
        return hash_obj.hexdigest()[:12]

    def _extract_video_info(self, file_path: str) -> Dict:
        """비디오 정보 추출"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,codec_name",
                "-show_entries", "format=duration,bit_rate",
                "-of", "json",
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
            
            format_info = data.get("format", {})
            stream_info = data.get("streams", [{}])[0]
            
            fps_str = stream_info.get("r_frame_rate", "30/1")
            fps = int(fps_str.split("/")[0]) if "/" in fps_str else 30
            
            return {
                "duration": int(float(format_info.get("duration", 0))),
                "bitrate": int(float(format_info.get("bit_rate", 0))),
                "width": stream_info.get("width", 0),
                "height": stream_info.get("height", 0),
                "codec": stream_info.get("codec_name", ""),
                "fps": fps
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract video info: {e}")
            return {}

    def _encode_video(self, input_path: str, output_path: str, resolution: str) -> bool:
        """비디오 인코딩"""
        try:
            # 해상도별 설정
            resolution_map = {
                "360p": "640:360",
                "480p": "854:480",
                "720p": "1280:720",
                "1080p": "1920:1080"
            }
            
            scale = resolution_map.get(resolution, "1280:720")
            
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-vf", f"scale={scale}:force_original_aspect_ratio=decrease",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"❌ Failed to encode video: {e}")
            return False

    def _generate_thumbnail(self, input_path: str, video_id: str) -> str:
        """썸네일 생성"""
        try:
            thumbnail_path = self.storage_path / f"{video_id}_thumb.jpg"
            
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-ss", "00:00:10",
                "-vf", "scale=320:180",
                "-frames:v", "1",
                "-y",
                str(thumbnail_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"✅ Thumbnail generated: {thumbnail_path}")
                return str(thumbnail_path)
            else:
                raise RuntimeError(f"Failed to generate thumbnail: {result.stderr}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate thumbnail: {e}")
            return ""

    def _save_metadata(self, video_id: str, metadata: Dict):
        """메타데이터 저장"""
        try:
            metadata_file = self.metadata_path / f"{video_id}.json"
            
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Metadata saved: {metadata_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save metadata: {e}")

    def _load_metadata(self, video_id: str) -> Optional[Dict]:
        """메타데이터 로드"""
        try:
            metadata_file = self.metadata_path / f"{video_id}.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
            
        except Exception as e:
            logger.error(f"❌ Failed to load metadata: {e}")
            return None


# 전역 인스턴스
_vod_storage = None


async def init_vod_storage() -> Optional[VODStorage]:
    """VODStorage 초기화"""
    global _vod_storage
    
    try:
        import os
        storage_path = os.getenv("VOD_STORAGE_PATH", "/storage/vod")
        metadata_path = os.getenv("VOD_METADATA_PATH", "/storage/vod_metadata")
        
        _vod_storage = VODStorage(storage_path, metadata_path)
        
        logger.info("✅ VODStorage initialized successfully")
        return _vod_storage
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize VODStorage: {e}")
        return None


def get_vod_storage() -> Optional[VODStorage]:
    """VODStorage 인스턴스 반환"""
    return _vod_storage
