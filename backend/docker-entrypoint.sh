#!/bin/bash
set -e

echo "=============================================="
echo "🚀 AIRClass Backend Starting"
echo "=============================================="
echo "Mode: ${MODE}"
echo "Node Name: ${NODE_NAME}"
echo "=============================================="

# MediaMTX 시작 (Master와 Slave는 다른 설정 파일 사용)
echo "📡 Starting MediaMTX..."
if [ "$MODE" = "master" ]; then
    echo "   Using Master configuration (RTMP Proxy enabled)"
    ./mediamtx mediamtx-master.yml &
else
    echo "   Using Slave configuration (Normal mode)"
    ./mediamtx mediamtx.yml &
fi

MEDIAMTX_PID=$!
echo "MediaMTX PID: $MEDIAMTX_PID"

# MediaMTX가 준비될 때까지 대기
sleep 3

# FastAPI 시작
echo "🐍 Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
