"""
System Status Router
===================
시스템 상태 및 헬스 체크 엔드포인트

- GET /: 루트 상태 (서비스 정보)
- GET /health: 헬스 체크 (Docker healthcheck 용)
- GET /api/status: 연결 상태 조회 (WebSocket)
- GET /api/stream-status: LiveKit 스트림 상태 조회
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter
import httpx
from utils import get_connection_manager


# LiveKit API는 필요시 동적 import (순환 의존 방지)
def get_livekit_api():
    from routers.livekit import lkapi
    from livekit import api

    return lkapi, api


logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["system"])

# ConnectionManager 싱글톤 가져오기
manager = get_connection_manager()


@router.get("/")
async def root():
    """서버 상태 확인"""
    return {
        "status": "running",
        "service": "AIRClass Backend Server",
        "version": "2.0.0",
        "frontend_url": "http://localhost:5173",
        "security": "JWT token required for LiveKit access",
    }


@router.get("/health")
async def health_check():
    """
    헬스 체크 (Docker healthcheck용)

    Returns:
        - status: healthy/degraded
        - mode: main/sub/standalone
        - stream_active: LiveKit에 활성 룸이 있는지 여부
        - timestamp: 현재 시간
    """
    mode = os.getenv("MODE", "main")

    # LiveKit API로 룸 상태 확인
    stream_active = False
    try:
        lkapi, api = get_livekit_api()
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest())
        if rooms.rooms:
            stream_active = True
    except Exception as e:
        logger.warning(f"Failed to check LiveKit status: {e}")

    # 자동 검색 시 포트 정보 (동적 포트 범위 사용 시 참고)
    api_port = int(os.getenv("MAIN_API_PORT", os.getenv("NODE_PORT", "8000")))
    return {
        "status": "healthy",
        "mode": mode,
        "stream_active": stream_active,
        "api_port": api_port,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/api/stream-status")
async def get_stream_status():
    """LiveKit 룸 목록 조회"""
    try:
        lkapi, api = get_livekit_api()
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest())
        return {
            "rooms": [
                {
                    "name": room.name,
                    "num_participants": room.num_participants,
                    "creation_time": room.creation_time,
                }
                for room in rooms.rooms
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list LiveKit rooms: {e}")
        return {"rooms": [], "error": str(e)}


@router.get("/api/status")
async def get_status():
    """현재 연결 상태 조회"""
    mode = os.getenv("MODE", "main")

    status_data = {
        "teacher_connected": manager.teacher is not None,
        "students_count": len(manager.students),
        "students": list(manager.students.keys()),
        "monitors_count": len(manager.monitors),
    }

    return status_data
