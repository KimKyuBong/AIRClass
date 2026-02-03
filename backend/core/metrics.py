"""
Prometheus Metrics
애플리케이션 모니터링을 위한 Prometheus 메트릭 정의
"""

from prometheus_client import Counter, Gauge, Histogram

# HTTP 요청 카운터
http_requests_total = Counter(
    "airclass_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# 활성 스트림 게이지
active_streams = Gauge(
    "airclass_active_streams",
    "Number of currently active streams",
)

# WebSocket 연결 게이지
active_websockets = Gauge(
    "airclass_active_websockets",
    "Number of currently active WebSocket connections",
    ["type"],  # teacher, student, monitor
)

# WebSocket 연결 게이지 (Alias for backwards compatibility)
active_connections = active_websockets

# 토큰 발급 카운터
tokens_issued_total = Counter(
    "airclass_tokens_issued_total",
    "Total JWT tokens issued",
    ["user_type"],  # teacher, student, monitor
)

# 클러스터 노드 게이지
cluster_nodes_total = Gauge(
    "airclass_cluster_nodes_total",
    "Total number of cluster nodes",
    ["status"],  # active, offline, unhealthy
)

# 클러스터 로드 게이지
cluster_load_percentage = Gauge(
    "airclass_cluster_load_percentage",
    "Load percentage per node",
    ["node_id"],
)

# 클러스터 연결 게이지
cluster_connections = Gauge(
    "airclass_cluster_connections",
    "Current connections per node",
    ["node_id"],
)

# 요청 처리 시간 히스토그램
http_request_duration_seconds = Histogram(
    "airclass_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

# 녹화 세션 카운터
recording_sessions_total = Counter(
    "airclass_recording_sessions_total",
    "Total number of recording sessions",
    ["status"],  # started, stopped, failed
)

# VOD 조회 카운터
vod_views_total = Counter(
    "airclass_vod_views_total",
    "Total number of VOD views",
)

# AI 분석 카운터
ai_analysis_total = Counter(
    "airclass_ai_analysis_total",
    "Total number of AI analyses",
    ["type"],  # vision, nlp, feedback
)

# 에러 카운터
errors_total = Counter(
    "airclass_errors_total",
    "Total errors",
    ["type"],  # auth, stream, cluster, websocket
)
