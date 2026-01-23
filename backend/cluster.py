"""
AIRClass Cluster Management
Master-Slave 아키텍처 구현

Master: 요청을 받아 최적의 Slave로 라우팅
Slave: 실제 스트리밍 처리 및 Master에 상태 보고
"""

import asyncio
import httpx
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from fastapi import HTTPException
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    """노드 정보"""

    node_id: str
    node_name: str
    host: str
    port: int
    rtmp_port: int
    hls_port: int
    webrtc_port: int
    max_connections: int
    current_connections: int
    cpu_usage: float
    memory_usage: float
    status: str  # "healthy", "warning", "critical", "offline"
    last_heartbeat: datetime

    @property
    def load_percentage(self) -> float:
        """부하율 계산"""
        return (self.current_connections / self.max_connections) * 100

    @property
    def is_healthy(self) -> bool:
        """헬스 체크"""
        age = datetime.now() - self.last_heartbeat
        return self.status == "healthy" and age < timedelta(seconds=30)

    @property
    def rtmp_url(self) -> str:
        return f"rtmp://{self.host}:{self.rtmp_port}/live/stream"

    @property
    def hls_url(self) -> str:
        return f"http://{self.host}:{self.hls_port}/live/stream/index.m3u8"

    @property
    def webrtc_url(self) -> str:
        return f"http://{self.host}:{self.webrtc_port}/live/stream/whep"

    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class ClusterManager:
    """Master 노드의 클러스터 관리자"""

    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        """클러스터 관리자 시작"""
        logger.info("🎯 Cluster Manager started")
        self.heartbeat_task = asyncio.create_task(self._check_health())

    async def stop(self):
        """클러스터 관리자 종료"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

    def register_node(self, node: NodeInfo) -> bool:
        """Slave 노드 등록"""
        self.nodes[node.node_id] = node
        logger.info(f"✅ Node registered: {node.node_name} ({node.host}:{node.port})")
        logger.info(f"   RTMP: {node.rtmp_url}")
        logger.info(f"   HLS:  {node.hls_url}")
        return True

    def unregister_node(self, node_id: str) -> bool:
        """Slave 노드 등록 해제"""
        if node_id in self.nodes:
            node = self.nodes.pop(node_id)
            logger.info(f"❌ Node unregistered: {node.node_name}")
            return True
        return False

    def update_node_stats(self, node_id: str, stats: dict) -> bool:
        """노드 통계 업데이트"""
        if node_id not in self.nodes:
            logger.warning(f"⚠️ Unknown node: {node_id}")
            return False

        node = self.nodes[node_id]
        node.current_connections = stats.get("connections", 0)
        node.cpu_usage = stats.get("cpu", 0.0)
        node.memory_usage = stats.get("memory", 0.0)
        node.last_heartbeat = datetime.now()

        # 상태 판단
        if node.load_percentage > 90:
            node.status = "critical"
        elif node.load_percentage > 70:
            node.status = "warning"
        else:
            node.status = "healthy"

        return True

    def get_least_loaded_node(self) -> Optional[NodeInfo]:
        """가장 부하가 적은 노드 선택 (로드 밸런싱)"""
        healthy_nodes = [n for n in self.nodes.values() if n.is_healthy]

        if not healthy_nodes:
            logger.error("❌ No healthy nodes available!")
            return None

        # 부하가 가장 적은 노드 선택
        return min(healthy_nodes, key=lambda n: n.load_percentage)

    def get_node_for_stream(self, stream_id: str) -> Optional[NodeInfo]:
        """특정 스트림을 처리할 노드 선택"""
        # TODO: 스트림 ID 기반 sticky session 구현 가능
        # 지금은 단순히 least loaded 방식
        return self.get_least_loaded_node()

    def get_all_nodes(self) -> List[Dict]:
        """모든 노드 정보 반환"""
        return [asdict(node) for node in self.nodes.values()]

    def get_cluster_stats(self) -> Dict:
        """클러스터 전체 통계"""
        total_nodes = len(self.nodes)
        healthy_nodes = sum(1 for n in self.nodes.values() if n.is_healthy)
        total_connections = sum(n.current_connections for n in self.nodes.values())
        total_capacity = sum(n.max_connections for n in self.nodes.values())

        return {
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "offline_nodes": total_nodes - healthy_nodes,
            "total_connections": total_connections,
            "total_capacity": total_capacity,
            "utilization": (total_connections / total_capacity * 100)
            if total_capacity > 0
            else 0,
            "nodes": self.get_all_nodes(),
        }

    async def _check_health(self):
        """주기적으로 노드 헬스 체크"""
        while True:
            try:
                await asyncio.sleep(10)  # 10초마다

                for node_id, node in list(self.nodes.items()):
                    # 30초 이상 heartbeat 없으면 offline
                    age = datetime.now() - node.last_heartbeat
                    if age > timedelta(seconds=30):
                        logger.warning(
                            f"⚠️ Node {node.node_name} is offline (no heartbeat for {age.seconds}s)"
                        )
                        node.status = "offline"

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")


class SlaveClient:
    """Slave 노드에서 Master와 통신하는 클라이언트"""

    def __init__(self, master_url: str, node_info: NodeInfo):
        self.master_url = master_url.rstrip("/")
        self.node_info = node_info
        self.client = httpx.AsyncClient(timeout=5.0)
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        """Slave 클라이언트 시작"""
        # Master에 등록
        success = await self.register()
        if success:
            logger.info(f"✅ Registered to master: {self.master_url}")
            # Heartbeat 시작
            self.heartbeat_task = asyncio.create_task(self._send_heartbeat())
        else:
            logger.error(f"❌ Failed to register to master: {self.master_url}")

    async def stop(self):
        """Slave 클라이언트 종료"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        await self.unregister()
        await self.client.aclose()

    async def register(self) -> bool:
        """Master에 등록"""
        try:
            # datetime을 ISO string으로 변환
            node_dict = asdict(self.node_info)
            node_dict["last_heartbeat"] = node_dict["last_heartbeat"].isoformat()

            response = await self.client.post(
                f"{self.master_url}/cluster/register", json=node_dict
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Registration failed: {e}")
            return False

    async def unregister(self) -> bool:
        """Master에서 등록 해제"""
        try:
            response = await self.client.post(
                f"{self.master_url}/cluster/unregister",
                json={"node_id": self.node_info.node_id},
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Unregistration failed: {e}")
            return False

    async def send_stats(self, stats: dict) -> bool:
        """통계 정보 전송"""
        try:
            response = await self.client.post(
                f"{self.master_url}/cluster/stats",
                json={"node_id": self.node_info.node_id, "stats": stats},
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Stats send failed: {e}")
            return False

    async def _send_heartbeat(self):
        """주기적으로 heartbeat 전송"""
        while True:
            try:
                await asyncio.sleep(5)  # 5초마다

                # 현재 통계 수집
                stats = {
                    "connections": self.node_info.current_connections,
                    "cpu": self.node_info.cpu_usage,
                    "memory": self.node_info.memory_usage,
                }

                await self.send_stats(stats)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Heartbeat error: {e}")


# 전역 인스턴스
cluster_manager = ClusterManager()
slave_client: Optional[SlaveClient] = None


async def init_cluster_mode():
    """클러스터 모드 초기화"""
    mode = os.getenv("MODE", "standalone").lower()

    if mode == "master":
        # Master 모드
        logger.info("🎯 Starting in MASTER mode")
        await cluster_manager.start()

    elif mode == "slave":
        # Slave 모드
        master_url = os.getenv("MASTER_URL")
        if not master_url:
            logger.error("❌ MASTER_URL not set for slave mode!")
            return

        logger.info(f"🔗 Starting in SLAVE mode, connecting to {master_url}")

        # 노드 정보 생성 (Docker 컨테이너 이름을 node_id로 사용)
        container_name = os.getenv("HOSTNAME", str(uuid.uuid4())[:8])
        node_info = NodeInfo(
            node_id=os.getenv("NODE_ID", f"slave-{container_name}"),
            node_name=os.getenv("NODE_NAME", f"slave-{container_name}"),
            host=os.getenv("NODE_HOST", "localhost"),
            port=int(os.getenv("NODE_PORT", "8000")),
            rtmp_port=int(os.getenv("RTMP_PORT", "1935")),
            hls_port=int(os.getenv("HLS_PORT", "8888")),
            webrtc_port=int(os.getenv("WEBRTC_PORT", "8889")),
            max_connections=int(os.getenv("MAX_CONNECTIONS", "150")),
            current_connections=0,
            cpu_usage=0.0,
            memory_usage=0.0,
            status="healthy",
            last_heartbeat=datetime.now(),
        )

        global slave_client
        slave_client = SlaveClient(master_url, node_info)
        await slave_client.start()

    else:
        # Standalone 모드 (기존 방식)
        logger.info("🖥️ Starting in STANDALONE mode")


async def shutdown_cluster():
    """클러스터 종료"""
    mode = os.getenv("MODE", "standalone").lower()

    if mode == "master":
        await cluster_manager.stop()
    elif mode == "slave" and slave_client:
        await slave_client.stop()
