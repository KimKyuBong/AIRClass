"""
Network Utilities
네트워크 관련 유틸리티 함수들
"""

import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """
    Get local IP address in the network

    Returns:
        로컬 IP 주소 문자열 (실패 시 "localhost")
    """
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to Google DNS (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        logger.info(f"Local IP detected: {local_ip}")
        return local_ip
    except Exception as e:
        logger.warning(f"Failed to detect local IP: {e}, using 'localhost'")
        return "localhost"


def get_public_ip() -> Optional[str]:
    """
    Get public IP address using external service

    Returns:
        공인 IP 주소 문자열 (실패 시 None)
    """
    try:
        import requests

        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        if response.status_code == 200:
            public_ip = response.json().get("ip")
            logger.info(f"Public IP detected: {public_ip}")
            return public_ip
    except Exception as e:
        logger.warning(f"Failed to detect public IP: {e}")
    return None


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """
    Check if a port is available for binding

    Args:
        port: 확인할 포트 번호
        host: 바인딩할 호스트 (기본값: "0.0.0.0")

    Returns:
        포트 사용 가능 여부
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except OSError:
        logger.warning(f"Port {port} is already in use on {host}")
        return False


def get_hostname() -> str:
    """
    Get machine hostname

    Returns:
        호스트 이름
    """
    try:
        hostname = socket.gethostname()
        logger.debug(f"Hostname: {hostname}")
        return hostname
    except Exception as e:
        logger.warning(f"Failed to get hostname: {e}")
        return "unknown"


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolve hostname to IP address

    Args:
        hostname: 해석할 호스트 이름

    Returns:
        IP 주소 문자열 (실패 시 None)
    """
    try:
        ip_address = socket.gethostbyname(hostname)
        logger.debug(f"Resolved {hostname} to {ip_address}")
        return ip_address
    except socket.gaierror as e:
        logger.warning(f"Failed to resolve hostname {hostname}: {e}")
        return None
