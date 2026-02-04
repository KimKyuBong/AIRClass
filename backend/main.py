"""
AIRClass Backend Server
FastAPI + MediaMTX를 사용한 실시간 WebRTC 스트리밍 백엔드
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set, Optional
from contextlib import asynccontextmanager
import json
import logging
import io
import os
import subprocess
from datetime import datetime, timedelta, UTC

# Utils
from utils import (
    # MediaMTX logic removed
    # start_mediamtx,
    # stop_mediamtx,
    # is_mediamtx_running,
    generate_stream_token,
    verify_token,
    get_local_ip,
    print_qr_code,
    JWT_EXPIRATION_MINUTES,
    get_connection_manager,
)

# Core modules
from core.cluster import cluster_manager, init_cluster_mode, shutdown_cluster, NodeInfo
from core.metrics import (
    http_requests_total,
    active_streams,
    active_websockets,
    active_connections,
    tokens_issued_total,
    cluster_nodes_total,
    cluster_load_percentage,
    cluster_connections,
    http_request_duration_seconds,
)
from config import CORS_ORIGINS, SERVER_IP

# Prometheus
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 라이프사이클 관리 (startup & shutdown)"""
    # Startup
    logger.info("🚀 Starting AIRClass Backend Server...")

    # 1. 클러스터 모드 초기화
    await init_cluster_mode()

    # 2. LiveKit 서버 시작
    try:
        from core.livekit_manager import init_livekit_manager
        from config import MODE, NODE_NAME, REDIS_URL, LIVEKIT_BINARY

        await init_livekit_manager(
            node_id=NODE_NAME,
            mode=MODE,
            redis_url=REDIS_URL,
            livekit_binary=LIVEKIT_BINARY,
        )
        logger.info("✅ LiveKit server initialized")
    except Exception as e:
        logger.error(f"❌ LiveKit server initialization failed: {e}")
        # LiveKit 실패 시 서버 시작 중단 (중요 서비스이므로)
        raise

    # 3. 백엔드 서비스들 초기화
    try:
        from core.cache import init_cache

        await init_cache()
        logger.info("✅ Cache initialized")
    except Exception as e:
        logger.warning(f"⚠️ Cache initialization failed: {e}")

    try:
        from core.database import init_database_manager

        await init_database_manager()
        logger.info("✅ DatabaseManager initialized")
    except Exception as e:
        logger.warning(f"⚠️ DatabaseManager initialization failed: {e}")

    try:
        from services.recording_service import init_recording_manager

        await init_recording_manager()
        logger.info("✅ RecordingManager initialized")
    except Exception as e:
        logger.warning(f"⚠️ RecordingManager initialization failed: {e}")

    try:
        from services.vod_service import init_vod_storage

        await init_vod_storage()
        logger.info("✅ VODStorage initialized")
    except Exception as e:
        logger.warning(f"⚠️ VODStorage initialization failed: {e}")

    try:
        from services.ai.vision import init_vision_analyzer

        await init_vision_analyzer()
        logger.info("✅ VisionAnalyzer initialized")
    except Exception as e:
        logger.warning(f"⚠️ VisionAnalyzer initialization failed: {e}")

    try:
        from services.ai.nlp import init_nlp_analyzer

        await init_nlp_analyzer()
        logger.info("✅ NLPAnalyzer initialized")
    except Exception as e:
        logger.warning(f"⚠️ NLPAnalyzer initialization failed: {e}")

    try:
        from services.ai.feedback import init_feedback_generator

        await init_feedback_generator()
        logger.info("✅ FeedbackGenerator initialized")
    except Exception as e:
        logger.warning(f"⚠️ FeedbackGenerator initialization failed: {e}")

    # Print QR code for Android app connection
    local_ip = get_local_ip()
    print_qr_code(local_ip)

    yield  # 서버 실행

    # Shutdown
    logger.info("🛑 Shutting down AIRClass Backend Server...")

    # 1. LiveKit 서버 종료
    try:
        from core.livekit_manager import shutdown_livekit_manager

        await shutdown_livekit_manager()
        logger.info("✅ LiveKit server stopped")
    except Exception as e:
        logger.error(f"❌ LiveKit server shutdown failed: {e}")

    # 2. 클러스터 종료
    await shutdown_cluster()


