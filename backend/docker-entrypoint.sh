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

# SERVER_IP: .env/스크립트/GUI로 주입 (한 개만 설정하면 접속 URL·LiveKit URL 모두 이 IP 기준).
# 비어 있을 때만 자동 감지.
#
# [도커] Linux에서는 호스트 LAN IP를 알 수 없으므로 .env에 SERVER_IP 설정 권장.
# Mac/Windows Docker Desktop은 host.docker.internal로 감지 가능.
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
            echo "✅ Detected gateway: $SERVER_IP (on Linux set SERVER_IP in .env for browser access)"
        fi
    fi
fi

# MediaMTX logic removed (Main/Sub configuration)
# if [ "$MODE" = "main" ]; then ... fi
# if [ "$MODE" = "sub" ]; then ... fi

# MediaMTX 시작 logic removed
# echo "📡 Starting MediaMTX..."
# ./mediamtx "$CONFIG_FILE" &

# LiveKit 설정 파일만 생성 (서버는 livekit_manager.py에서 시작)
echo "📡 Generating LiveKit config..."
mkdir -p /app/configs
export SERVER_IP=${SERVER_IP:-127.0.0.1}
python3 -c "
from core.livekit_config import LiveKitConfigGenerator
generator = LiveKitConfigGenerator(node_id='main', mode='main', redis_url='${REDIS_URL:-redis://redis:6379}')
generator.save_to_file('/app/configs/livekit.yaml')
print('✅ LiveKit config saved to /app/configs/livekit.yaml')
"

# FastAPI 시작 (포그라운드로 실행) - LiveKit 서버는 livekit_manager.py에서 시작
echo "🐍 Starting FastAPI in foreground..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
