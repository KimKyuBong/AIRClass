"""
AIRClass Cluster Management
Main-Sub Node 아키텍처 구현

Main Node: 요청을 받아 최적의 Sub Node로 라우팅
Sub Node: 실제 스트리밍 처리 및 Main Node에 상태 보고
"""

import asyncio
import httpx
import logging
import uuid
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from fastapi import HTTPException
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_cluster_auth_token(secret: str, timestamp: str) -> str:
    """
    클러스터 인증 토큰 생성

    Args:
        secret: CLUSTER_SECRET 환경 변수 값
        timestamp: ISO 형식의 타임스탬프

    Returns:
        HMAC-SHA256 해시 (hex 형식)
    """
    message = f"{timestamp}:{secret}"
    return hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_cluster_auth_token(secret: str, timestamp: str, provided_token: str) -> bool:
    """
    클러스터 인증 토큰 검증

    Args:
        secret: CLUSTER_SECRET 환경 변수 값
        timestamp: ISO 형식의 타임스탬프
        provided_token: 클라이언트가 제공한 토큰

    Returns:
        검증 성공 여부
    """
    expected_token = generate_cluster_auth_token(secret, timestamp)
    return hmac.compare_digest(expected_token, provided_token)


@dataclass
class NodeInfo:
    """노드 정보"""

    node_id: str
    node_name: str
    host: str
    port: int
    rtmp_port: int
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
    def webrtc_url(self) -> str:
        return f"http://{self.host}:{self.webrtc_port}/live/stream/whep"

    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class ClusterManager:
    """Main 노드의 클러스터 관리자"""

    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.stream_assignments: Dict[str, str] = {}  # stream_id -> node_id mapping
        self.main_node_id: Optional[str] = None  # 메인 노드 자신의 ID

    async def start(self):
        """클러스터 관리자 시작"""
        logger.info("🎯 Cluster Manager started")
        self.heartbeat_task = asyncio.create_task(self._check_health())

    async def stop(self):
        """클러스터 관리자 종료"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

    def register_node(self, node: NodeInfo) -> bool:
        """Sub 노드 등록"""
        self.nodes[node.node_id] = node
        logger.info(f"✅ Node registered: {node.node_name} ({node.host}:{node.port})")
        logger.info(f"   RTMP:   {node.rtmp_url}")
        logger.info(f"   WebRTC: {node.webrtc_url}")
        return True

    def unregister_node(self, node_id: str) -> bool:
        """Sub 노드 등록 해제"""
        if node_id in self.nodes:
            node = self.nodes.pop(node_id)
            logger.info(f"❌ Node unregistered: {node.node_name}")

            # 해당 노드에 할당된 스트림 재할당
            streams_to_reassign = [
                sid for sid, nid in self.stream_assignments.items() if nid == node_id
            ]
            for stream_id in streams_to_reassign:
                del self.stream_assignments[stream_id]
                logger.info(f"🔄 Stream {stream_id} will be reassigned on next request")

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
        """가장 부하가 적은 노드 선택 (로드 밸런싱 - Fallback용)"""
        healthy_nodes = [n for n in self.nodes.values() if n.is_healthy]

        if not healthy_nodes:
            logger.error("❌ No healthy nodes available!")
            return None

        # 부하가 가장 적은 노드 선택
        return min(healthy_nodes, key=lambda n: n.load_percentage)

    def get_node_rendezvous(self, stream_id: str) -> Optional[NodeInfo]:
        """
        Rendezvous Hashing (HRW - Highest Random Weight)
        Stream ID 기반으로 노드를 일관성 있게 선택

        장점:
        - Sticky session 자동 지원 (같은 stream_id는 항상 같은 노드)
        - 노드 추가/제거 시 최소한의 재할당 (K/N 비율만큼만)
        - Virtual Node 불필요
        - 균등한 분산
        """
        healthy_nodes = [n for n in self.nodes.values() if n.is_healthy]

        if not healthy_nodes:
            logger.error("❌ No healthy nodes available!")
            return None

        # 각 노드에 대해 점수 계산
        max_score = float("-inf")  # 음수 hash 값 처리를 위해 -inf로 초기화
        selected_node = None

        for node in healthy_nodes:
            # stream_id와 node_id를 조합하여 해시 생성
            combined = f"{stream_id}:{node.node_id}"
            score = hash(combined)

            if score > max_score:
                max_score = score
                selected_node = node

        # healthy_nodes가 있으면 selected_node는 반드시 설정됨
        if selected_node is None:
            logger.error(f"❌ Failed to select node for stream '{stream_id}'")
            return healthy_nodes[0]  # Fallback to first healthy node

        logger.info(
            f"🎯 Rendezvous Hashing: stream '{stream_id}' → node '{selected_node.node_name}'"
        )
        return selected_node

    def get_node_for_stream(
        self, stream_id: str, use_sticky: bool = True
    ) -> Optional[NodeInfo]:
        """
        특정 스트림을 처리할 노드 선택

        전략:
        1. Sticky Session: 이미 할당된 노드가 healthy면 재사용
        2. Rendezvous Hashing: stream_id 기반 일관성 해싱
        3. Health-aware Fallback: 선택된 노드가 과부하면 least-loaded로 대체
        """
        # 1. Sticky Session 체크
        if use_sticky and stream_id in self.stream_assignments:
            assigned_node_id = self.stream_assignments[stream_id]
            if assigned_node_id in self.nodes:
                node = self.nodes[assigned_node_id]
                if node.is_healthy and node.load_percentage < 90:
                    logger.info(
                        f"📌 Sticky session: stream '{stream_id}' → existing node '{node.node_name}'"
                    )
                    return node
                else:
                    logger.warning(
                        f"⚠️ Assigned node '{node.node_name}' is unhealthy or overloaded, reassigning..."
                    )
                    del self.stream_assignments[stream_id]

        # 2. Rendezvous Hashing으로 노드 선택
        node = self.get_node_rendezvous(stream_id)

        if not node:
            return None

        # 3. Health-aware Fallback: 과부하 체크
        if node.load_percentage > 90:
            logger.warning(
                f"⚠️ Selected node '{node.node_name}' is overloaded ({node.load_percentage:.1f}%), using fallback..."
            )
            node = self.get_least_loaded_node()

        # 스트림 할당 기록
        if node:
            self.stream_assignments[stream_id] = node.node_id
            logger.info(
                f"✅ Stream '{stream_id}' assigned to '{node.node_name}' (load: {node.load_percentage:.1f}%)"
            )

        return node

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
        """주기적으로 노드 헬스 체크 및 메인 노드 상태 업데이트"""
        while True:
            try:
                await asyncio.sleep(10)  # 10초마다

                # 메인 노드 자신의 연결 수 업데이트
                if self.main_node_id and self.main_node_id in self.nodes:
                    try:
                        main_node = self.nodes[self.main_node_id]
                        async with httpx.AsyncClient(timeout=2.0) as client:
                            # MediaMTX API로 현재 연결 수 조회
                            response = await client.get(
                                f"http://{main_node.host}:{main_node.webrtc_port}/v3/paths/list"
                            )
                            if response.status_code == 200:
                                data = response.json()
                                # readers 수를 합산
                                total_readers = 0
                                if "items" in data:
                                    for item in data["items"]:
                                        total_readers += item.get("readers", 0)

                                main_node.current_connections = total_readers
                                main_node.last_heartbeat = datetime.now()
                                logger.info(
                                    f"📊 Main node connections: {total_readers}"
                                )
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to update main node stats: {e}")

                # Sub 노드들 헬스 체크
                for node_id, node in list(self.nodes.items()):
                    # 메인 노드는 스킵 (위에서 이미 처리)
                    if node_id == self.main_node_id:
                        continue

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


class SubNodeClient:
    """Sub 노드에서 Main Node와 통신하는 클라이언트"""

    def __init__(self, main_node_url: str, node_info: NodeInfo):
        self.main_node_url = main_node_url.rstrip("/")
        self.node_info = node_info
        self.client = httpx.AsyncClient(timeout=5.0)
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def start(self):
        """Sub Node 클라이언트 시작"""
        # Main Node에 등록
        success = await self.register()
        if success:
            logger.info(f"✅ Registered to main node: {self.main_node_url}")
            # Heartbeat 시작
            self.heartbeat_task = asyncio.create_task(self._send_heartbeat())
        else:
            logger.error(f"❌ Failed to register to main node: {self.main_node_url}")

    async def stop(self):
        """Sub Node 클라이언트 종료"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        await self.unregister()
        await self.client.aclose()

    async def register(self) -> bool:
        """Main Node에 등록 (HMAC 인증 포함)"""
        try:
            # CLUSTER_SECRET 가져오기
            cluster_secret = os.getenv("CLUSTER_SECRET", "")
            if not cluster_secret:
                logger.error("❌ CLUSTER_SECRET not set! Cannot register.")
                return False

            # datetime을 ISO string으로 변환
            node_dict = asdict(self.node_info)
            timestamp = datetime.now().isoformat()
            node_dict["last_heartbeat"] = timestamp

            # HMAC 인증 토큰 생성
            auth_token = generate_cluster_auth_token(cluster_secret, timestamp)
            node_dict["auth_token"] = auth_token
            node_dict["timestamp"] = timestamp

            response = await self.client.post(
                f"{self.main_node_url}/cluster/register", json=node_dict
            )

            if response.status_code == 200:
                return True
            elif response.status_code == 403:
                logger.error("❌ Authentication failed: CLUSTER_SECRET mismatch!")
                logger.error(
                    "   Main 노드와 Sub 노드의 .env 파일에 같은 CLUSTER_SECRET을 설정하세요"
                )
                return False
            else:
                return False

        except Exception as e:
            logger.error(f"❌ Registration failed: {e}")
            return False

    async def unregister(self) -> bool:
        """Main Node에서 등록 해제"""
        try:
            response = await self.client.post(
                f"{self.main_node_url}/cluster/unregister",
                json={"node_id": self.node_info.node_id},
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Unregistration failed: {e}")
            return False

    async def send_stats(self, stats: dict) -> bool:
        """통계 정보 전송 (HMAC 인증 포함)"""
        try:
            # CLUSTER_SECRET 가져오기
            cluster_secret = os.getenv("CLUSTER_SECRET", "")
            if not cluster_secret:
                logger.error("❌ CLUSTER_SECRET not set!")
                return False

            # HMAC 인증 토큰 생성
            timestamp = datetime.now().isoformat()
            auth_token = generate_cluster_auth_token(cluster_secret, timestamp)

            response = await self.client.post(
                f"{self.main_node_url}/cluster/stats",
                json={
                    "node_id": self.node_info.node_id,
                    "stats": stats,
                    "auth_token": auth_token,
                    "timestamp": timestamp,
                },
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Stats send failed: {e}")
            return False

    async def _send_heartbeat(self):
        """주기적으로 heartbeat 전송 (재연결 로직 포함)"""
        consecutive_failures = 0
        registered = True

        while True:
            try:
                await asyncio.sleep(5)  # 5초마다

                # 현재 통계 수집
                stats = {
                    "connections": self.node_info.current_connections,
                    "cpu": self.node_info.cpu_usage,
                    "memory": self.node_info.memory_usage,
                }

                success = await self.send_stats(stats)

                if success:
                    consecutive_failures = 0
                    if not registered:
                        logger.info(
                            f"✅ Reconnected to main node: {self.main_node_url}"
                        )
                        registered = True
                else:
                    consecutive_failures += 1

                    # 3번 연속 실패하면 재등록 시도
                    if consecutive_failures >= 3:
                        logger.warning(
                            f"⚠️ Lost connection to main node (failures: {consecutive_failures}), attempting to re-register..."
                        )
                        registered = False

                        # 재등록 시도
                        if await self.register():
                            logger.info(f"✅ Successfully re-registered to main node")
                            consecutive_failures = 0
                            registered = True
                        else:
                            logger.error(
                                f"❌ Re-registration failed, will retry in 5 seconds"
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Heartbeat error: {e}")
                consecutive_failures += 1


# 전역 인스턴스
cluster_manager = ClusterManager()
sub_node_client: Optional[SubNodeClient] = None
mdns_service = None  # mDNS 광고 서비스


async def init_cluster_mode():
    """클러스터 모드 초기화"""
    mode = os.getenv("MODE", "standalone").lower()

    if mode == "main":
        # Main Node 모드
        logger.info("🎯 Starting in MAIN NODE mode")
        await cluster_manager.start()

        # 메인 노드 자신도 로드밸런싱 풀에 추가
        main_node_id = os.getenv("NODE_ID", "main")
        main_node_info = NodeInfo(
            node_id=main_node_id,
            node_name=os.getenv("NODE_NAME", "main"),
            host=os.getenv("NODE_HOST", "10.100.0.146"),
            port=int(os.getenv("NODE_PORT", "8000")),
            rtmp_port=int(os.getenv("RTMP_PORT", "1935")),
            webrtc_port=int(os.getenv("WEBRTC_PORT", "8889")),
            max_connections=int(os.getenv("MAX_CONNECTIONS", "150")),
            current_connections=0,
            cpu_usage=0.0,
            memory_usage=0.0,
            status="healthy",
            last_heartbeat=datetime.now(),
        )
        cluster_manager.register_node(main_node_info)
        cluster_manager.main_node_id = main_node_id  # 메인 노드 ID 저장
        logger.info("✅ Main node added to load balancing pool")

        # mDNS 광고 시작 (선택사항 - 실패해도 계속 진행)
        try:
            from discovery import discovery_manager

            global mdns_service
            mdns_service = await discovery_manager.advertise_main_node(
                port=int(os.getenv("NODE_PORT", "8000")),
                node_name=os.getenv("NODE_NAME", "main"),
            )
            if mdns_service:
                logger.info("✅ mDNS 광고 활성화")
            else:
                logger.info("ℹ️  mDNS 비활성화 (다른 발견 방법 사용 가능)")
        except Exception as e:
            logger.warning(f"⚠️ mDNS 광고 실패: {e} (다른 발견 방법으로 계속)")

    elif mode == "sub":
        # Sub Node 모드
        main_node_url = os.getenv("MAIN_NODE_URL")

        # MAIN_NODE_URL이 없으면 자동 발견 시도
        if not main_node_url:
            logger.info("🔍 MAIN_NODE_URL 미설정 - 자동 발견 시도...")

            try:
                from discovery import find_main_node_with_fallback

                discovered_node = await find_main_node_with_fallback(timeout=10)

                if discovered_node:
                    main_node_url = discovered_node.url
                    logger.info(f"✅ 메인 노드 자동 발견 성공: {main_node_url}")
                    logger.info(f"   발견 방법: {discovered_node.discovery_method}")
                else:
                    logger.error("❌ 메인 노드 자동 발견 실패!")
                    logger.error("   MAIN_NODE_URL 환경 변수를 설정하거나")
                    logger.error("   install.sh 스크립트를 사용하세요")
                    return

            except Exception as e:
                logger.error(f"❌ 자동 발견 오류: {e}")
                logger.error("   MAIN_NODE_URL 환경 변수를 수동으로 설정하세요")
                return

        logger.info(f"🔗 Starting in SUB NODE mode, connecting to {main_node_url}")

        # 노드 정보 생성 (Docker 컨테이너 이름을 node_id로 사용)
        container_name = os.getenv("HOSTNAME", str(uuid.uuid4())[:8])
        node_info = NodeInfo(
            node_id=os.getenv("NODE_ID", f"sub-{container_name}"),
            node_name=os.getenv("NODE_NAME", f"sub-{container_name}"),
            host=os.getenv("NODE_HOST", "localhost"),
            port=int(os.getenv("NODE_PORT", "8000")),
            rtmp_port=int(os.getenv("RTMP_PORT", "1935")),
            webrtc_port=int(os.getenv("WEBRTC_PORT", "8889")),
            max_connections=int(os.getenv("MAX_CONNECTIONS", "150")),
            current_connections=0,
            cpu_usage=0.0,
            memory_usage=0.0,
            status="healthy",
            last_heartbeat=datetime.now(),
        )

        global sub_node_client
        sub_node_client = SubNodeClient(main_node_url, node_info)
        await sub_node_client.start()

    else:
        # Standalone 모드 (기존 방식)
        logger.info("🖥️ Starting in STANDALONE mode")


async def shutdown_cluster():
    """클러스터 종료"""
    mode = os.getenv("MODE", "standalone").lower()

    if mode == "main":
        await cluster_manager.stop()
        # mDNS 서비스 종료
        if mdns_service:
            try:
                mdns_service.close()
                logger.info("✅ mDNS 광고 종료")
            except Exception as e:
                logger.warning(f"⚠️ mDNS 종료 오류: {e}")
    elif mode == "sub" and sub_node_client:
        await sub_node_client.stop()
