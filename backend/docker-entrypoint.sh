#!/bin/bash
set -e

echo "=============================================="
echo "🚀 AIRClass Backend Starting"
echo "=============================================="
echo "Mode: ${MODE}"
echo "Node Name: ${NODE_NAME}"
echo "=============================================="

# SERVER_IP 환경변수가 설정되어 있는지 확인
if [ -z "$SERVER_IP" ]; then
    echo "⚠️  SERVER_IP not set, using localhost"
    SERVER_IP="localhost"
fi

# Main 노드인 경우
if [ "$MODE" = "main" ]; then
    echo "🔍 Configuring WebRTC ICE candidates for Main node..."
    # Main 노드도 ICE candidate에 IP 추가 필요
    sed -i "s|webrtcAdditionalHosts: \[\]|webrtcAdditionalHosts: ['${SERVER_IP}']|g" mediamtx-main.yml
    echo "📝 Updated Main MediaMTX config with ICE candidate: ${SERVER_IP}"
fi

# Sub 노드인 경우, 외부 포트를 사용하여 MediaMTX 설정 수정
if [ "$MODE" = "sub" ]; then
    echo "🔍 Configuring WebRTC ICE candidates for Sub node..."
    
    # MediaMTX 설정 파일에 동적으로 ICE 후보 및 UDP 포트 설정
    if [ ! -z "$WEBRTC_UDP_PORT" ]; then
        # MediaMTX가 외부 포트와 동일한 포트로 리스닝하도록 변경
        # 이렇게 하면 Docker 포트 매핑이 8190:8190처럼 1:1이 되어
        # ICE candidate에 올바른 포트가 들어감
        sed -i "s|webrtcLocalUDPAddress: :8189|webrtcLocalUDPAddress: :${WEBRTC_UDP_PORT}|g" mediamtx.yml
        sed -i "s|webrtcLocalTCPAddress: ':8189'|webrtcLocalTCPAddress: ':${WEBRTC_UDP_PORT}'|g" mediamtx.yml
        echo "✅ Set MediaMTX UDP/TCP port to: ${WEBRTC_UDP_PORT}"
    fi
    
    # IP 주소를 ICE candidate에 추가
    sed -i "s|webrtcAdditionalHosts: \[\]|webrtcAdditionalHosts: ['${SERVER_IP}']|g" mediamtx.yml
    echo "📝 Updated MediaMTX config with ICE candidate: ${SERVER_IP}"
fi

# MediaMTX 시작 (Main과 Sub는 다른 설정 파일 사용)
echo "📡 Starting MediaMTX..."
if [ "$MODE" = "main" ]; then
    echo "   Using Main configuration (RTMP Proxy enabled)"
    ./mediamtx mediamtx-main.yml &
else
    echo "   Using Sub configuration (Normal mode)"
    ./mediamtx mediamtx.yml &
fi

MEDIAMTX_PID=$!
echo "MediaMTX PID: $MEDIAMTX_PID"

# MediaMTX가 준비될 때까지 대기
sleep 3

# FastAPI 시작
echo "🐍 Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
