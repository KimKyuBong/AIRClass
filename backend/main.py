"""
AIRClass Backend Server
FastAPI + MediaMTX를 사용한 실시간 HLS 스트리밍 백엔드
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
from cluster import cluster_manager, init_cluster_mode, shutdown_cluster
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
    description="Real-time HLS streaming with chat support",
    version="2.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    "Number of active WebSocket/HLS connections",
    ["type"],  # teacher, student, monitor, hls
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
    """MediaMTX RTMP/HLS 서버 시작"""
    global mediamtx_process

    if mediamtx_process is None:
        print("🚀 Starting MediaMTX server...")
        mediamtx_process = subprocess.Popen(
            ["./mediamtx"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(f"✅ MediaMTX started (PID: {mediamtx_process.pid})")
        print("📡 RTMP: rtmp://localhost:1935/live/stream")
        print("🎬 HLS: http://localhost:8888/live/stream/index.m3u8")


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


def generate_stream_token(user_type: str, user_id: str) -> str:
    """
    스트림 접근 토큰 생성

    Args:
        user_type: 'teacher', 'student', 'monitor'
        user_id: 사용자 ID (학생 이름 등)

    Returns:
        JWT 토큰 문자열
    """
    expiration = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "user_type": user_type,
        "user_id": user_id,
        "exp": expiration,
        "iat": datetime.utcnow(),
        "action": "read",  # MediaMTX action
        "path": "live/stream",  # MediaMTX path
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    active_tokens.add(token)
    return token


def verify_token(token: str) -> Optional[dict]:
    """토큰 검증"""
    try:
        # JWT 검증만 수행 (active_tokens는 Master에서만 관리하므로 Slave에서는 체크하지 않음)
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print(f"[verify_token] ✅ Token valid. Payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError as e:
        print(f"[verify_token] ❌ Token expired: {e}")
        # Master에서만 active_tokens 정리
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
        "hls_url": "http://localhost:8888/live/stream/index.m3u8",
        "frontend_url": "http://localhost:5173",
        "security": "JWT token required for HLS access",
    }


async def get_external_hls_port(node_id: str) -> Optional[int]:
    """
    Docker 컨테이너의 외부에 매핑된 HLS 포트를 찾습니다.

    Args:
        node_id: 노드 ID (예: "slave-e3300a10f9b7")

    Returns:
        외부 포트 번호 또는 None
    """
    try:
        # node_id에서 컨테이너 호스트명 추출 (slave-HOSTNAME 형식)
        # Docker Compose는 airclass-slave-1, airclass-slave-2 등의 이름 사용
        # node_id는 "slave-<hostname>" 형식이므로, 실제 컨테이너는 airclass-slave-* 패턴

        # 모든 slave 컨테이너의 포트 매핑 확인
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=airclass-slave",
                "--format",
                "{{.Names}}\t{{.Ports}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.error(f"Failed to get docker containers: {result.stderr}")
            return None

        # 각 컨테이너의 포트 매핑 파싱
        # 출력 예: "airclass-slave-1\t0.0.0.0:60064->8888/tcp, ..."
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            container_name = parts[0]
            ports_str = parts[1]

            # node_id의 hostname 부분과 컨테이너 호스트명 매칭 확인
            # docker exec로 컨테이너의 HOSTNAME 환경변수 확인
            hostname_check = subprocess.run(
                ["docker", "exec", container_name, "hostname"],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if hostname_check.returncode == 0:
                container_hostname = hostname_check.stdout.strip()
                expected_node_id = f"slave-{container_hostname}"

                if expected_node_id == node_id:
                    # 이 컨테이너가 맞음! 8888 포트의 외부 매핑 찾기
                    # 포트 형식: "0.0.0.0:60064->8888/tcp"
                    import re

                    match = re.search(r"0\.0\.0\.0:(\d+)->8888/tcp", ports_str)
                    if match:
                        external_port = int(match.group(1))
                        logger.info(
                            f"Found external HLS port for {node_id}: {external_port}"
                        )
                        return external_port

        logger.warning(f"Could not find external port mapping for node {node_id}")
        return None

    except subprocess.TimeoutExpired:
        logger.error("Timeout while querying Docker containers")
        return None
    except Exception as e:
        logger.error(f"Error getting external HLS port: {e}")
        return None


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

    # Master 모드: 내부 프록시 스크립트의 RTMP read 허용 (localhost에서만)
    if action == "read" and protocol == "rtmp":
        ip = request.get("ip", "")
        if ip in ["127.0.0.1", "::1", "localhost"]:
            print(f"[MediaMTX Auth] ✅ Allowing internal RTMP read from {ip}")
            return {"status": "ok"}
        else:
            print(f"[MediaMTX Auth] ❌ RTMP read denied - not from localhost (ip={ip})")
            raise HTTPException(status_code=403, detail="RTMP read not allowed")

    # Master 모드: 내부 FFmpeg의 RTSP read 허용 (모든 localhost 연결)
    # FFmpeg 프록시는 항상 localhost에서만 실행되므로 RTSP read는 모두 허용
    if action == "read" and protocol == "rtsp":
        print(f"[MediaMTX Auth] ✅ Allowing internal RTSP read (FFmpeg proxy)")
        return {"status": "ok"}

    # HLS read는 JWT 토큰 필요
    if action == "read" and protocol == "hls":
        # query에서 jwt 파라미터 추출
        token = None
        if "jwt=" in query:
            # 첫 번째 jwt= 값만 추출 (중복 방지)
            token = query.split("jwt=")[1].split("&")[0]
            print(f"[MediaMTX Auth] Extracted JWT token: {token[:50]}...")

        if not token:
            print(f"[MediaMTX Auth] ❌ HLS read denied - no token")
            raise HTTPException(status_code=401, detail="Token required")

        # 토큰 검증
        payload = verify_token(token)
        if not payload:
            print(f"[MediaMTX Auth] ❌ HLS read denied - invalid token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # path 검증
        if payload.get("path") != path:
            print(
                f"[MediaMTX Auth] ❌ HLS read denied - path mismatch (expected: {payload.get('path')}, got: {path})"
            )
            raise HTTPException(status_code=403, detail="Path mismatch")

        print(f"[MediaMTX Auth] ✅ Allowing HLS read for {payload.get('user_id')}")
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

            # Note: Screen data is now handled by MediaMTX HLS streaming
            # Android app sends RTMP to MediaMTX, clients play HLS directly

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
        # Note: Students now receive video via HLS stream from MediaMTX
        # URL: http://localhost:8888/live/stream/index.m3u8

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
        # Note: Monitors now receive video via HLS stream from MediaMTX
        # URL: http://localhost:8888/live/stream/index.m3u8

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
# Cluster Management APIs (Master/Slave)
# ============================================================


@app.post("/cluster/register")
async def register_node(request: Request):
    """Slave 노드 등록 (Master only)"""
    mode = os.getenv("MODE", "standalone")
    if mode != "master":
        raise HTTPException(status_code=403, detail="Only master can register nodes")

    data = await request.json()
    from cluster import NodeInfo
    from datetime import datetime

    # last_heartbeat을 ISO string에서 datetime으로 변환
    if "last_heartbeat" in data and isinstance(data["last_heartbeat"], str):
        data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])

    node = NodeInfo(**data)
    cluster_manager.register_node(node)
    return {"status": "registered", "node_id": node.node_id}


@app.post("/cluster/unregister")
async def unregister_node(request: Request):
    """Slave 노드 등록 해제 (Master only)"""
    mode = os.getenv("MODE", "standalone")
    if mode != "master":
        raise HTTPException(status_code=403, detail="Only master can unregister nodes")

    data = await request.json()
    node_id = data.get("node_id")
    success = cluster_manager.unregister_node(node_id)

    if success:
        return {"status": "unregistered", "node_id": node_id}
    else:
        raise HTTPException(status_code=404, detail="Node not found")


@app.post("/cluster/stats")
async def update_node_stats(request: Request):
    """노드 통계 업데이트 (Slave → Master)"""
    mode = os.getenv("MODE", "standalone")
    if mode != "master":
        raise HTTPException(status_code=403, detail="Only master can receive stats")

    data = await request.json()
    node_id = data.get("node_id")
    stats = data.get("stats", {})

    success = cluster_manager.update_node_stats(node_id, stats)
    if success:
        return {"status": "updated"}
    else:
        raise HTTPException(status_code=404, detail="Node not found")


@app.get("/cluster/nodes")
async def get_cluster_nodes():
    """클러스터 노드 목록 조회"""
    mode = os.getenv("MODE", "standalone")
    if mode != "master":
        raise HTTPException(status_code=403, detail="Only master has cluster info")

    return cluster_manager.get_cluster_stats()


@app.get("/cluster/best-node")
async def get_best_node():
    """최적의 노드 선택 (로드 밸런싱)"""
    mode = os.getenv("MODE", "standalone")
    if mode != "master":
        raise HTTPException(status_code=403, detail="Only master can route")

    node = cluster_manager.get_least_loaded_node()
    if not node:
        raise HTTPException(status_code=503, detail="No healthy nodes available")

    return {
        "node_id": node.node_id,
        "node_name": node.node_name,
        "rtmp_url": node.rtmp_url,
        "hls_url": node.hls_url,
        "api_url": node.api_url,
        "load_percentage": node.load_percentage,
        "current_connections": node.current_connections,
        "max_connections": node.max_connections,
    }


# ============================================================
# Modified Token API for Cluster Mode
# ============================================================


@app.post("/api/token")
async def create_token_cluster_aware(user_type: str, user_id: str):
    """
    스트림 접근 토큰 발급 (클러스터 지원)

    Master 모드: 최적의 Slave 노드로 리다이렉트
    Slave/Standalone 모드: 직접 토큰 발급
    """
    mode = os.getenv("MODE", "standalone")

    # DEVELOPMENT: Master에서 직접 WebRTC 제공 (NAT 문제 회피)
    use_master_webrtc = os.getenv("USE_MASTER_WEBRTC", "true").lower() == "true"

    # Master 모드: 최적의 Slave 선택하여 리다이렉트
    if mode == "master" and not use_master_webrtc:
        node = cluster_manager.get_least_loaded_node()
        if not node:
            raise HTTPException(status_code=503, detail="No healthy nodes available")

        # Slave의 토큰 발급 엔드포인트로 리다이렉트
        redirect_url = (
            f"{node.api_url}/api/token?user_type={user_type}&user_id={user_id}"
        )

        # 직접 Slave에 요청하여 토큰 받기
        import httpx
        import re

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(redirect_url)
                if response.status_code == 200:
                    data = response.json()

                    # Docker 외부 접근을 위해 호스트에 매핑된 포트 찾기 (HLS & WebRTC)
                    try:
                        # Get Docker container port mappings
                        result = subprocess.run(
                            [
                                "docker",
                                "ps",
                                "--filter",
                                "name=airclass-slave",
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
                                    container_hostname = hostname_check.stdout.strip()
                                    expected_node_id = f"slave-{container_hostname}"

                                    if expected_node_id == node.node_id:
                                        # Extract external ports for HLS (8888) and WebRTC (8889)
                                        hls_match = re.search(
                                            r"0\.0\.0\.0:(\d+)->8888/tcp", ports_str
                                        )
                                        webrtc_match = re.search(
                                            r"0\.0\.0\.0:(\d+)->8889/tcp", ports_str
                                        )

                                        if hls_match:
                                            external_hls_port = hls_match.group(1)
                                            # Rewrite HLS URL to use localhost with external port
                                            token = data.get("token", "")
                                            data["hls_url"] = (
                                                f"http://localhost:{external_hls_port}/live/stream/index.m3u8?jwt={token}"
                                            )
                                            logger.info(
                                                f"Rewrote HLS URL to use external port {external_hls_port}"
                                            )

                                        if webrtc_match:
                                            external_webrtc_port = webrtc_match.group(1)
                                            # Rewrite WebRTC URL to use localhost with external port
                                            token = data.get("token", "")
                                            data["webrtc_url"] = (
                                                f"http://localhost:{external_webrtc_port}/live/stream/whep?jwt={token}"
                                            )
                                            logger.info(
                                                f"Rewrote WebRTC URL to use external port {external_webrtc_port}"
                                            )

                                        break
                    except Exception as e:
                        logger.error(f"Error finding external ports: {e}")

                    # Master 정보 추가
                    data["routed_by"] = "master"
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

    # Slave/Standalone 모드: 기존 로직 (직접 토큰 발급)
    if user_type not in ["teacher", "student", "monitor"]:
        raise HTTPException(status_code=400, detail="Invalid user_type")

    if not user_id or len(user_id) < 1:
        raise HTTPException(status_code=400, detail="user_id required")

    token = generate_stream_token(user_type, user_id)

    # Track token issuance
    tokens_issued_total.labels(user_type=user_type).inc()

    # HLS URL 생성 (Slave는 자신의 주소 반환)
    node_host = os.getenv("NODE_HOST", "localhost")
    hls_port = os.getenv("HLS_PORT", "8888")
    webrtc_port = os.getenv("WEBRTC_PORT", "8889")

    # Master 모드에서는 localhost 사용 (Docker 외부 접근)
    if mode == "master":
        node_host = "localhost"

    hls_url = f"http://{node_host}:{hls_port}/live/stream/index.m3u8?jwt={token}"
    webrtc_url = f"http://{node_host}:{webrtc_port}/live/stream/whep?jwt={token}"

    return {
        "token": token,
        "hls_url": hls_url,
        "webrtc_url": webrtc_url,
        "expires_in": JWT_EXPIRATION_MINUTES * 60,
        "user_type": user_type,
        "user_id": user_id,
        "mode": mode,
    }


# ============================================================
# Health Check API
# ============================================================


@app.get("/health")
async def health_check():
    """
    헬스 체크 (Docker healthcheck용)

    Returns:
        - status: healthy/degraded
        - mode: master/slave/standalone
        - stream_active: MediaMTX에서 스트림을 받고 있는지 여부
        - timestamp: 현재 시간
    """
    mode = os.getenv("MODE", "standalone")

    # MediaMTX API로 스트림 상태 확인 (v2 API 사용)
    stream_active = False
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2.0) as client:
            # MediaMTX API v2: GET /v2/paths/list
            response = await client.get("http://127.0.0.1:9997/v2/paths/list")
            if response.status_code == 200:
                data = response.json()
                # "live/stream" 경로에 활성 publisher가 있는지 확인
                items = data.get("items", [])
                for item in items:
                    if item.get("name") == "live/stream":
                        # 활성 reader나 publisher가 있는지 확인
                        readers = item.get("readers", 0)
                        source_ready = item.get("sourceReady", False)

                        if source_ready or readers > 0:
                            stream_active = True
                            logger.debug(
                                f"Stream active: sourceReady={source_ready}, readers={readers}"
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

    # Update cluster metrics if in master mode
    mode = os.getenv("MODE", "standalone")
    if mode == "master" and cluster_manager:
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
        "hls_stream_url": "http://localhost:8888/live/stream/index.m3u8",
    }


# Note: /api/screen endpoint removed - Android app now sends RTMP directly to MediaMTX
# MediaMTX converts RTMP to HLS automatically at http://localhost:8888/live/stream/index.m3u8


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🎓 AIRClass Backend Server v2.0.0")
    print("=" * 60)
    print("📡 RTMP: rtmp://localhost:1935/live/stream")
    print("🎬 HLS: http://localhost:8888/live/stream/index.m3u8")
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
