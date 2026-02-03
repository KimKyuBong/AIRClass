"""
AIRClass Configuration
중앙화된 설정 관리
"""

import os
import secrets
from typing import Literal

# ============================================
# Mode Configuration
# ============================================
MODE: Literal["main", "sub", "standalone"] = os.getenv("MODE", "standalone")  # type: ignore
NODE_NAME = os.getenv("NODE_NAME", "node")
NODE_HOST = os.getenv("NODE_HOST", "localhost")
NODE_PORT = int(os.getenv("NODE_PORT", "8000"))

# ============================================
# JWT Configuration
# ============================================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

# ============================================
# MediaMTX Configuration
# ============================================
RTMP_PORT = int(os.getenv("RTMP_PORT", "1935"))
WEBRTC_PORT = int(os.getenv("WEBRTC_PORT", "8889"))
MEDIAMTX_API_PORT = 9997
MEDIAMTX_API_URL = f"http://127.0.0.1:{MEDIAMTX_API_PORT}"

# ============================================
# Cluster Configuration
# ============================================
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", "150"))
MAIN_NODE_URL = os.getenv("MAIN_NODE_URL", "")

# Load Balancing
# Set to true to bypass load balancing (development only)
USE_MAIN_WEBRTC = os.getenv("USE_MAIN_WEBRTC", "false").lower() == "true"

# ============================================
# CORS Configuration
# ============================================
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ============================================
# Network Configuration
# ============================================
# 서버의 실제 IP 주소 (내부 네트워크에서 접속 가능한 주소)
# Docker 컨테이너 내부에서는 실제 호스트 IP를 알 수 없으므로 환경변수로 설정
SERVER_IP = os.getenv("SERVER_IP", "localhost")

# ============================================
# Database Configuration
# ============================================
MONGO_URL = os.getenv(
    "MONGO_URL",
    "mongodb://airclass:airclass2025@localhost:27017/airclass?authSource=admin",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ============================================
# API Configuration
# ============================================
API_TITLE = "AIRClass Backend Server"
API_DESCRIPTION = "Real-time WebRTC streaming with multi-node cluster support"
API_VERSION = "2.0.0"
