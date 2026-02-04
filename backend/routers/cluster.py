"""
Cluster Management Router
=========================
클러스터 노드 등록/해제 및 통계 업데이트 엔드포인트

Main 노드에서만 동작:
- POST /cluster/register: Sub 노드 등록 (HMAC 인증)
- POST /cluster/unregister: Sub 노드 등록 해제
- POST /cluster/stats: Sub 노드 통계 업데이트 (HMAC 인증)
- GET /cluster/nodes: 클러스터 노드 목록 조회
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from core.cluster import cluster_manager, NodeInfo, verify_cluster_auth_token

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/cluster", tags=["cluster"])


@router.post("/register")
async def register_node(request: Request):
    """Sub 노드 등록 (HMAC 인증)"""
    mode = os.getenv("MODE", "main")
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


@router.post("/unregister")
async def unregister_node(request: Request):
    """Sub 노드 등록 해제 (Main only)"""
    mode = os.getenv("MODE", "main")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main can unregister nodes")

    data = await request.json()
    node_id = data.get("node_id")
    success = cluster_manager.unregister_node(node_id)

    if success:
        return {"status": "unregistered", "node_id": node_id}
    else:
        raise HTTPException(status_code=404, detail="Node not found")


@router.post("/stats")
async def update_node_stats(request: Request):
    """노드 통계 업데이트 (Sub → Main, HMAC 인증)"""
    mode = os.getenv("MODE", "main")
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


@router.get("/nodes")
async def get_cluster_nodes():
    """클러스터 노드 목록 조회"""
    mode = os.getenv("MODE", "main")
    if mode != "main":
        raise HTTPException(status_code=403, detail="Only main has cluster info")

    return cluster_manager.get_cluster_stats()
