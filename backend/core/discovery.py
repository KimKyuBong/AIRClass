"""
AIRClass Node Discovery System
다중 발견 전략으로 학교 네트워크 환경에서도 안정적으로 작동

전략 우선순위:
1. mDNS/Zeroconf (빠르고 자동, 하지만 차단될 수 있음)
2. 로컬 네트워크 스캔 (mDNS 차단 시 대안)
3. 수동 IP 입력 (항상 작동)
4. QR 코드 (가장 사용자 친화적)
5. 중앙 레지스트리 (인터넷 경유, 다른 네트워크도 가능)
"""

import asyncio
import socket
import logging
import json
from typing import Optional, List, Dict
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredNode:
    """발견된 노드 정보"""

    ip: str
    port: int
    node_name: str
    role: str  # 'main' or 'sub'
    discovery_method: str  # 어떤 방법으로 발견했는지
    version: str = "2.0.0"

    @property
    def url(self) -> str:
        return f"http://{self.ip}:{self.port}"


def _discovery_ports() -> List[int]:
    """자동 검색에 사용할 API 포트 목록 (동적 포트 범위 대응: 8000, 8100, 8200, ...)"""
    import os
    raw = os.getenv("DISCOVERY_PORTS", "8000,8100,8200,8300")
    try:
        return [int(p.strip()) for p in raw.split(",") if p.strip()]
    except ValueError:
        return [8000, 8100, 8200, 8300]