app = FastAPI(
    title="AIRClass Backend Server",
    description="Real-time WebRTC streaming with multi-node cluster support",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS 설정 - config에서 가져오기
# CORS_ORIGINS가 ["*"]인 경우 credentials를 False로 설정
# 그렇지 않으면 특정 origin에 대해 credentials를 True로 설정
if CORS_ORIGINS == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # "*"일 때는 False여야 함
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ============================================
# Include Routers
# ============================================
try:
    from routers.quiz import router as quiz_router

    app.include_router(quiz_router)
    logger.info("✅ Quiz router included")
except Exception as e:
    logger.warning(f"⚠️ Quiz router import failed: {e}")

try:
    from routers.engagement import router as engagement_router

    app.include_router(engagement_router)
    logger.info("✅ Engagement router included")
except Exception as e:
    logger.warning(f"⚠️ Engagement router import failed: {e}")

try:
    from routers.dashboard import router as dashboard_router

    app.include_router(dashboard_router)
    logger.info("✅ Dashboard router included")
except Exception as e:
    logger.warning(f"⚠️ Dashboard router import failed: {e}")

try:
    from routers.recording import router as recording_router

    app.include_router(recording_router)
    logger.info("✅ Recording router included")
except Exception as e:
    logger.warning(f"⚠️ Recording router import failed: {e}")

try:
    from routers.vod import router as vod_router

    app.include_router(vod_router)
    logger.info("✅ VOD router included")
except Exception as e:
    logger.warning(f"⚠️ VOD router import failed: {e}")

try:
    from routers.ai_analysis import router as ai_router

    app.include_router(ai_router)
    logger.info("✅ AI Analysis router included")
except Exception as e:
    logger.warning(f"⚠️ AI Analysis router import failed: {e}")

try:
    from routers.cluster import router as cluster_router

    app.include_router(cluster_router)
    logger.info("✅ Cluster router included")
except Exception as e:
    logger.warning(f"⚠️ Cluster router import failed: {e}")

try:
    from routers.auth import router as auth_router

    app.include_router(auth_router)
    logger.info("✅ Auth router included")
except Exception as e:
    logger.warning(f"⚠️ Auth router import failed: {e}")

try:
    from routers.websocket_routes import router as websocket_router

    app.include_router(websocket_router)
    logger.info("✅ WebSocket router included")
except Exception as e:
    logger.warning(f"⚠️ WebSocket router import failed: {e}")

try:
    from routers.system import router as system_router

    app.include_router(system_router)
    logger.info("✅ System router included")
except Exception as e:
    logger.warning(f"⚠️ System router import failed: {e}")

try:
    from routers.monitoring import router as monitoring_router

    app.include_router(monitoring_router)
    logger.info("✅ Monitoring router included")
except Exception as e:
    logger.warning(f"⚠️ Monitoring router import failed: {e}")

# MediaMTX routers removed
# try:
#     from routers.mediamtx_auth import router as mediamtx_auth_router
#     app.include_router(mediamtx_auth_router)
# except Exception as e:
#     logger.warning(f"⚠️ MediaMTX Auth router import failed: {e}")

# try:
#     from routers.mediamtx_proxy import router as mediamtx_proxy_router
#     app.include_router(mediamtx_proxy_router)
# except Exception as e:
#     logger.warning(f"⚠️ MediaMTX Proxy router import failed: {e}")

try:
    from routers.livekit import router as livekit_router

    app.include_router(livekit_router)
    logger.info("✅ LiveKit router included")
except Exception as e:
    logger.warning(f"⚠️ LiveKit router import failed: {e}")

# MediaMTX process variable removed
# mediamtx_process = None


# WebSocket connection manager (from utils)
manager = get_connection_manager()


# Note: /api/screen endpoint removed - Now switching to LiveKit
# MediaMTX logic was: Android app sends RTMP directly to MediaMTX


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🎓 AIRClass Backend Server v2.0.0 (LiveKit Mode)")
    print("=" * 60)
    # print("📡 RTMP: rtmp://localhost:1935/live/stream")
    # print("🎬 WebRTC: http://localhost:8889/live/stream/whep")
    print("🌐 API: http://localhost:8000")
    print("🖥️  Frontend: http://localhost:5173")
    print("=" * 60)
    print("👨‍🏫 Teacher: http://localhost:5173/#/teacher")
    print("👨‍🎓 Student: http://localhost:5173/#/student")
    print("📺 Monitor: http://localhost:5173/#/monitor")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
