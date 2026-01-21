#!/bin/bash

# WebRTC Screen Streaming Server 시작 스크립트

cd "$(dirname "$0")"

echo "="  * 60
echo "🎥 Starting WebRTC Screen Streaming Server"
echo "=" * 60

# MediaMTX 먼저 시작
echo "📡 Starting MediaMTX..."
./mediamtx &
MEDIAMTX_PID=$!
echo "✅ MediaMTX started (PID: $MEDIAMTX_PID)"

# 잠시 대기
sleep 2

# FastAPI 서버 시작
echo "🚀 Starting FastAPI server..."
source venv/bin/activate
python main.py

# Cleanup on exit
trap "kill $MEDIAMTX_PID 2>/dev/null" EXIT
