"""
Monitoring Router
=================
시스템 모니터링 및 메트릭 엔드포인트

- GET /metrics: Prometheus 메트릭 노출
- GET /api/viewers: MediaMTX 뷰어 수 조회 (클러스터 지원)
"""

import os
import logging
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import PlainTextResponse
import httpx
from utils import get_connection_manager
from core.cluster import cluster_manager
from core.metrics import (
    active_connections,
    cluster_nodes_total,
    cluster_load_percentage,
    cluster_connections,
)

logger = logging.getLogger("uvicorn")
router = APIRouter(tags=["monitoring"])

# ConnectionManager 싱글톤 가져오기
manager = get_connection_manager()


@router.get("/metrics")
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
    mode = os.getenv("MODE", "main")
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


@router.get("/api/viewers")
async def get_viewers():
    """Get current WebRTC viewers from MediaMTX with node distribution"""
    try:
        mode = os.getenv("MODE", "main")
        
        from config import MEDIAMTX_API_URL

        # Get viewers from MediaMTX
        mediamtx_url = f"{MEDIAMTX_API_URL}/v3/paths/list"

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
