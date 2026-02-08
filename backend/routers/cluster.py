"""
Cluster Management Router
=========================
클러스터 노드 등록/해제 및 통계 업데이트 엔드포인트

Main 노드에서만 동작:
- POST /cluster/register: Sub 노드 등록 (HMAC 또는 Bearer device 토큰)
- GET /cluster/totp-setup: TOTP QR/프로비저닝 URI (앱·서브노드 등록용)
- POST /cluster/unregister: Sub 노드 등록 해제
- POST /cluster/stats: Sub 노드 통계 업데이트 (HMAC 또는 Bearer)
- GET /cluster/nodes: 클러스터 노드 목록 조회

인증: CLUSTER_SECRET(HMAC) 또는 TOTP로 발급한 device 토큰(Bearer) 중 하나.
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from core.cluster import cluster_manager, NodeInfo, verify_cluster_auth_token

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/cluster", tags=["cluster"])


def _auth_via_bearer(request: Request) -> bool:
    """Authorization: Bearer <device_jwt> 검증. 성공 시 True, 실패 시 False."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    try:
        from utils import verify_token
        payload = verify_token(token)
        if payload and payload.get("scope") == "device":
            return True
    except Exception:
        pass
    return False


def _auth_cluster_request(request: Request, data: dict) -> bool:
    """클러스터 API 인증: Bearer device 토큰 또는 HMAC(CLUSTER_SECRET)."""
    if _auth_via_bearer(request):
        return True
    cluster_secret = os.getenv("CLUSTER_SECRET", "")
    if not cluster_secret:
        return False
    provided = data.get("auth_token")
    timestamp = data.get("timestamp")
    if not provided or not timestamp:
        return False
    return verify_cluster_auth_token(cluster_secret, timestamp, provided)


def _require_totp_if_configured(data: dict) -> None:
    """TOTP_SECRET이 설정된 경우 totp_code 검증. 실패 시 HTTPException."""
    totp_secret = os.getenv("TOTP_SECRET")
    if not totp_secret:
        return
    try:
        from core.totp_utils import verify_totp_code
    except ImportError:
        logger.warning("TOTP configured but pyotp not installed")
        return
    code = (data.get("totp_code") or "").strip()
    if not code:
        raise HTTPException(
            status_code=403,
            detail="TOTP code required (6 digits). Register with QR from /cluster/totp-setup first.",
        )
    if not verify_totp_code(totp_secret, code):
        raise HTTPException(status_code=403, detail="Invalid or expired TOTP code")


@router.post("/register")
async def register_node(request: Request):
    """Sub 노드 등록. 인증: Bearer device 토큰 또는 HMAC(CLUSTER_SECRET) + TOTP(선택)."""
    mode = os.getenv("MODE", "main")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main can register nodes")

    data = await request.json()

    # 인증: Bearer device 토큰 또는 HMAC
    if _auth_via_bearer(request):
        pass  # Bearer로 이미 인증됨 (TOTP로 발급된 토큰)
    else:
        cluster_secret = os.getenv("CLUSTER_SECRET", "")
        if not cluster_secret:
            logger.error("❌ CLUSTER_SECRET not set in Main node!")
            raise HTTPException(status_code=500, detail="Server configuration error")
        provided_token = data.get("auth_token")
        timestamp = data.get("timestamp")
        if not provided_token or not timestamp:
            raise HTTPException(status_code=403, detail="Authentication required (Bearer token or auth_token+timestamp)")
        if not verify_cluster_auth_token(cluster_secret, timestamp, provided_token):
            logger.warning(f"⚠️ Authentication failed for node: {data.get('node_name', 'unknown')}")
            raise HTTPException(status_code=403, detail="Authentication failed: CLUSTER_SECRET mismatch")
        _require_totp_if_configured(data)

    # 인증 성공 - auth_token, timestamp, totp_code는 NodeInfo에 없으므로 제거
    data.pop("auth_token", None)
    data.pop("timestamp", None)
    data.pop("totp_code", None)

    # last_heartbeat을 ISO string에서 datetime으로 변환
    if "last_heartbeat" in data and isinstance(data["last_heartbeat"], str):
        data["last_heartbeat"] = datetime.fromisoformat(data["last_heartbeat"])

    node = NodeInfo(**data)
    cluster_manager.register_node(node)
    logger.info(f"✅ Node authenticated and registered: {node.node_name}")
    return {"status": "registered", "node_id": node.node_id}


@router.get("/totp-setup")
async def get_totp_setup():
    """
    TOTP 프로비저닝 URI 및 QR용 데이터 반환.
    .env에 TOTP_SECRET이 있을 때만 사용. 앱에서 QR 스캔 후 6자리 코드로 Sub 등록·Android 연동.
    """
    mode = os.getenv("MODE", "main")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main node exposes TOTP setup")

    try:
        from core.totp_utils import get_totp_secret, get_provisioning_uri
    except ImportError:
        raise HTTPException(status_code=503, detail="TOTP not available (pyotp not installed)")

    secret = get_totp_secret()
    if not secret:
        raise HTTPException(
            status_code=404,
            detail="TOTP_SECRET not set in .env. Set it (e.g. via GUI first-time setup) to enable TOTP.",
        )

    uri = get_provisioning_uri(secret, issuer="AIRClass", account_name="cluster")
    # QR 이미지 base64 (선택)
    try:
        import qrcode
        import base64
        import io
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        qr_base64 = None

    return JSONResponse(content={
        "provisioning_uri": uri,
        "qr_image_base64": qr_base64,
        "hint": "Scan with any TOTP app (Google Authenticator, Authy, etc.). Use the 6-digit code for Sub registration and device linking.",
    })


@router.post("/unregister")
async def unregister_node(request: Request):
    """Sub 노드 등록 해제 (Main only). 인증: Bearer device 토큰 또는 HMAC(CLUSTER_SECRET)."""
    mode = os.getenv("MODE", "main")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main can unregister nodes")

    data = await request.json()
    if not _auth_cluster_request(request, data):
        raise HTTPException(status_code=403, detail="Authentication required")
    node_id = data.get("node_id")
    success = cluster_manager.unregister_node(node_id)

    if success:
        return {"status": "unregistered", "node_id": node_id}
    else:
        raise HTTPException(status_code=404, detail="Node not found")


@router.post("/stats")
async def update_node_stats(request: Request):
    """노드 통계 업데이트 (Sub → Main). 인증: Bearer device 토큰 또는 HMAC."""
    mode = os.getenv("MODE", "main")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main can receive stats")

    data = await request.json()

    if not _auth_cluster_request(request, data):
        logger.warning(f"⚠️ Stats authentication failed for node: {data.get('node_id', 'unknown')}")
        raise HTTPException(status_code=403, detail="Authentication failed")

    # 인증 성공
    node_id = data.get("node_id")
    stats = data.get("stats", {})

    success = cluster_manager.update_node_stats(node_id, stats)

    if not success:
        raise HTTPException(status_code=404, detail="Node not found")

    return {"status": "updated"}


@router.get("/nodes")
async def get_cluster_nodes():
    """클러스터 노드 목록 조회"""
    mode = os.getenv("MODE", "main")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main has cluster info")

    return cluster_manager.get_cluster_stats()
