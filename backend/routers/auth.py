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
import subprocess
from fastapi import APIRouter, HTTPException
import httpx
from core.cluster import cluster_manager
from core.metrics import tokens_issued_total
from utils import generate_stream_token, JWT_EXPIRATION_MINUTES
from config import SERVER_IP

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/token")
async def create_token_cluster_aware(
    user_type: str, user_id: str, action: str = "read"
):
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
                raise HTTPException(
                    status_code=503, detail="No healthy nodes available"
                )

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
            logger.info(
                f"Using absolute URL for WebRTC: http://{server_ip}:{external_port}"
            )
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
