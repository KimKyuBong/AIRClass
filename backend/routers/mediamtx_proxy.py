"""
MediaMTX 프록시 라우터
프론트엔드의 /live/* 요청을 올바른 MediaMTX 노드로 프록시
"""

from fastapi import APIRouter, Request
from fastapi.responses import Response
import httpx
import logging
import os
import jwt as pyjwt
from core.cluster import cluster_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/live/{path:path}")
@router.post("/live/{path:path}")
@router.patch("/live/{path:path}")
@router.delete("/live/{path:path}")
@router.options("/live/{path:path}")
async def proxy_to_mediamtx(path: str, request: Request):
    """
    프론트엔드의 /live/* 요청을 올바른 MediaMTX 노드로 프록시
    JWT 토큰에서 노드 정보를 추출하여 해당 노드로 라우팅
    """
    # JWT 토큰에서 노드 정보 추출
    query_params = dict(request.query_params)
    jwt_token = query_params.get("jwt", "")
    
    # 기본값: 로컬 MediaMTX (standalone 모드)
    target_host = "127.0.0.1"
    target_port = 8889
    
    # 클러스터 모드인 경우 JWT에서 노드 정보 추출
    mode = os.getenv("MODE", "main").lower()
    
    if mode == "main" and jwt_token:
        # Main 노드: JWT 토큰을 디코딩해서 어느 Sub 노드로 가야 하는지 판단
        try:
            # JWT 디코딩 (검증 없이, 페이로드만 추출)
            decoded = pyjwt.decode(jwt_token, options={"verify_signature": False})
            user_id = decoded.get("user_id", "")
            
            # 클러스터 매니저에서 해당 사용자가 할당된 노드 찾기
            # (토큰 발행 시 사용한 것과 동일한 로직)
            selected_node = cluster_manager.get_node_rendezvous(user_id)
            if selected_node:
                # Sub 노드의 호스트와 포트 사용
                # Docker 네트워크 내에서는 컨테이너 내부 포트(8889) 사용
                target_host = selected_node.host
                target_port = 8889  # 컨테이너 내부 MediaMTX 포트
                
                logger.info(f"🎯 Routing to Sub node: {selected_node.node_name} ({target_host}:{target_port})")
            else:
                logger.warning("⚠️ No healthy nodes, using local MediaMTX")
                target_host = "127.0.0.1"
                target_port = int(os.getenv("WEBRTC_PORT", "8889"))
        except Exception as e:
            logger.error(f"❌ Failed to decode JWT: {e}, using local MediaMTX")
            target_host = "127.0.0.1"
            target_port = int(os.getenv("WEBRTC_PORT", "8889"))
    elif mode == "sub":
        # Sub 노드는 자신의 MediaMTX 사용
        target_host = "127.0.0.1"
        target_port = int(os.getenv("WEBRTC_PORT", "8889"))
    else:
        # Standalone 모드
        target_host = "127.0.0.1"
        target_port = 8889
    
    # 타겟 URL 생성
    # path는 이미 "stream/whep" 형태로 들어옴 (/live/가 제거됨)
    # MediaMTX는 /live/stream/whep 형태를 기대하므로 live/ 추가
    target_url = f"http://{target_host}:{target_port}/live/{path}"
    if request.query_params:
        target_url += f"?{request.url.query}"
    
    logger.info(f"🔀 Proxying {request.method} /live/{path} -> {target_url}")
    
    # 요청 본문 읽기
    body = await request.body()
    
    # 헤더 복사 (Host 제외)
    headers = dict(request.headers)
    headers.pop("host", None)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
            
            # 응답 헤더 복사
            response_headers = dict(response.headers)
            # CORS 헤더 추가
            response_headers["Access-Control-Allow-Origin"] = "*"
            response_headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response_headers["Access-Control-Allow-Headers"] = "*"
            
            # Response 객체를 직접 반환
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type", "application/octet-stream")
            )
    except Exception as e:
        logger.error(f"❌ Proxy error: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={"error": str(e)},
            status_code=502,
        )