class MultiDiscoveryManager:
    """다중 발견 전략 관리자"""

    def __init__(self):
        self.discovered_nodes: List[DiscoveredNode] = []
        self.client = httpx.AsyncClient(timeout=3.0)

    async def find_main_node(self, timeout: int = 10) -> Optional[DiscoveredNode]:
        """
        메인 노드를 찾습니다 (여러 전략 시도)

        Args:
            timeout: 전체 검색 타임아웃 (초)

        Returns:
            발견된 메인 노드 또는 None
        """
        logger.info("🔍 메인 노드 검색 시작...")

        # 전략 1: mDNS (3초 타임아웃)
        logger.info("📡 전략 1: mDNS 자동 발견 시도...")
        node = await self._try_mdns_discovery(timeout=3)
        if node:
            logger.info(f"✅ mDNS로 메인 노드 발견: {node.url}")
            return node
        logger.warning("⚠️ mDNS 실패 (차단되었거나 메인 노드 없음)")

        # 전략 2: 로컬 네트워크 스캔 (5초 타임아웃)
        logger.info("🔎 전략 2: 로컬 네트워크 스캔 시도...")
        node = await self._try_network_scan(timeout=5)
        if node:
            logger.info(f"✅ 네트워크 스캔으로 메인 노드 발견: {node.url}")
            return node
        logger.warning("⚠️ 네트워크 스캔 실패")

        # 전략 3: 알려진 IP들 확인 (일반적인 라우터 게이트웨이)
        logger.info("🎯 전략 3: 일반적인 IP 주소 확인...")
        node = await self._try_common_ips()
        if node:
            logger.info(f"✅ 일반 IP로 메인 노드 발견: {node.url}")
            return node

        logger.error("❌ 모든 자동 발견 전략 실패 - 수동 입력 필요")
        return None

    async def _try_mdns_discovery(self, timeout: int = 3) -> Optional[DiscoveredNode]:
        """mDNS를 사용한 자동 발견"""
        try:
            from zeroconf import ServiceBrowser, Zeroconf, ServiceStateChange

            found_node = None

            def on_service_state_change(zeroconf, service_type, name, state_change):
                nonlocal found_node
                if state_change is ServiceStateChange.Added:
                    info = zeroconf.get_service_info(service_type, name)
                    if info and info.properties.get(b"role") == b"main":
                        ip = socket.inet_ntoa(info.addresses[0])
                        port = info.port
                        found_node = DiscoveredNode(
                            ip=ip,
                            port=port,
                            node_name=info.properties.get(b"name", b"main").decode(),
                            role="main",
                            discovery_method="mDNS",
                            version=info.properties.get(b"version", b"2.0.0").decode(),
                        )

            zeroconf = Zeroconf()
            browser = ServiceBrowser(
                zeroconf, "_airclass._tcp.local.", handlers=[on_service_state_change]
            )

            # 타임아웃까지 대기
            await asyncio.sleep(timeout)

            zeroconf.close()
            return found_node

        except ImportError:
            logger.warning("⚠️ zeroconf 라이브러리 없음 - pip install zeroconf")
            return None
        except Exception as e:
            logger.error(f"❌ mDNS 오류: {e}")
            return None

    async def _try_network_scan(self, timeout: int = 5) -> Optional[DiscoveredNode]:
        """
        로컬 네트워크 스캔 (ping sweep)
        현재 IP 대역에서 AirClass 메인 노드 찾기
        """
        try:
            # 현재 IP 주소 가져오기
            local_ip = self._get_local_ip()
            if not local_ip or local_ip == "127.0.0.1":
                return None

            # IP 대역 추출 (예: 192.168.1.x)
            ip_parts = local_ip.split(".")
            network_prefix = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"

            ports = _discovery_ports()
            logger.info(f"🔍 네트워크 대역 스캔: {network_prefix}.0/24 (포트: {ports})")

            # 동시에 여러 IP × 여러 포트 스캔 (동적 포트 범위 대응)
            tasks = []
            for i in range(1, 255):
                ip = f"{network_prefix}.{i}"
                if ip == local_ip:
                    continue
                for port in ports:
                    tasks.append(self._check_airclass_node(ip, port))

            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True), timeout=timeout
                )
                for result in results:
                    if isinstance(result, DiscoveredNode) and result.role == "main":
                        return result
            except asyncio.TimeoutError:
                logger.warning("⚠️ 네트워크 스캔 타임아웃")

            return None

        except Exception as e:
            logger.error(f"❌ 네트워크 스캔 오류: {e}")
            return None

    async def _check_airclass_node(
        self, ip: str, port: int = 8000
    ) -> Optional[DiscoveredNode]:
        """특정 IP가 AirClass 노드인지 확인"""
        try:
            response = await self.client.get(
                f"http://{ip}:{port}/health",
                timeout=1.0,  # 빠른 스캔을 위해 짧은 타임아웃
            )

            if response.status_code == 200:
                data = response.json()

                # AirClass 노드인지 확인
                if data.get("status") == "healthy":
                    return DiscoveredNode(
                        ip=ip,
                        port=port,
                        node_name=data.get("mode", "unknown"),
                        role=data.get("mode", "unknown"),
                        discovery_method="network_scan",
                    )

        except Exception:
            # 연결 실패는 정상 (해당 IP에 노드 없음)
            pass

        return None

    async def _try_common_ips(self) -> Optional[DiscoveredNode]:
        """일반적인 IP 주소에서 메인 노드 찾기"""
        local_ip = self._get_local_ip()
        if not local_ip or local_ip == "127.0.0.1":
            return None

        # 게이트웨이 IP 추출
        ip_parts = local_ip.split(".")
        common_ips = [
            f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1",  # 라우터 (일반적)
            f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.254",  # 라우터 (대체)
            f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.100",  # 일반적인 고정 IP
            "localhost",  # 로컬 테스트
        ]

        ports = _discovery_ports()
        for ip in common_ips:
            if ip == local_ip:
                continue
            addr = ip if ip != "localhost" else "127.0.0.1"
            for port in ports:
                node = await self._check_airclass_node(addr, port)
                if node:
                    return node

        return None

    def _get_local_ip(self) -> str:
        """현재 컴퓨터의 로컬 IP 주소 가져오기"""
        try:
            # 외부 연결 시도로 로컬 IP 확인 (실제로 연결하지 않음)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    async def advertise_main_node(self, port: int = 8000, node_name: str = "main"):
        """
        메인 노드를 mDNS로 광고
        (mDNS가 차단되어도 다른 발견 방법이 작동하므로 선택사항)
        """
        try:
            from zeroconf import ServiceInfo, Zeroconf

            local_ip = self._get_local_ip()

            info = ServiceInfo(
                "_airclass._tcp.local.",
                f"{node_name}._airclass._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=port,
                properties={
                    "role": "main",
                    "name": node_name,
                    "version": "2.0.0",
                    "ip": local_ip,
                },
                server=f"{node_name}.local.",
            )

            zeroconf = Zeroconf()
            zeroconf.register_service(info)

            logger.info(f"📡 mDNS 광고 시작: {node_name} at {local_ip}:{port}")
            logger.info("   (mDNS가 차단되어도 다른 발견 방법이 작동합니다)")

            return zeroconf  # 종료 시 close() 호출 필요

        except ImportError:
            logger.info("ℹ️  zeroconf 미설치 - mDNS 비활성화 (다른 발견 방법 사용)")
            return None
        except Exception as e:
            logger.warning(f"⚠️ mDNS 광고 실패: {e} (다른 발견 방법 사용)")
            return None

    async def verify_manual_ip(
        self, ip: str, port: int = 8000
    ) -> Optional[DiscoveredNode]:
        """수동으로 입력한 IP 주소 검증"""
        logger.info(f"🔍 수동 IP 검증 중: {ip}:{port}")
        node = await self._check_airclass_node(ip, port)

        if node:
            logger.info(f"✅ 메인 노드 확인됨: {ip}:{port}")
            node.discovery_method = "manual_ip"
            return node
        else:
            logger.error(f"❌ {ip}:{port}에서 AirClass 메인 노드를 찾을 수 없습니다")
            return None

    async def close(self):
        """리소스 정리"""
        await self.client.aclose()


# 전역 인스턴스
discovery_manager = MultiDiscoveryManager()


async def find_main_node_with_fallback(timeout: int = 10) -> Optional[DiscoveredNode]:
    """
    메인 노드를 찾습니다 (여러 전략 Fallback)

    학교 네트워크 환경을 고려한 강력한 발견 시스템:
    1. mDNS 시도 (3초)
    2. 로컬 네트워크 스캔 (5초)
    3. 일반적인 IP 확인
    4. 실패 시 수동 입력 요청

    Returns:
        발견된 메인 노드 또는 None (수동 입력 필요)
    """
    return await discovery_manager.find_main_node(timeout=timeout)
