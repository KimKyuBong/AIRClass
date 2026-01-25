"""
AIRClass Recording API
실시간 스트림 녹화 관리 API
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List

from recording import get_recording_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recording", tags=["recording"])


# ============================================
# Dependencies
# ============================================


def get_manager():
    """RecordingManager 의존성"""
    manager = get_recording_manager()
    if not manager:
        raise HTTPException(
            status_code=503, detail="Recording manager not initialized"
        )
    return manager


# ============================================
# Recording Control Endpoints
# ============================================


@router.post("/start")
async def start_recording(
    session_id: str,
    stream_url: str,
    output_format: str = "mp4",
    manager=Depends(get_manager)
):
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
        result = manager.start_recording(
            session_id=session_id,
            stream_url=stream_url,
            output_format=output_format
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error starting recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_recording(
    recording_id: str,
    manager=Depends(get_manager)
):
    """
    스트림 녹화 중지
    
    Args:
        recording_id: 녹화 ID
        
    Returns:
        {status, file_path, duration_seconds, file_size_mb}
    """
    try:
        result = manager.stop_recording(recording_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error stopping recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Recording Status Endpoints
# ============================================


@router.get("/{recording_id}/status")
async def get_recording_status(
    recording_id: str,
    manager=Depends(get_manager)
):
    """
    녹화 상태 조회
    
    Args:
        recording_id: 녹화 ID
        
    Returns:
        {recording_id, status, file_size_mb, started_at, duration_seconds}
    """
    try:
        result = manager.get_recording_status(recording_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail="Recording not found")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error getting recording status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def list_session_recordings(
    session_id: str,
    manager=Depends(get_manager)
):
    """
    세션별 녹화 목록
    
    Args:
        session_id: 세션 ID
        
    Returns:
        [{recording_id, status, created_at, duration_seconds, file_size_mb}]
    """
    try:
        recordings = manager.list_recordings(session_id)
        return recordings
        
    except Exception as e:
        logger.error(f"❌ Error listing recordings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_all_recordings(
    manager=Depends(get_manager)
):
    """
    모든 녹화 조회
    
    Returns:
        [{recording_id, session_id, status, created_at}]
    """
    try:
        recordings = manager.get_all_recordings()
        return recordings
        
    except Exception as e:
        logger.error(f"❌ Error listing all recordings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Recording Management Endpoints
# ============================================


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: str,
    manager=Depends(get_manager)
):
    """
    녹화 파일 삭제
    
    Args:
        recording_id: 녹화 ID
        
    Returns:
        {status, deleted_at}
    """
    try:
        result = manager.delete_recording(recording_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error deleting recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Health Check
# ============================================


@router.get("/health", tags=["health"])
async def health_check():
    """
    녹화 시스템 헬스 체크
    
    Returns:
        {status: "healthy"}
    """
    try:
        manager = get_recording_manager()
        
        if not manager:
            return {"status": "unhealthy", "reason": "Manager not initialized"}
        
        return {"status": "healthy"}
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {"status": "unhealthy", "reason": str(e)}
