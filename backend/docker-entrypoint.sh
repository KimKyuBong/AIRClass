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

# Main 노드인 경우
if [ "$MODE" = "main" ]; then
    echo "🔍 Configuring WebRTC ICE candidates for Main node..."
    # Main 노드도 ICE candidate에 IP 추가 필요
    sed -i "s|webrtcAdditionalHosts: \[\]|webrtcAdditionalHosts: ['${SERVER_IP}']|g" mediamtx-main.yml
    echo "📝 Updated Main MediaMTX config with ICE candidate: ${SERVER_IP}"
fi

# Sub 노드인 경우, 템플릿에서 mediamtx-sub.yml 생성 (포트/호스트 확실 반영)
if [ "$MODE" = "sub" ]; then
    echo "🔍 Generating mediamtx-sub.yml from template..."
    WEBRTC_PORT="${WEBRTC_UDP_PORT:-8189}"
    sed -e "s/__WEBRTC_UDP_PORT__/${WEBRTC_PORT}/g" -e "s/__SERVER_IP__/${SERVER_IP}/g" \
        mediamtx-sub.template.yml > mediamtx-sub.yml
    echo "✅ webrtcLocalUDPAddress/TCP: :${WEBRTC_PORT}, webrtcAdditionalHosts: ${SERVER_IP}"
    grep -E "webrtcLocal|webrtcAdditional" mediamtx-sub.yml || true
fi

# MediaMTX 시작 (백그라운드)
echo "📡 Starting MediaMTX..."
if [ "$MODE" = "main" ]; then
    echo "   Using Main configuration (RTMP Proxy enabled)"
    CONFIG_FILE="mediamtx-main.yml"
elif [ "$MODE" = "sub" ]; then
    echo "   Using Sub configuration (Stream Relay enabled)"
    # 환경 변수로 ICE 포트 강제
    export MTX_WEBRTCLOCALUDPADDRESS=":${WEBRTC_UDP_PORT:-8189}"
    export MTX_WEBRTCLOCALTCPADDRESS=":${WEBRTC_UDP_PORT:-8189}"
    CONFIG_FILE="mediamtx-sub.yml"
else
    echo "   Using Standard configuration"
    CONFIG_FILE="mediamtx.yml"
fi

./mediamtx "$CONFIG_FILE" &
MEDIAMTX_PID=$!
echo "MediaMTX PID: $MEDIAMTX_PID"

# MediaMTX가 준비될 때까지 대기
sleep 3

# FastAPI 시작 (포그라운드로 실행)
echo "🐍 Starting FastAPI in foreground..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
