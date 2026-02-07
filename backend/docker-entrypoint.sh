#!/bin/bash
set -e

# MediaMTX 설정 파일은 /app에 있음
cd /app

echo "=============================================="
echo "🚀 AIRClass Backend Starting"
echo "=============================================="
echo "Mode: ${MODE}"
echo "Node Name: ${NODE_NAME}"
echo "=============================================="

# SERVER_IP: 스크립트/GUI 또는 .env로 주입 권장 (기본값 10.100.0.102).
# 비어 있을 때만 자동 감지하며, 한 번 설정되면 덮어쓰지 않음.
#
# [도커 입장에서 "상위(호스트) 인터페이스" IP]
# - Linux: 컨테이너 안에서 호스트의 실제 LAN IP(eth0 등)는 알 수 없음.
#   ip route 기본 게이트웨이 = Docker 브리지 IP(172.17.0.1, 172.18.0.1 등)일 뿐이라
#   브라우저/외부에서는 접근 불가. → SERVER_IP / LIVEKIT_PUBLIC_URL 은 .env 등으로 반드시 설정 권장.
# - Mac/Windows (Docker Desktop): host.docker.internal 이 호스트로 접근 가능한 IP로 풀림.
# - Linux + extra_hosts (host.docker.internal:host-gateway): host.docker.internal = 브리지 게이트웨이(172.x) → 역시 외부 접근용 아님.
if [ -z "$SERVER_IP" ]; then
    echo "⚠️  SERVER_IP not set, trying to detect host..."
    # 1) Docker Desktop (Mac/Windows): host.docker.internal 이 있으면 그 IP 사용
    if SERVER_IP=$(getent hosts host.docker.internal 2>/dev/null | awk '{print $1}' | head -1) && [ -n "$SERVER_IP" ]; then
        echo "✅ Using host.docker.internal: $SERVER_IP"
    else
        # 2) Linux 등: 기본 게이트웨이 (브리지 IP, 외부 접근 불가일 수 있음)
        SERVER_IP=$(ip route 2>/dev/null | grep default | awk '{print $3}')
        if [ -z "$SERVER_IP" ]; then
            echo "⚠️  Could not detect host IP, using 127.0.0.1"
            SERVER_IP="127.0.0.1"
        else
            echo "✅ Detected gateway: $SERVER_IP (on Linux this is often 172.x; set SERVER_IP/LIVEKIT_PUBLIC_URL in .env for browser access)"
        fi
    fi
fi

# MediaMTX logic removed (Main/Sub configuration)
# if [ "$MODE" = "main" ]; then ... fi
# if [ "$MODE" = "sub" ]; then ... fi

# MediaMTX 시작 logic removed
# echo "📡 Starting MediaMTX..."
# ./mediamtx "$CONFIG_FILE" &

# FastAPI 시작 (포그라운드로 실행)
echo "🐍 Starting FastAPI in foreground..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
