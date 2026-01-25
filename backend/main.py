"""
AIRClass Backend Server
FastAPI + MediaMTX를 사용한 실시간 WebRTC 스트리밍 백엔드
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set, Optional
import subprocess
import atexit
import json
import jwt
import secrets
import os
import logging
import socket
import qrcode
import io
from datetime import datetime, timedelta
from cluster import cluster_manager, init_cluster_mode, shutdown_cluster, NodeInfo
from config import CORS_ORIGINS, SERVER_IP
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AIRClass Backend Server",
    description="Real-time WebRTC streaming with multi-node cluster support",
    version="2.0.0",
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
# Prometheus Metrics
# ============================================
# Request metrics
http_requests_total = Counter(
    "airclass_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "airclass_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

# Streaming metrics
active_streams = Gauge("airclass_active_streams", "Number of active streams")

active_connections = Gauge(
    "airclass_active_connections",
    "Number of active WebSocket connections",
    ["type"],  # teacher, student, monitor
)

tokens_issued_total = Counter(
    "airclass_tokens_issued_total",
    "Total JWT tokens issued",
    ["user_type"],  # teacher, student, monitor
)

# Cluster metrics
cluster_nodes_total = Gauge(
    "airclass_cluster_nodes_total",
    "Total number of nodes in cluster",
    ["status"],  # active, offline, unhealthy
)

cluster_load_percentage = Gauge(
    "airclass_cluster_load_percentage", "Load percentage per node", ["node_id"]
)

cluster_connections = Gauge(
    "airclass_cluster_connections", "Current connections per node", ["node_id"]
)

# Error metrics
errors_total = Counter(
    "airclass_errors_total",
    "Total errors",
    ["type"],  # auth, stream, cluster, websocket
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

mediamtx_process = None


# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.teacher: WebSocket | None = None
        self.students: Dict[str, WebSocket] = {}
        self.monitors: Set[WebSocket] = set()

    async def connect_teacher(self, websocket: WebSocket):
        """교사 연결"""
        await websocket.accept()
        if self.teacher:
            # 기존 교사가 있으면 연결 해제
            try:
                await self.teacher.close()
            except:
                pass
        self.teacher = websocket
        print(f"👨‍🏫 Teacher connected")

    async def connect_student(self, websocket: WebSocket, name: str):
        """학생 연결"""
        await websocket.accept()
        self.students[name] = websocket
        print(f"👨‍🎓 Student '{name}' connected ({len(self.students)} total)")

        # 교사에게 학생 목록 업데이트 전송
        if self.teacher:
            await self.send_to_teacher(
                {"type": "student_list", "students": list(self.students.keys())}
            )

    async def connect_monitor(self, websocket: WebSocket):
        """모니터 연결"""
        await websocket.accept()
        self.monitors.add(websocket)
        print(f"📺 Monitor connected ({len(self.monitors)} total)")

    def disconnect_teacher(self):
        """교사 연결 해제"""
        self.teacher = None
        print("👨‍🏫 Teacher disconnected")

    def disconnect_student(self, name: str):
        """학생 연결 해제"""
        if name in self.students:
            del self.students[name]
            print(
                f"👨‍🎓 Student '{name}' disconnected ({len(self.students)} remaining)"
            )

    def disconnect_monitor(self, websocket: WebSocket):
        """모니터 연결 해제"""
        self.monitors.discard(websocket)
        print(f"📺 Monitor disconnected ({len(self.monitors)} remaining)")

    async def send_to_teacher(self, message: dict):
        """교사에게 메시지 전송"""
        if self.teacher:
            try:
                await self.teacher.send_json(message)
            except:
                self.disconnect_teacher()

    async def send_to_student(self, name: str, message: dict):
        """특정 학생에게 메시지 전송"""
        if name in self.students:
            try:
                await self.students[name].send_json(message)
            except:
                self.disconnect_student(name)

    async def send_to_all_students(self, message: dict):
        """모든 학생에게 메시지 전송"""
        disconnected = []
        for name, ws in self.students.items():
            try:
                await ws.send_json(message)
            except:
                disconnected.append(name)

        for name in disconnected:
            self.disconnect_student(name)

    async def send_to_all_monitors(self, message: dict):
        """모든 모니터에게 메시지 전송"""
        disconnected = []
        for ws in self.monitors:
            try:
                await ws.send_json(message)
            except:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect_monitor(ws)


manager = ConnectionManager()


def start_mediamtx():
    """MediaMTX RTMP/WebRTC 서버 시작"""
    global mediamtx_process

    if mediamtx_process is None:
        print("🚀 Starting MediaMTX server...")
        mediamtx_process = subprocess.Popen(
            ["./mediamtx"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(f"✅ MediaMTX started (PID: {mediamtx_process.pid})")
        print("📡 RTMP: rtmp://localhost:1935/live/stream")
        print("🎬 WebRTC: http://localhost:8889/live/stream/whep")


def stop_mediamtx():
    """MediaMTX 서버 중지"""
    global mediamtx_process

    if mediamtx_process:
        print("🛑 Stopping MediaMTX...")
        mediamtx_process.terminate()
        mediamtx_process.wait()


mediamtx_process = None

# JWT Secret Key (환경 변수에서 읽기, 없으면 생성하여 환경에 저장)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60  # 토큰 유효 시간

# Active tokens (간단한 토큰 관리)
active_tokens: Set[str] = set()


def get_local_ip() -> str:
    """Get local IP address in the network"""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to Google DNS (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "localhost"


def print_qr_code(data: str):
    """Print QR code to terminal using ASCII art"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Print to terminal
    print("\n" + "=" * 60)
    print("📱 QR Code for Android App Connection:")
    print("=" * 60)
    qr.print_ascii(invert=True)
    print("=" * 60)
    print(f"Server IP: {data}")
    print("=" * 60 + "\n")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 MediaMTX 실행 및 클러스터 초기화"""
    start_mediamtx()
    await init_cluster_mode()

    # Initialize recording and VOD systems
    try:
        from recording import init_recording_manager

        await init_recording_manager()
        logger.info("✅ RecordingManager initialized")
    except Exception as e:
        logger.warning(f"⚠️ RecordingManager initialization failed: {e}")

    try:
        from vod_storage import init_vod_storage

        await init_vod_storage()
        logger.info("✅ VODStorage initialized")
    except Exception as e:
        logger.warning(f"⚠️ VODStorage initialization failed: {e}")

    # Print QR code for Android app connection
    local_ip = get_local_ip()
    print_qr_code(local_ip)


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 MediaMTX 중지 및 클러스터 종료"""
    await shutdown_cluster()
    stop_mediamtx()


