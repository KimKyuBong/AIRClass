"""
AIRClass VOD API
비디오 재생 및 관리 API
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from vod_storage import get_vod_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vod", tags=["vod"])


# ============================================
# Dependencies
# ============================================


def get_storage():
    """VODStorage 의존성"""
    storage = get_vod_storage()
    if not storage:
        raise HTTPException(
            status_code=503, detail="VOD storage not initialized"
        )
    return storage


# ============================================
# VOD Info Endpoints
# ============================================


@router.get("/{video_id}/info")
async def get_video_info(
    video_id: str,
    storage=Depends(get_storage)
):
    """
    비디오 정보 조회
    
    Args:
        video_id: 비디오 ID
        
    Returns:
        {video_id, title, duration, codec, resolution, created_at}
    """
    try:
        video_info = storage.get_video_info(video_id)
        
        if video_info.get("status") == "error":
            raise HTTPException(status_code=404, detail="Video not found")
        
        return video_info
        
    except Exception as e:
        logger.error(f"❌ Error getting video info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def list_session_vods(
    session_id: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    storage=Depends(get_storage)
):
    """
    세션별 VOD 목록
    
    Args:
        session_id: 세션 ID
        limit: 결과 제한
        offset: 오프셋
        
    Returns:
        [{video_id, title, duration, created_at, thumbnail}]
    """
    try:
        videos = storage.list_videos_by_session(session_id, limit, offset)
        return videos
        
    except Exception as e:
        logger.error(f"❌ Error listing session VODs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# VOD Stream Endpoints
# ============================================


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    resolution: str = Query("720p", regex="^(360p|480p|720p|1080p)$"),
    start: int = Query(0, ge=0),
    end: Optional[int] = Query(None, ge=0),
    storage=Depends(get_storage)
):
    """
    비디오 스트림
    
    Args:
        video_id: 비디오 ID
        resolution: 해상도 (360p, 480p, 720p, 1080p)
        start: 시작 초 (선택사항)
        end: 종료 초 (선택사항)
        
    Returns:
        비디오 스트림
    """
    try:
        video_info = storage.get_video_info(video_id)
        
        if video_info.get("status") == "error":
            raise HTTPException(status_code=404, detail="Video not found")
        
        output_paths = video_info.get("available_resolutions", {})
        
        if resolution not in output_paths:
            # 가장 가까운 해상도 선택
            resolution = "720p"
        
        # 메타데이터에서 경로 가져오기 (실제 구현에서는 DB에서 조회)
        # 여기서는 예시만 제공
        
        return {
            "status": "streaming",
            "video_id": video_id,
            "resolution": resolution,
            "format": "mp4"
        }
        
    except Exception as e:
        logger.error(f"❌ Error streaming video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/thumbnail")
async def get_thumbnail(
    video_id: str,
    storage=Depends(get_storage)
):
    """
    비디오 썸네일
    
    Args:
        video_id: 비디오 ID
        
    Returns:
        썸네일 이미지
    """
    try:
        video_info = storage.get_video_info(video_id)
        
        if video_info.get("status") == "error":
            raise HTTPException(status_code=404, detail="Video not found")
        
        thumbnail_path = video_info.get("thumbnail")
        
        if not thumbnail_path or not Path(thumbnail_path).exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        return FileResponse(
            thumbnail_path,
            media_type="image/jpeg",
            filename=f"{video_id}_thumbnail.jpg"
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# VOD Search & Filter Endpoints
# ============================================


@router.get("/search")
async def search_videos(
    query: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    storage=Depends(get_storage)
):
    """
    비디오 검색
    
    Args:
        query: 검색어 (제목, 설명)
        teacher_name: 교사명
        date_from: 시작 날짜 (ISO 형식)
        date_to: 종료 날짜 (ISO 형식)
        limit: 결과 제한
        
    Returns:
        [{video_id, title, teacher_name, created_at, thumbnail}]
    """
    try:
        videos = storage.search_videos(
            query=query,
            teacher_name=teacher_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )
        return videos
        
    except Exception as e:
        logger.error(f"❌ Error searching videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# VOD Management Endpoints
# ============================================


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    storage=Depends(get_storage)
):
    """
    비디오 삭제
    
    Args:
        video_id: 비디오 ID
        
    Returns:
        {status, deleted_at}
    """
    try:
        result = storage.delete_video(video_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error deleting video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Chapters Management
# ============================================


@router.post("/{video_id}/chapters")
async def add_chapter(
    video_id: str,
    start_time: int,
    title: str,
    description: str = "",
    storage=Depends(get_storage)
):
    """
    챕터 추가
    
    Args:
        video_id: 비디오 ID
        start_time: 시작 시간 (초)
        title: 챕터 제목
        description: 설명
        
    Returns:
        {chapter_id, status}
    """
    try:
        # 실제 구현: DB에 저장
        chapter_id = f"{video_id}_{start_time}"
        
        return {
            "chapter_id": chapter_id,
            "status": "created",
            "start_time": start_time,
            "title": title,
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error adding chapter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}/chapters")
async def get_chapters(
    video_id: str,
    storage=Depends(get_storage)
):
    """
    챕터 목록
    
    Args:
        video_id: 비디오 ID
        
    Returns:
        [{chapter_id, start_time, title, description}]
    """
    try:
        # 실제 구현: DB에서 조회
        return {
            "video_id": video_id,
            "chapters": []
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting chapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Health Check
# ============================================


@router.get("/health", tags=["health"])
async def health_check():
    """
    VOD 시스템 헬스 체크
    
    Returns:
        {status: "healthy"}
    """
    try:
        storage = get_vod_storage()
        
        if not storage:
            return {"status": "unhealthy", "reason": "Storage not initialized"}
        
        return {"status": "healthy"}
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {"status": "unhealthy", "reason": str(e)}
