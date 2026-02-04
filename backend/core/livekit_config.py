"""
LiveKit 설정 동적 생성 모듈

FastAPI가 노드 역할(main/sub)에 따라 livekit.yaml을 동적으로 생성
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LiveKitConfigGenerator:
    """LiveKit 설정 파일 동적 생성기"""

    def __init__(
        self,
        node_id: str,
        mode: str,
        redis_url: str,
        livekit_port: int = 7880,
        rtc_port_range_start: int = 50000,
        rtc_port_range_end: int = 50020,
        api_key: str = "AIRClass2025DevKey123456789ABC",
        api_secret: str = "AIRclass2025DevSecretXYZ987654321",
    ):
        """
        Args:
            node_id: 노드 ID (예: "main", "node-1", "node-2")
            mode: 클러스터 모드 ("main", "sub", "standalone")
            redis_url: Redis 연결 URL
            livekit_port: LiveKit HTTP 포트
            rtc_port_range_start: WebRTC 포트 범위 시작
            rtc_port_range_end: WebRTC 포트 범위 끝
            api_key: LiveKit API 키
            api_secret: LiveKit API 시크릿
        """
        self.node_id = node_id
        self.mode = mode
        self.redis_url = redis_url
        self.livekit_port = livekit_port
        self.rtc_port_range_start = rtc_port_range_start
        self.rtc_port_range_end = rtc_port_range_end
        self.api_key = api_key
        self.api_secret = api_secret

    def _calculate_ports(self) -> Dict[str, int]:
        """
        노드 ID 기반으로 포트 자동 계산

        main: 7880, 50000-50020
        node-1: 7890, 51000-51020
        node-2: 7900, 52000-52020
        node-3: 7910, 53000-53020
        """
        if self.node_id == "main":
            return {
                "http_port": 7880,
                "rtc_start": 50000,
                "rtc_end": 50020,
                "tcp_port": 7881,
                "udp_port": 7882,
            }

        # sub 노드는 숫자 추출 (node-1 → 1)
        try:
            node_num = int(self.node_id.split("-")[-1])
            base_offset = node_num * 10  # 노드당 10 포트 간격
            rtc_offset = node_num * 1000  # RTC 포트는 1000 간격

            return {
                "http_port": 7880 + base_offset,
                "rtc_start": 50000 + rtc_offset,
                "rtc_end": 50020 + rtc_offset,
                "tcp_port": 7881 + base_offset,
                "udp_port": 7882 + base_offset,
            }
        except (ValueError, IndexError):
            # 파싱 실패 시 기본값 사용
            logger.warning(f"노드 ID '{self.node_id}' 파싱 실패, 기본 포트 사용")
            return {
                "http_port": self.livekit_port,
                "rtc_start": self.rtc_port_range_start,
                "rtc_end": self.rtc_port_range_end,
                "tcp_port": 7881,
                "udp_port": 7882,
            }

    def generate_config(self) -> Dict[str, Any]:
        """
        LiveKit YAML 설정 생성

        Returns:
            dict: LiveKit 설정 딕셔너리
        """
        ports = self._calculate_ports()

        # Redis URL 처리 (redis:// 프로토콜 제거)
        redis_addr = self.redis_url.replace("redis://", "")

        config = {
            "port": ports["http_port"],
            "bind_addresses": ["0.0.0.0"],  # 모든 인터페이스에서 수신
            "redis": {
                "address": redis_addr,  # redis:6379 형식
                # use_cluster 제거 (LiveKit 1.9.x에서 지원하지 않음)
                # db는 기본값 사용
            },
            "keys": {
                self.api_key: self.api_secret,
            },
            "logging": {
                "level": "info",
                "sample": True,
            },
            "room": {
                "auto_create": True,
                "empty_timeout": 300,  # 5분
                "max_participants": 200,
                # enable_pit 제거 (LiveKit 1.9.x에서 기본 활성화)
            },
            "rtc": {
                "port_range_start": ports["rtc_start"],
                "port_range_end": ports["rtc_end"],
                "tcp_port": ports["tcp_port"],
                "udp_port": ports["udp_port"],
                "use_external_ip": True,
                "node_ip": "0.0.0.0",  # 컨테이너 환경에서 자동 감지
            },
            # TURN 서버 비활성화 (도메인 설정 없이는 실패)
            # 프로덕션에서는 TURN 서버 설정 권장
        }

        return config

    def save_to_file(self, output_path: Optional[Path] = None) -> Path:
        """
        설정을 YAML 파일로 저장

        Args:
            output_path: 출력 파일 경로 (None이면 자동 생성)

        Returns:
            Path: 저장된 파일 경로
        """
        if output_path is None:
            # backend/configs/ 디렉토리에 저장
            config_dir = Path(__file__).parent.parent / "configs"
            config_dir.mkdir(exist_ok=True)
            output_path = config_dir / f"livekit-{self.node_id}.yaml"

        config = self.generate_config()

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"LiveKit 설정 파일 생성: {output_path}")
        logger.debug(f"설정 내용: {config}")

        return output_path

    def get_websocket_url(self) -> str:
        """
        LiveKit WebSocket URL 반환

        Returns:
            str: ws:// 또는 wss:// URL
        """
        ports = self._calculate_ports()
        # 프로덕션에서는 wss:// 사용 권장
        return f"ws://localhost:{ports['http_port']}"

    def get_http_url(self) -> str:
        """
        LiveKit HTTP API URL 반환

        Returns:
            str: http:// 또는 https:// URL
        """
        ports = self._calculate_ports()
        return f"http://localhost:{ports['http_port']}"


def create_livekit_config(
    node_id: str, mode: str, redis_url: str = "redis://localhost:6379", **kwargs
) -> Path:
    """
    LiveKit 설정 파일 생성 헬퍼 함수

    Args:
        node_id: 노드 ID
        mode: 클러스터 모드
        redis_url: Redis URL
        **kwargs: 추가 설정

    Returns:
        Path: 생성된 설정 파일 경로
    """
    generator = LiveKitConfigGenerator(node_id=node_id, mode=mode, redis_url=redis_url, **kwargs)
    return generator.save_to_file()


if __name__ == "__main__":
    # 테스트: Main 노드 설정 생성
    main_config = create_livekit_config(node_id="main", mode="main", redis_url="redis://redis:6379")
    print(f"Main node config: {main_config}")

    # 테스트: Sub 노드 설정 생성
    sub_config = create_livekit_config(node_id="node-1", mode="sub", redis_url="redis://redis:6379")
    print(f"Sub node config: {sub_config}")
