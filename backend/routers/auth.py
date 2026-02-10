"""
Authentication & Token Router
==============================
스트림 접근 토큰 발급 (Main-Sub 아키텍처)

Main 모드: 최적의 Sub 노드로 로드 밸런싱, Sub 노드에서 토큰 발급
Sub 모드: 직접 토큰 발급, 자신의 WebRTC URL 반환
"""

import os
import re
import logging
import secrets
import string
import subprocess
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException
import httpx
from core.cluster import cluster_manager
from core.metrics import tokens_issued_total
from fastapi import Body
from utils import generate_stream_token, generate_device_token, JWT_EXPIRATION_MINUTES
from config import SERVER_IP

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/token")
async def create_token_cluster_aware(user_type: str, user_id: str, action: str = "read"):
    """
    스트림 접근 토큰 발급 (Main-Sub 아키텍처)

    Main 모드: 최적의 Sub 노드로 리다이렉트
    Sub 모드: 직접 토큰 발급
    """
    mode = os.getenv("MODE", "main")

    # ============================================
    # Main 모드: 로드 밸런싱
    # ============================================
    if mode == "main":
        # Production: Load balancing enabled by default
        # Set USE_MAIN_WEBRTC=true to bypass load balancing (development only)
        use_main_webrtc = os.getenv("USE_MAIN_WEBRTC", "false").lower() == "true"

        # Teacher는 항상 Main 노드에 연결 (RTMP 스트리밍 소스이므로)
        # Student만 Sub 노드로 로드 밸런싱
        # action이 'publish'인 경우(교사 화면 공유)도 Main으로 연결
        if not use_main_webrtc and user_type == "student" and action == "read":
            # Rendezvous Hashing을 사용하여 user_id 기반 일관성 있는 노드 선택
            node = cluster_manager.get_node_for_stream(user_id, use_sticky=True)
            if not node:
                raise HTTPException(status_code=503, detail="No healthy nodes available")

            # 메인 노드 자신이 선택되었다면 직접 토큰 발급 (리다이렉트 없음)
            if node.node_id == cluster_manager.main_node_id:
                logger.info(f"✅ Main node selected for {user_id}, serving directly")
                # Sub 모드 로직으로 진행
            else:
                # Sub의 토큰 발급 엔드포인트로 리다이렉트
                redirect_url = f"{node.api_url}/api/token?user_type={user_type}&user_id={user_id}&action={action}"

                # 직접 Sub에 요청하여 토큰 받기
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.post(redirect_url)
                        if response.status_code == 200:
                            data = response.json()

                            # Sub 노드가 반환한 external_port 사용
                            external_port = data.get("external_port")
                            if external_port:
                                token = data.get("token", "")
                                server_ip = os.getenv("SERVER_IP", "localhost")
                                data["webrtc_url"] = (
                                    f"http://{server_ip}:{external_port}/live/stream/whep?jwt={token}"
                                )
                                logger.info(
                                    f"Using absolute URL for WebRTC: http://{server_ip}:{external_port}"
                                )

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
                            status_code=503,
                            detail=f"Node communication error: {str(e)}",
                        )

    # ============================================
    # Sub 모드: 직접 토큰 발급
    # ============================================
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

    # WebRTC URL 생성
    node_name = os.getenv("NODE_NAME", "main")
    server_ip = os.getenv("SERVER_IP", "localhost")

    # 환경 변수로 명시적 URL 지정 가능 (개발용)
    whep_base = os.getenv("WHEP_BASE_URL", "").rstrip("/")
    whip_base = os.getenv("WHIP_BASE_URL", "").rstrip("/")

    if whep_base and action != "publish":
        webrtc_url = f"{whep_base}/live/stream/whep?jwt={token}"
    elif whip_base and action == "publish":
        webrtc_url = f"{whip_base}/live/stream/whip?jwt={token}"
    else:
        # 환경 변수에서 외부 포트 가져오기 (Docker Compose에서 설정)
        external_port = os.getenv("WEBRTC_EXTERNAL_PORT")

        if external_port:
            if action == "publish":
                webrtc_url = f"http://{server_ip}:{external_port}/live/stream/whip?jwt={token}"
            else:
                webrtc_url = f"http://{server_ip}:{external_port}/live/stream/whep?jwt={token}"
            logger.info(f"Using absolute URL for WebRTC: http://{server_ip}:{external_port}")
        else:
            # Fallback to relative path
            if action == "publish":
                webrtc_url = f"/live/stream/whip?jwt={token}"
            else:
                webrtc_url = f"/live/stream/whep?jwt={token}"
            logger.warning("WEBRTC_EXTERNAL_PORT not set, using relative path")

    # 응답 데이터 생성
    response_data = {
        "token": token,
        "webrtc_url": webrtc_url,
        "expires_in": JWT_EXPIRATION_MINUTES * 60,
        "user_type": user_type,
        "user_id": user_id,
        "mode": mode,
        "action": action,
        "node_name": node_name,
        "node_id": os.getenv("NODE_ID", node_name),
        "external_port": os.getenv("WEBRTC_EXTERNAL_PORT"),  # Main 노드에서 사용
    }

    return response_data


