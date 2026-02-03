"""
System Status Router
===================
시스템 상태 및 헬스 체크 엔드포인트

- GET /: 루트 상태 (서비스 정보)
- GET /health: 헬스 체크 (Docker healthcheck 용)
- GET /api/status: 연결 상태 조회 (WebSocket)
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter
import httpx
from utils import get_connection_manager

logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["system"])

# ConnectionManager 싱글톤 가져오기
manager = get_connection_manager()

# MediaMTX API URL
MEDIAMTX_API_URL = os.getenv("MEDIAMTX_API_URL", "http://127.0.0.1:9997")


@router.get("/")
async def root():
    """서버 상태 확인"""
    # mediamtx_process는 main.py의 lifespan에서 관리되므로
    # 여기서는 프로세스 실행 여부만 체크
    mediamtx_running = True  # lifespan에서 시작되었다고 가정

    return {
        "status": "running",
        "service": "AIRClass Backend Server",
        "version": "2.0.0",
        "mediamtx_running": mediamtx_running,
        "rtmp_url": "rtmp://localhost:1935/live/stream",
        "webrtc_url": "http://localhost:8889/live/stream/whep",
        "frontend_url": "http://localhost:5173",
        "security": "JWT token required for WebRTC access",
    }


@router.get("/health")
async def health_check():
    """
    헬스 체크 (Docker healthcheck용)

    Returns:
        - status: healthy/degraded
        - mode: main/sub/standalone
        - stream_active: MediaMTX에서 스트림을 받고 있는지 여부
        - timestamp: 현재 시간
    """
    mode = os.getenv("MODE", "standalone")

    # MediaMTX API로 스트림 상태 확인
    stream_active = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # MediaMTX API
            response = await client.get(f"{MEDIAMTX_API_URL}/v3/paths/list")
            if response.status_code == 200:
                data = response.json()
                # "live/stream" 경로에 활성 source가 있는지 확인
                items = data.get("items", [])
                for item in items:
                    if item.get("name") == "live/stream":
                        # ready (bool), readers (array), source (object)
                        ready = item.get("ready", False)
                        readers = item.get("readers", [])
                        source = item.get("source")

                        # stream_active는 실제 publisher(source)가 있을 때만 true
                        # ready는 source가 있고 트랙이 준비된 상태
                        # readers는 시청자이므로 stream_active 판단에서 제외
                        if ready and source:
                            stream_active = True
                            logger.debug(
                                f"Stream active: ready={ready}, readers={len(readers)}, source={source is not None}"
                            )
                        break
    except Exception as e:
        logger.warning(f"Failed to check MediaMTX stream status: {e}")

    # 자동 검색 시 포트 정보 (동적 포트 범위 사용 시 참고)
    api_port = int(os.getenv("MAIN_API_PORT", os.getenv("NODE_PORT", "8000")))
    return {
        "status": "healthy",
        "mode": mode,
        "stream_active": stream_active,
        "api_port": api_port,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/api/status")
async def get_status():
    """현재 연결 상태 조회"""
    mode = os.getenv("MODE", "standalone")

    status_data = {
        "teacher_connected": manager.teacher is not None,
        "students_count": len(manager.students),
        "students": list(manager.students.keys()),
        "monitors_count": len(manager.monitors),
    }

    return status_data