# 프로세스 종료 시 cleanup
atexit.register(stop_mediamtx)


def generate_stream_token(user_type: str, user_id: str, action: str = "read") -> str:
    """
    스트림 접근 토큰 생성

    Args:
        user_type: 'teacher', 'student', 'monitor'
        user_id: 사용자 ID (학생 이름 등)
        action: 'read' (default) or 'publish'

    Returns:
        JWT 토큰 문자열
    """
    expiration = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "user_type": user_type,
        "user_id": user_id,
        "exp": expiration,
        "iat": datetime.utcnow(),
        "action": action,  # MediaMTX action
        "path": "live/stream",  # MediaMTX path
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    active_tokens.add(token)
    return token


def verify_token(token: str) -> Optional[dict]:
    """토큰 검증"""
    try:
        # JWT 검증만 수행 (active_tokens는 Main에서만 관리하므로 Sub에서는 체크하지 않음)
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print(f"[verify_token] ✅ Token valid. Payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError as e:
        print(f"[verify_token] ❌ Token expired: {e}")
        # Main에서만 active_tokens 정리
        if token in active_tokens:
            active_tokens.discard(token)
        return None
    except jwt.InvalidTokenError as e:
        print(f"[verify_token] ❌ Invalid token: {e}")
        return None


@app.get("/")
async def root():
    """서버 상태 확인"""
    return {
        "status": "running",
        "service": "AIRClass Backend Server",
        "version": "2.0.0",
        "mediamtx_running": mediamtx_process is not None,
        "rtmp_url": "rtmp://localhost:1935/live/stream",
        "webrtc_url": "http://localhost:8889/live/stream/whep",
        "frontend_url": "http://localhost:5173",
        "security": "JWT token required for WebRTC access",
    }


@app.post("/api/auth/mediamtx")
async def mediamtx_auth(request: dict):
    """
    MediaMTX HTTP 인증 엔드포인트

    MediaMTX가 클라이언트 인증 시 호출
    """
    action = request.get("action")
    path = request.get("path")
    query = request.get("query", "")
    protocol = request.get("protocol")
    ip = request.get("ip", "")

    # 디버깅용 로그
    print(
        f"[MediaMTX Auth] action={action}, protocol={protocol}, path={path}, query={query}, ip={ip}"
    )
    print(f"[MediaMTX Auth] Full request: {request}")

    # Android 앱의 RTMP publish는 항상 허용
    if action == "publish" and protocol == "rtmp":
        print(f"[MediaMTX Auth] ✅ Allowing RTMP publish")
        return {"status": "ok"}

    # WebRTC publish (Teacher Screen Share) - WHIP
    if action == "publish" and protocol == "webrtc":
        # query에서 jwt 파라미터 추출
        token = None
        if "jwt=" in query:
            # 첫 번째 jwt= 값만 추출 (중복 방지)
            token = query.split("jwt=")[1].split("&")[0]
            print(f"[MediaMTX Auth] Extracted JWT token for publish: {token[:50]}...")

        if not token:
            print(f"[MediaMTX Auth] ❌ WebRTC publish denied - no token")
            raise HTTPException(status_code=401, detail="Token required")

        # 토큰 검증
        payload = verify_token(token)
        if not payload:
            print(f"[MediaMTX Auth] ❌ WebRTC publish denied - invalid token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Teacher 권한 확인
        if payload.get("user_type") != "teacher":
            print(f"[MediaMTX Auth] ❌ WebRTC publish denied - not a teacher")
            raise HTTPException(status_code=403, detail="Only teachers can publish")

        print(
            f"[MediaMTX Auth] ✅ Allowing WebRTC publish for teacher {payload.get('user_id')}"
        )
        return {"status": "ok"}

    # Main 모드: 내부 프록시 스크립트의 RTMP read 허용 (localhost에서만)
    if action == "read" and protocol == "rtmp":
        ip = request.get("ip", "")
        if ip in ["127.0.0.1", "::1", "localhost"]:
            print(f"[MediaMTX Auth] ✅ Allowing internal RTMP read from {ip}")
            return {"status": "ok"}
        else:
            print(f"[MediaMTX Auth] ❌ RTMP read denied - not from localhost (ip={ip})")
            raise HTTPException(status_code=403, detail="RTMP read not allowed")

    # Main 모드: 내부 FFmpeg의 RTSP read 허용 (모든 localhost 연결)
    # FFmpeg 프록시는 항상 localhost에서만 실행되므로 RTSP read는 모두 허용
    if action == "read" and protocol == "rtsp":
        print(f"[MediaMTX Auth] ✅ Allowing internal RTSP read (FFmpeg proxy)")
        return {"status": "ok"}

    # WebRTC read는 JWT 토큰 필요
    if action == "read" and protocol == "webrtc":
        # query에서 jwt 파라미터 추출
        token = None
        if "jwt=" in query:
            # 첫 번째 jwt= 값만 추출 (중복 방지)
            token = query.split("jwt=")[1].split("&")[0]
            print(f"[MediaMTX Auth] Extracted JWT token: {token[:50]}...")

        if not token:
            print(f"[MediaMTX Auth] ❌ WebRTC read denied - no token")
            raise HTTPException(status_code=401, detail="Token required")

        # 토큰 검증
        payload = verify_token(token)
        if not payload:
            print(f"[MediaMTX Auth] ❌ WebRTC read denied - invalid token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # path 검증
        if payload.get("path") != path:
            print(
                f"[MediaMTX Auth] ❌ WebRTC read denied - path mismatch (expected: {payload.get('path')}, got: {path})"
            )
            raise HTTPException(status_code=403, detail="Path mismatch")

        print(f"[MediaMTX Auth] ✅ Allowing WebRTC read for {payload.get('user_id')}")
        return {"status": "ok"}

    # 그 외는 거부
    print(f"[MediaMTX Auth] ❌ Denied - action={action}, protocol={protocol}")
    raise HTTPException(status_code=403, detail="Access denied")


# WebSocket 엔드포인트
@app.websocket("/ws/teacher")
async def websocket_teacher(websocket: WebSocket):
    """교사용 WebSocket - 학생 관리 및 채팅"""
    await manager.connect_teacher(websocket)

    try:
        while True:
            data = await websocket.receive()

            if "text" in data:
                message = json.loads(data["text"])
                msg_type = message.get("type")

                if msg_type == "chat":
                    # 교사의 채팅 메시지를 모든 학생에게 전송
                    await manager.send_to_all_students(
                        {
                            "type": "chat",
                            "from": "teacher",
                            "message": message.get("message"),
                        }
                    )

                elif msg_type == "control":
                    # 제어 명령 (예: 특정 학생에게 메시지)
                    target = message.get("target")
                    command = message.get("command")
                    if target and command:
                        await manager.send_to_student(
                            target, {"type": "control", "command": command}
                        )

            # Note: Screen data is now handled by MediaMTX WebRTC streaming
            # Android app sends RTMP to MediaMTX, clients play WebRTC directly

    except WebSocketDisconnect:
        manager.disconnect_teacher()
    except Exception as e:
        print(f"Error in teacher websocket: {e}")
        manager.disconnect_teacher()


@app.websocket("/ws/student")
async def websocket_student(websocket: WebSocket, name: str):
    """학생용 WebSocket - 채팅"""
    await manager.connect_student(websocket, name)

    try:
        # Note: Students now receive video via WebRTC stream from MediaMTX

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "chat":
                # 학생의 질문을 교사에게 전송
                await manager.send_to_teacher(
                    {"type": "chat", "from": name, "message": message.get("message")}
                )

            elif msg_type == "ping":
                # 연결 유지를 위한 ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect_student(name)
        # 교사에게 학생 목록 업데이트 전송
        if manager.teacher:
            await manager.send_to_teacher(
                {"type": "student_list", "students": list(manager.students.keys())}
            )
    except Exception as e:
        print(f"Error in student websocket ({name}): {e}")
        manager.disconnect_student(name)


@app.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """모니터용 WebSocket - 연결 상태 유지"""
    await manager.connect_monitor(websocket)

    try:
        # Note: Monitors now receive video via WebRTC stream from MediaMTX

        while True:
            # 모니터는 데이터를 보내지 않고 수신만 함
            # 하지만 연결 유지를 위해 메시지 대기
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect_monitor(websocket)
    except Exception as e:
        print(f"Error in monitor websocket: {e}")
        manager.disconnect_monitor(websocket)


# ============================================================
# Cluster Management APIs (Main/Sub)
# ============================================================


@app.post("/cluster/register")
async def register_node(request: Request):
    """Sub 노드 등록 (HMAC 인증)"""
    mode = os.getenv("MODE", "standalone")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main can register nodes")

    data = await request.json()

    # HMAC 인증 검증
    cluster_secret = os.getenv("CLUSTER_SECRET", "")
    if not cluster_secret:
        logger.error("❌ CLUSTER_SECRET not set in Main node!")
        raise HTTPException(status_code=500, detail="Server configuration error")

    provided_token = data.get("auth_token")
    timestamp = data.get("timestamp")

    if not provided_token or not timestamp:
        logger.warning("⚠️ Registration attempt without auth_token or timestamp")
        raise HTTPException(status_code=403, detail="Authentication required")

    # HMAC 검증
    from cluster import verify_cluster_auth_token

    if not verify_cluster_auth_token(cluster_secret, timestamp, provided_token):
        logger.warning(
            f"⚠️ Authentication failed for node: {data.get('node_name', 'unknown')}"
        )
        logger.warning("   CLUSTER_SECRET이 일치하지 않습니다")
        raise HTTPException(
            status_code=403, detail="Authentication failed: CLUSTER_SECRET mismatch"
        )

    # 인증 성공 - auth_token과 timestamp는 NodeInfo에 없으므로 제거
    data.pop("auth_token", None)
    data.pop("timestamp", None)

    # last_heartbeat을 ISO string에서 datetime으로 변환
    if "last_heartbeat" in data and isinstance(data["last_heartbeat"], str):
        data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])

    node = NodeInfo(**data)
    cluster_manager.register_node(node)
    logger.info(f"✅ Node authenticated and registered: {node.node_name}")
    return {"status": "registered", "node_id": node.node_id}


@app.post("/cluster/unregister")
async def unregister_node(request: Request):
    """Sub 노드 등록 해제 (Main only)"""
    mode = os.getenv("MODE", "standalone")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main can unregister nodes")

    data = await request.json()
    node_id = data.get("node_id")
    success = cluster_manager.unregister_node(node_id)

    if success:
        return {"status": "unregistered", "node_id": node_id}
    else:
        raise HTTPException(status_code=404, detail="Node not found")


@app.post("/cluster/stats")
async def update_node_stats(request: Request):
    """노드 통계 업데이트 (Sub → Main, HMAC 인증)"""
    mode = os.getenv("MODE", "standalone")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main can receive stats")

    data = await request.json()

    # HMAC 인증 검증
    cluster_secret = os.getenv("CLUSTER_SECRET", "")
    if not cluster_secret:
        raise HTTPException(status_code=500, detail="Server configuration error")

    provided_token = data.get("auth_token")
    timestamp = data.get("timestamp")

    if not provided_token or not timestamp:
        raise HTTPException(status_code=403, detail="Authentication required")

    # HMAC 검증
    from cluster import verify_cluster_auth_token

    if not verify_cluster_auth_token(cluster_secret, timestamp, provided_token):
        logger.warning(
            f"⚠️ Stats authentication failed for node: {data.get('node_id', 'unknown')}"
        )
        raise HTTPException(status_code=403, detail="Authentication failed")

    # 인증 성공
    node_id = data.get("node_id")
    stats = data.get("stats", {})

    success = cluster_manager.update_node_stats(node_id, stats)

    if not success:
        raise HTTPException(status_code=404, detail="Node not found")

    return {"status": "updated"}


@app.get("/cluster/nodes")
async def get_cluster_nodes():
    """클러스터 노드 목록 조회"""
    mode = os.getenv("MODE", "standalone")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main has cluster info")

    return cluster_manager.get_cluster_stats()


# ============================================================
# Token API for Cluster Mode
# ============================================================


@app.post("/api/token")
async def create_token_cluster_aware(
    user_type: str, user_id: str, action: str = "read"
):
    """
    스트림 접근 토큰 발급 (클러스터 지원)

    Main 모드: 최적의 Sub 노드로 리다이렉트
    Sub/Standalone 모드: 직접 토큰 발급
    """
    mode = os.getenv("MODE", "standalone")

    # Production: Load balancing enabled by default
    # Set USE_MAIN_WEBRTC=true to bypass load balancing (development only)
    use_main_webrtc = os.getenv("USE_MAIN_WEBRTC", "false").lower() == "true"

    # Teacher는 항상 Main 노드에 연결 (RTMP 스트리밍 소스이므로)
    # Student만 Sub 노드로 로드 밸런싱
    # action이 'publish'인 경우(교사 화면 공유)도 Main으로 연결
    if (
        mode == "main"
        and not use_main_webrtc
        and user_type == "student"
        and action == "read"
    ):
        # Rendezvous Hashing을 사용하여 user_id 기반 일관성 있는 노드 선택
        node = cluster_manager.get_node_for_stream(user_id, use_sticky=True)
        if not node:
            raise HTTPException(status_code=503, detail="No healthy nodes available")

        # 메인 노드 자신이 선택되었다면 직접 토큰 발급 (리다이렉트 없음)
        if node.node_id == cluster_manager.main_node_id:
            logger.info(f"✅ Main node selected for {user_id}, serving directly")
            # 아래 "Sub/Standalone 모드" 로직으로 진행 (pass through)
        else:
            # Sub의 토큰 발급 엔드포인트로 리다이렉트
            redirect_url = f"{node.api_url}/api/token?user_type={user_type}&user_id={user_id}&action={action}"

            # 직접 Sub에 요청하여 토큰 받기
            import httpx
            import re

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(redirect_url)
                    if response.status_code == 200:
                        data = response.json()

                        # Docker 외부 접근을 위해 호스트에 매핑된 포트 찾기 (WebRTC)
                        try:
                            # Get Docker container port mappings
                            result = subprocess.run(
                                [
                                    "docker",
                                    "ps",
                                    "--filter",
                                    "name=airclass-sub",
                                    "--format",
                                    "{{.Names}}\t{{.Ports}}",
                                ],
                                capture_output=True,
                                text=True,
                                timeout=5,
                            )

                            if result.returncode == 0:
                                # Find the specific container for this node
                                for line in result.stdout.strip().split("\n"):
                                    if not line:
                                        continue

                                    parts = line.split("\t")
                                    if len(parts) < 2:
                                        continue

                                    container_name = parts[0]
                                    ports_str = parts[1]

                                    # Check if this container matches our node_id
                                    hostname_check = subprocess.run(
                                        ["docker", "exec", container_name, "hostname"],
                                        capture_output=True,
                                        text=True,
                                        timeout=2,
                                    )

                                    if hostname_check.returncode == 0:
                                        container_hostname = (
                                            hostname_check.stdout.strip()
                                        )
                                        expected_node_id = f"sub-{container_hostname}"

                                        if expected_node_id == node.node_id:
                                            # Extract external port for WebRTC (8889)
                                            webrtc_match = re.search(
                                                r"0\.0\.0\.0:(\d+)->8889/tcp", ports_str
                                            )

                                            if webrtc_match:
                                                external_webrtc_port = (
                                                    webrtc_match.group(1)
                                                )
                                                # Rewrite WebRTC URL to use server IP with external port
                                                token = data.get("token", "")
                                                # Use SERVER_IP from config (set via environment variable)
                                                data["webrtc_url"] = (
                                                    f"http://{SERVER_IP}:{external_webrtc_port}/live/stream/whep?jwt={token}"
                                                )
                                                logger.info(
                                                    f"Rewrote WebRTC URL to use server IP {SERVER_IP} and external port {external_webrtc_port}"
                                                )

                                            break
                        except Exception as e:
                            logger.error(f"Error finding external ports: {e}")

                        # Main 정보 추가
                        data["routed_by"] = "main"
                        data["node_id"] = node.node_id
                        data["node_name"] = node.node_name
                        return data
                    else:
                        raise HTTPException(
                            status_code=503, detail="Failed to get token from node"
                        )
                except Exception as e:
                    raise HTTPException(
                        status_code=503, detail=f"Node communication error: {str(e)}"
                    )

    # Sub/Standalone 모드: 기존 로직 (직접 토큰 발급)
    if user_type not in ["teacher", "student", "monitor"]:
        raise HTTPException(status_code=400, detail="Invalid user_type")

    # Publish 권한 체크: 교사만 가능
    if action == "publish" and user_type != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can publish streams")

    if not user_id or len(user_id) < 1:
        raise HTTPException(status_code=400, detail="user_id required")

    token = generate_stream_token(user_type, user_id, action)

    # Track token issuance
    tokens_issued_total.labels(user_type=user_type).inc()

    # WebRTC URL 생성 (Sub는 자신의 주소 반환)
    node_host = os.getenv("NODE_HOST", "localhost")
    webrtc_port = os.getenv("WEBRTC_PORT", "8889")

    # Main 모드에서는 서버 IP 사용 (내부 네트워크 접근 가능)
    if mode == "main":
        node_host = SERVER_IP

    if action == "publish":
        # Publishing uses WHIP
        webrtc_url = f"http://{node_host}:{webrtc_port}/live/stream/whip?jwt={token}"
    else:
        # Reading uses WHEP
        webrtc_url = f"http://{node_host}:{webrtc_port}/live/stream/whep?jwt={token}"

    # 응답 데이터 생성
    response_data = {
        "token": token,
        "webrtc_url": webrtc_url,
        "expires_in": JWT_EXPIRATION_MINUTES * 60,
        "user_type": user_type,
        "user_id": user_id,
        "mode": mode,
        "action": action,
    }

    # Main 모드에서 직접 서빙하는 경우 node_name 추가
    if mode == "main":
        response_data["node_name"] = os.getenv("NODE_NAME", "main")
        response_data["node_id"] = os.getenv("NODE_ID", "main")

    return response_data


# ============================================================
# Health Check API
# ============================================================


@app.get("/health")
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
        import httpx

        async with httpx.AsyncClient(timeout=2.0) as client:
            # MediaMTX API: GET /v3/paths/list
            response = await client.get("http://127.0.0.1:9997/v3/paths/list")
            if response.status_code == 200:
                data = response.json()
                # "live/stream" 경로에 활성 source가 있는지 확인
                items = data.get("items", [])
                for item in items:
                    if item.get("name") == "live/stream":
                        # v3 API: ready (bool), readers (array), source (object)
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

    return {
        "status": "healthy",
        "mode": mode,
        "stream_active": stream_active,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint

    Exposes metrics for monitoring:
    - HTTP request counts and latency
    - Active streams and connections
    - Cluster node status and load
    - Token issuance stats
    - Error counts
    """
    # Update current connection counts
    active_connections.labels(type="teacher").set(1 if manager.teacher else 0)
    active_connections.labels(type="student").set(len(manager.students))
    active_connections.labels(type="monitor").set(len(manager.monitors))

    # Update cluster metrics if in main mode
    mode = os.getenv("MODE", "standalone")
    if mode == "main" and cluster_manager:
        # Count nodes by status
        active_nodes = sum(
            1 for n in cluster_manager.nodes.values() if n.status == "active"
        )
        offline_nodes = sum(
            1 for n in cluster_manager.nodes.values() if n.status == "offline"
        )

        cluster_nodes_total.labels(status="active").set(active_nodes)
        cluster_nodes_total.labels(status="offline").set(offline_nodes)

        # Update per-node metrics
        for node in cluster_manager.nodes.values():
            cluster_load_percentage.labels(node_id=node.node_id).set(
                node.load_percentage
            )
            cluster_connections.labels(node_id=node.node_id).set(
                node.current_connections
            )

    # Generate Prometheus format
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# 연결 상태 확인 API
@app.get("/api/status")
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


@app.get("/api/viewers")
async def get_viewers():
    """Get current WebRTC viewers from MediaMTX with node distribution"""
    try:
        import httpx

        mode = os.getenv("MODE", "standalone")

        # Get viewers from main node MediaMTX
        mediamtx_url = "http://127.0.0.1:9997/v3/paths/list"

        total_viewers = 0
        viewers_list = []
        node_stats = {}

        async with httpx.AsyncClient(timeout=2.0) as client:
            # Get main node viewers
            response = await client.get(mediamtx_url)

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                # Find the live/stream path
                for item in items:
                    if item.get("name") == "live/stream":
                        readers = item.get("readers", [])
                        main_viewer_count = len(readers)
                        total_viewers += main_viewer_count

                        # Add main node viewers
                        for r in readers:
                            viewers_list.append(
                                {
                                    "id": r.get("id", "unknown"),
                                    "connected_at": r.get("created", ""),
                                    "type": "webrtc",
                                    "node": "main",
                                }
                            )

                        # Main node stats
                        node_stats["main"] = {
                            "name": "main",
                            "viewers": main_viewer_count,
                            "capacity": 150,
                            "load_percent": round((main_viewer_count / 150) * 100, 1),
                            "status": "active",
                        }

                        stream_ready = item.get("ready", False)
                        break
                else:
                    stream_ready = False
            else:
                stream_ready = False

            # Get sub node information from cluster manager
            if mode == "main" and cluster_manager:
                sub_nodes = cluster_manager.get_all_nodes()

                for node in sub_nodes:
                    node_name = node.get("node_name", "unknown")
                    # In development, sub nodes don't handle viewers yet
                    # This is a placeholder for future distributed viewer handling
                    node_stats[node_name] = {
                        "name": node_name,
                        "viewers": 0,
                        "capacity": 150,
                        "load_percent": 0.0,
                        "status": "standby",
                        "webrtc_port": node.get("webrtc_port", "unknown"),
                    }

        return {
            "total_viewers": total_viewers,
            "viewers": viewers_list,
            "stream_ready": stream_ready,
            "node_stats": node_stats,
            "cluster_mode": mode,
        }

    except Exception as e:
        logger.error(f"Failed to get viewers from MediaMTX: {e}")
        return {
            "total_viewers": 0,
            "viewers": [],
            "stream_ready": False,
            "node_stats": {},
            "cluster_mode": "unknown",
            "error": str(e),
        }


# Note: /api/screen endpoint removed - Android app now sends RTMP directly to MediaMTX
# MediaMTX converts RTMP to WebRTC automatically


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🎓 AIRClass Backend Server v2.0.0")
    print("=" * 60)
    print("📡 RTMP: rtmp://localhost:1935/live/stream")
    print("🎬 WebRTC: http://localhost:8889/live/stream/whep")
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
        reload=False,  # MediaMTX 프로세스 관리 때문에 reload 비활성화
        log_level="info",
    )
