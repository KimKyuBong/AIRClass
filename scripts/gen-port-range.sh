#!/usr/bin/env bash
# AIRClass 포트 범위 생성
# 같은 컴퓨터에서 여러 Main/Sub 인스턴스를 띄울 때 호스트 포트를 오프셋하여 충돌 방지
#
# 사용법:
#   ./scripts/gen-port-range.sh           # OFFSET=0 (기본값) 출력
#   ./scripts/gen-port-range.sh 100       # OFFSET=100 적용
#   ./scripts/gen-port-range.sh auto      # 빈 포트 범위 자동 탐지 후 출력
#   PORT_OFFSET=200 ./scripts/gen-port-range.sh
#   ./scripts/gen-port-range.sh 100 >> .env && docker-compose up -d
#
set -e

# 포트 사용 여부 확인 (TCP, 127.0.0.1)
_is_port_free() {
  local port=$1
  if command -v nc >/dev/null 2>&1; then
    ! nc -z 127.0.0.1 "$port" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('127.0.0.1', $port))
    s.close()
    exit(0)
except OSError:
    exit(1)
" 2>/dev/null
  else
    return 0
  fi
}

# 한 오프셋에 필요한 TCP 포트들이 모두 비어 있는지 확인
_ports_free_for_offset() {
  local o=$1
  _is_port_free $((8000 + o)) && \
  _is_port_free $((8001 + o)) && \
  _is_port_free $((8002 + o)) && \
  _is_port_free $((8003 + o)) && \
  _is_port_free $((1935 + o)) && \
  _is_port_free $((8889 + o)) && \
  _is_port_free $((8890 + o)) && \
  _is_port_free $((8891 + o)) && \
  _is_port_free $((8892 + o))
}

# auto: 0, 100, 200, ... 중 첫 번째로 비어 있는 오프셋 사용
if [ "${1:-}" = "auto" ]; then
  OFFSET=0
  while [ $OFFSET -lt 1000 ]; do
    if _ports_free_for_offset $OFFSET; then
      echo "# AIRClass 포트 범위 자동 탐지: OFFSET=${OFFSET} (빈 범위)" >&2
      break
    fi
    OFFSET=$((OFFSET + 100))
  done
  if [ $OFFSET -ge 1000 ]; then
    echo "# 경고: 0~900 범위에서 빈 포트를 찾지 못함. OFFSET=0 사용" >&2
    OFFSET=0
  fi
else
  OFFSET="${1:-${PORT_OFFSET:-0}}"
  OFFSET=$((OFFSET + 0))
fi

echo "# AIRClass 포트 범위 (PORT_OFFSET=${OFFSET}) - $(date -Iseconds 2>/dev/null || date)"
echo "# 같은 PC에서 두 번째 인스턴스: 이 값을 .env에 넣고 docker-compose up"
echo ""
echo "MAIN_API_PORT=$((8000 + OFFSET))"
echo "MAIN_RTMP_PORT=$((1935 + OFFSET))"
echo "MAIN_WEBRTC_HTTP_PORT=$((8889 + OFFSET))"
echo "MAIN_WEBRTC_UDP_PORT=$((8189 + OFFSET))"
echo "SUB1_API_PORT=$((8001 + OFFSET))"
echo "SUB1_WEBRTC_HTTP_PORT=$((8890 + OFFSET))"
echo "SUB1_WEBRTC_UDP_PORT=$((8190 + OFFSET))"
echo "SUB2_API_PORT=$((8002 + OFFSET))"
echo "SUB2_WEBRTC_HTTP_PORT=$((8891 + OFFSET))"
echo "SUB2_WEBRTC_UDP_PORT=$((8191 + OFFSET))"
echo "SUB3_API_PORT=$((8003 + OFFSET))"
echo "SUB3_WEBRTC_HTTP_PORT=$((8892 + OFFSET))"
echo "SUB3_WEBRTC_UDP_PORT=$((8192 + OFFSET))"
