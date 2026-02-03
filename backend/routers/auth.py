"""
Authentication & Token Router
==============================
스트림 접근 토큰 발급 (클러스터 지원)

Main 모드: 최적의 Sub 노드로 로드 밸런싱
Sub/Standalone 모드: 직접 토큰 발급
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
                                                token = data.get("token", "")
                                                whep_base = os.getenv("WHEP_BASE_URL", "").rstrip("/")
                                                if whep_base:
                                                    data["webrtc_url"] = f"{whep_base}/live/stream/whep?jwt={token}"
                                                    logger.info("Rewrote WebRTC URL to WHEP_BASE_URL (same-origin)")
                                                else:
                                                    # Sub 노드의 external WebRTC 포트로 URL 생성
                                                    data["webrtc_url"] = (
                                                        f"http://{SERVER_IP}:{external_webrtc_port}/live/stream/whep?jwt={token}"
                                                    )
                                                    logger.info(
                                                        f"Rewrote WebRTC URL to use Sub node at {SERVER_IP}:{external_webrtc_port}"
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
    # 개발 시 HTTPS 페이지에서 Mixed Content 방지: WHEP_BASE_URL=https://localhost:5175 등으로 프론트 origin 지정
    whep_base = os.getenv("WHEP_BASE_URL", "").rstrip("/")
    whip_base = os.getenv("WHIP_BASE_URL", "").rstrip("/")

    if whep_base and action != "publish":
        webrtc_url = f"{whep_base}/live/stream/whep?jwt={token}"
    elif whip_base and action == "publish":
        webrtc_url = f"{whip_base}/live/stream/whip?jwt={token}"
    else:
        node_host = os.getenv("NODE_HOST", "localhost")
        webrtc_port = os.getenv("WEBRTC_PORT", "8889")
        if mode == "main":
            node_host = SERVER_IP
        if action == "publish":
            webrtc_url = f"http://{node_host}:{webrtc_port}/live/stream/whip?jwt={token}"
        else:
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

    # 모든 모드에서 node_name과 node_id 추가 (클러스터 정보 표시용)
    response_data["node_name"] = os.getenv("NODE_NAME", mode)
    response_data["node_id"] = os.getenv("NODE_ID", mode)

    return response_data
