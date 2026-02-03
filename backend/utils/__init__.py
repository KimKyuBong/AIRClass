"""
Utilities Package
백엔드 유틸리티 모듈들
"""

from .mediamtx import (
    start_mediamtx,
    stop_mediamtx,
    is_mediamtx_running,
    get_mediamtx_pid,
)

from .jwt_auth import (
    generate_stream_token,
    verify_token,
    revoke_token,
    get_active_token_count,
    clear_expired_tokens,
    is_token_active,
    JWT_EXPIRATION_MINUTES,  # 상수도 export
)

from .qr_code import (
    print_qr_code,
    generate_qr_code_image,
    generate_qr_code_svg,
)

from .network import (
    get_local_ip,
    get_public_ip,
    is_port_available,
    get_hostname,
    resolve_hostname,
)

from .websocket import (
    ConnectionManager,
    get_connection_manager,
)

__all__ = [
    # MediaMTX
    "start_mediamtx",
    "stop_mediamtx",
    "is_mediamtx_running",
    "get_mediamtx_pid",
    # JWT Auth
    "generate_stream_token",
    "verify_token",
    "revoke_token",
    "get_active_token_count",
    "clear_expired_tokens",
    "is_token_active",
    "JWT_EXPIRATION_MINUTES",
    # QR Code
    "print_qr_code",
    "generate_qr_code_image",
    "generate_qr_code_svg",
    # Network
    "get_local_ip",
    "get_public_ip",
    "is_port_available",
    "get_hostname",
    "resolve_hostname",
    # WebSocket
    "ConnectionManager",
    "get_connection_manager",
]
