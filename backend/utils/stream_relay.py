"""
AIRClass Stream Relay Manager
Sub 노드: Main의 RTMP 스트림을 받아서 학생들에게 WebRTC로 배포
"""

import logging
from typing import Optional, Dict
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class StreamRelayManager:
    """Sub 노드의 스트림 중계 관리자"""

    def __init__(self, main_url: str, node_name: str):
        self.main_url = main_url
        self.node_name = node_name
        self.relay_process = None
        self.is_relaying = False
        self.stream_url = None

        logger.info(f"🔄 StreamRelayManager initialized for {node_name}")
        logger.info(f"   Main URL: {main_url}")

    def start_relay(self) -> bool:
        """
        Main 노드의 RTMP 스트림을 로컬 MediaMTX로 중계 시작
        
        Main의 RTMP → Sub의 MediaMTX로 수신 → 학생들에게 배포
        
        Returns:
            성공 여부
        """
        if self.is_relaying:
            logger.warning("⚠️ Relay already active")
            return False

        try:
            # Main 노드에서 RTMP 스트림 수신
            main_rtmp_url = f"rtmp://{self.main_url.replace('http://', '').split(':')[0]}/live/stream"
            
            # ffmpeg로 RTMP → 로컬 RTMP 중계
            # Sub 노드의 MediaMTX가 rtmp://localhost/live/relay에서 수신
            ffmpeg_cmd = [
                "ffmpeg",
                "-rtsp_transport", "tcp",
                "-i", main_rtmp_url,
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "flv",
                "rtmp://localhost/live/relay",
            ]

            self.relay_process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL
            )

            self.is_relaying = True
            self.stream_url = main_rtmp_url

            logger.info(f"✅ Stream relay started on {self.node_name}")
            logger.info(f"   Source: {main_rtmp_url}")
            logger.info(f"   Output: rtmp://localhost/live/relay")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start relay: {e}")
            return False

    def stop_relay(self) -> bool:
        """스트림 중계 중지"""
        if not self.is_relaying or self.relay_process is None:
            logger.warning("⚠️ No relay in progress")
            return False

        try:
            self.relay_process.terminate()
            self.relay_process.wait(timeout=10)
            self.is_relaying = False

            logger.info(f"✅ Stream relay stopped on {self.node_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to stop relay: {e}")
            if self.relay_process:
                self.relay_process.kill()
            self.is_relaying = False
            return False

    def health_check(self) -> Dict[str, any]:
        """스트림 중계 상태 확인"""
        return {
            "node_name": self.node_name,
            "is_relaying": self.is_relaying,
            "source_url": self.stream_url or "Not set",
            "status": "active" if self.is_relaying else "inactive",
        }


class WHEPServer:
    """
    WHEP (WebRTC-HTTP Egress Protocol) 서버
    Sub 노드에서 학생들에게 WebRTC 스트림 배포
    """

    def __init__(self, node_name: str, mediamtx_host: str = "localhost"):
        self.node_name = node_name
        self.mediamtx_host = mediamtx_host
        self.whep_url = f"http://{mediamtx_host}:8889/webrtc/relay"

        logger.info(f"📡 WHEP Server initialized for {node_name}")
        logger.info(f"   WHEP URL: {self.whep_url}")

    def get_whep_offer_url(self) -> str:
        """
        학생에게 제공할 WHEP 오퍼 URL
        클라이언트가 이 URL로 POST 요청을 보내면 WebRTC 스트림 수신
        """
        return self.whep_url

    def get_stream_info(self) -> Dict:
        """
        학생 클라이언트에게 제공할 스트림 정보
        """
        return {
            "type": "whep",
            "url": self.whep_url,
            "protocol": "webrtc",
            "transport": "http",
            "node": self.node_name,
            "description": "WebRTC stream from Sub node via WHEP",
        }


# 전역 인스턴스
stream_relay_manager = None
whep_server = None


def init_stream_relay():
    """StreamRelayManager 초기화 (Sub 노드만)"""
    global stream_relay_manager, whep_server

    from config import MODE
    import os

    if MODE == "sub":
        main_url = os.getenv("MAIN_URL", "http://main:8000")
        node_name = os.getenv("NODE_NAME", "sub-1")
        mediamtx_host = os.getenv("MEDIAMTX_HOST", "localhost")

        stream_relay_manager = StreamRelayManager(main_url, node_name)
        whep_server = WHEPServer(node_name, mediamtx_host)

        logger.info(f"✅ Stream relay system initialized for {node_name}")
    else:
        logger.info("⚠️ StreamRelayManager not initialized (not Sub node)")
        stream_relay_manager = None
        whep_server = None


def get_stream_relay_manager() -> Optional[StreamRelayManager]:
    """StreamRelayManager 인스턴스 반환"""
    return stream_relay_manager


def get_whep_server() -> Optional[WHEPServer]:
    """WHEP Server 인스턴스 반환"""
    return whep_server
