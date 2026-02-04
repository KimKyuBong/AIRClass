"""
Monitoring Router
=================
시스템 모니터링 및 메트릭 엔드포인트

- GET /metrics: Prometheus 메트릭 노출
- GET /api/viewers: LiveKit 참여자 수 조회
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


# LiveKit API는 필요시 동적 import (순환 의존 방지)
def get_livekit_api():
    from routers.livekit import lkapi
    from livekit import api

    return lkapi, api


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
        active_nodes = sum(1 for n in cluster_manager.nodes.values() if n.status == "active")
        offline_nodes = sum(1 for n in cluster_manager.nodes.values() if n.status == "offline")

        cluster_nodes_total.labels(status="active").set(active_nodes)
        cluster_nodes_total.labels(status="offline").set(offline_nodes)

        # Update per-node metrics
        for node in cluster_manager.nodes.values():
            cluster_load_percentage.labels(node_id=node.node_id).set(node.load_percentage)
            cluster_connections.labels(node_id=node.node_id).set(node.current_connections)

    # Generate Prometheus format
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/api/viewers")
async def get_viewers():
    """Get current LiveKit participants with room distribution"""
    try:
        mode = os.getenv("MODE", "main")

        # Get LiveKit API
        lkapi, api = get_livekit_api()

        # Get rooms from LiveKit
        rooms_res = await lkapi.room.list_rooms(api.ListRoomsRequest())

        total_viewers = 0
        viewers_list = []
        room_stats = {}

        for room in rooms_res.rooms:
            # Get participants for each room
            participants_res = await lkapi.room.list_participants(
                api.ListParticipantsRequest(room=room.name)
            )

            room_viewer_count = len(participants_res.participants)
            total_viewers += room_viewer_count

            # Add participants to list
            for p in participants_res.participants:
                viewers_list.append(
                    {
                        "id": p.identity,
                        "connected_at": p.joined_at,
                        "type": "livekit",
                        "room": room.name,
                    }
                )

            # Room stats
            room_stats[room.name] = {
                "name": room.name,
                "viewers": room_viewer_count,
                "status": "active" if room_viewer_count > 0 else "idle",
            }

        return {
            "total_viewers": total_viewers,
            "viewers": viewers_list,
            "room_stats": room_stats,
            "cluster_mode": mode,
        }

    except Exception as e:
        logger.error(f"Failed to get viewers from LiveKit: {e}")
        return {
            "total_viewers": 0,
            "viewers": [],
            "room_stats": {},
            "cluster_mode": "unknown",
            "error": str(e),
        }
