"""
Core Infrastructure Package
데이터베이스, 캐시, 메시징, 클러스터 등 핵심 인프라 모듈들
"""

from .database import get_database_manager, DatabaseManager
from .cache import get_cache, Cache
from .messaging import get_messaging_system, MessagingSystem
from .cluster import cluster_manager, init_cluster_mode, shutdown_cluster, NodeInfo
from .metrics import (
    http_requests_total,
    active_streams,
    active_websockets,
    active_connections,
    tokens_issued_total,
    cluster_nodes_total,
    cluster_load_percentage,
    cluster_connections,
    http_request_duration_seconds,
    recording_sessions_total,
    vod_views_total,
    ai_analysis_total,
    errors_total,
)
from .ai_keys import (
    encrypt_api_key,
    decrypt_api_key,
    upsert_teacher_gemini_key,
    delete_teacher_gemini_key,
    has_teacher_gemini_key,
    get_teacher_gemini_key,
    get_env_gemini_key,
)

__all__ = [
    # Database
    "get_database_manager",
    "DatabaseManager",
    # Cache
    "get_cache",
    "Cache",
    # Messaging
    "get_messaging_system",
    "MessagingSystem",
    # Cluster
    "cluster_manager",
    "init_cluster_mode",
    "shutdown_cluster",
    "NodeInfo",
    # Metrics
    "http_requests_total",
    "active_streams",
    "active_websockets",
    "active_connections",
    "tokens_issued_total",
    "cluster_nodes_total",
    "cluster_load_percentage",
    "cluster_connections",
    "http_request_duration_seconds",
    "recording_sessions_total",
    "vod_views_total",
    "ai_analysis_total",
    "errors_total",
    # AI Keys
    "encrypt_api_key",
    "decrypt_api_key",
    "upsert_teacher_gemini_key",
    "delete_teacher_gemini_key",
    "has_teacher_gemini_key",
    "get_teacher_gemini_key",
    "get_env_gemini_key",
]
