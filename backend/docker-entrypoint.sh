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

# SERVER_IP 환경변수가 설정되어 있는지 확인
if [ -z "$SERVER_IP" ] || [ "$SERVER_IP" = "localhost" ] || [ "$SERVER_IP" = "127.0.0.1" ]; then
    echo "⚠️  SERVER_IP not set or is localhost, detecting host IP..."
    # Docker 환경에서 호스트 IP 감지
    SERVER_IP=$(ip route | grep default | awk '{print $3}')
    if [ -z "$SERVER_IP" ]; then
        echo "⚠️  Could not detect host IP, using 127.0.0.1"
        SERVER_IP="127.0.0.1"
    else
        echo "✅ Detected host IP: $SERVER_IP"
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