# TOTP 검증 후 디바이스(Android 송신 앱 등) 연동용 토큰
DEVICE_TOKEN_EXPIRES_DAYS = 30


@router.post("/auth/device-token")
async def create_device_token(totp_code: str = Body(..., embed=True)):
    """
    TOTP 6자리 코드 검증 후 디바이스 연동용 JWT 발급.
    Android 송신 앱 등에서 앱에 등록한 TOTP 코드를 보내면 30일 유효한 토큰을 반환.
    """
    import os

    totp_secret = os.getenv("TOTP_SECRET")
    if not totp_secret:
        raise HTTPException(
            status_code=503,
            detail="TOTP not configured. Set TOTP_SECRET in .env (e.g. via GUI first-time setup).",
        )
    try:
        from core.totp_utils import verify_totp_code
    except ImportError:
        raise HTTPException(status_code=503, detail="TOTP not available (pyotp not installed)")

    # 1. TOTP 검증 (재생 공격 방지 포함)
    if not verify_totp_code(totp_secret, totp_code):
        # 백업 코드 검증 시도 (추가 구현 가능)
        raise HTTPException(status_code=403, detail="Invalid or expired TOTP code")

    # 2. 30일 만료 토큰 발급
    token = generate_device_token(expires_minutes=DEVICE_TOKEN_EXPIRES_DAYS * 24 * 60)
    return {
        "token": token,
        "expires_in_days": DEVICE_TOKEN_EXPIRES_DAYS,
        "scope": "device",
    }


@router.post("/auth/refresh-token")
async def refresh_device_token(token: str = Body(..., embed=True)):
    """
    기존 유효한 디바이스 토큰을 사용하여 새로운 토큰으로 갱신.
    """
    from utils.jwt_auth import verify_token

    payload = verify_token(token)
    if not payload or payload.get("scope") != "device":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    new_token = generate_device_token(expires_minutes=DEVICE_TOKEN_EXPIRES_DAYS * 24 * 60)
    return {
        "token": new_token,
        "expires_in_days": DEVICE_TOKEN_EXPIRES_DAYS,
        "scope": "device",
    }


@router.post("/auth/backup-codes")
async def generate_backup_codes():
    """
    새로운 백업 코드 세트 생성 (8자리 숫자 10개).
    기존 백업 코드는 무효화됨.
    """
    import secrets
    import string
    from core.database import get_database_manager

    db = get_database_manager()
    if db is None or db.db is None:
        raise HTTPException(status_code=503, detail="Database not available")

    # 8자리 숫자 코드 10개 생성
    new_codes = ["".join(secrets.choice(string.digits) for _ in range(8)) for _ in range(10)]

    # DB에 저장 (간단하게 teacher_id="admin"으로 저장하거나 전역 설정으로 저장)
    await db.db.backup_codes.update_one(
        {"user_id": "admin"},
        {"$set": {"codes": new_codes, "created_at": datetime.now(UTC)}},
        upsert=True,
    )

    return {"backup_codes": new_codes}
