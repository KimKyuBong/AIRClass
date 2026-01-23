#!/bin/bash
# AIRClass Master RTMP Proxy Script
# MediaMTX runOnReady 훅에서 호출됨

PATH_NAME="$MTX_PATH"

# Master API에서 최적의 Slave 노드 정보 가져오기
SLAVE_INFO=$(curl -s http://127.0.0.1:8000/cluster/best-node)

if [ $? -ne 0 ]; then
    echo "❌ Failed to get optimal slave from Master API"
    exit 1
fi

# 디버깅: API 응답 출력
echo "DEBUG: SLAVE_INFO = $SLAVE_INFO"

# JSON 파싱 (python3 사용 - jq가 없을 수 있음)
SLAVE_ID=$(echo "$SLAVE_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin)['node_id'])" 2>/dev/null)
SLAVE_RTMP_PORT=$(echo "$SLAVE_INFO" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['rtmp_url'].split(':')[-1].split('/')[0])" 2>/dev/null || echo "1935")

echo "DEBUG: SLAVE_ID = $SLAVE_ID"
echo "DEBUG: SLAVE_RTMP_PORT = $SLAVE_RTMP_PORT"

# node_id 형식: slave-{container_hostname}
# Docker 내부 네트워크에서는 container_hostname으로 접근 가능
SLAVE_HOSTNAME=$(echo "$SLAVE_ID" | cut -d'-' -f2)
SLAVE_TARGET="$SLAVE_HOSTNAME"

echo "DEBUG: SLAVE_HOSTNAME = $SLAVE_HOSTNAME"
echo "DEBUG: SLAVE_TARGET = $SLAVE_TARGET"

echo "=========================================="
echo "🎯 RTMP Proxy for path: $PATH_NAME"
echo "📡 Forwarding to: $SLAVE_ID"
echo "🔗 Target: rtmp://$SLAVE_TARGET:1935/$PATH_NAME"
echo "=========================================="

# 스트림이 안정화될 때까지 잠깐 대기 (비디오 메타데이터가 준비되도록)
echo "⏳ Waiting 2 seconds for stream metadata to stabilize..."
sleep 2

# FFmpeg로 스트림 프록시 (RTMP에서 읽어서 RTMP로 전송)
# -fflags nobuffer: 버퍼링 최소화
# -flags low_delay: 낮은 지연
# -probesize/analyzeduration: 충분한 시간을 두고 모든 트랙 감지
# -map 0: 모든 스트림 강제 포함 (비디오 메타데이터가 불완전해도)
exec ffmpeg -hide_banner -loglevel info \
    -fflags nobuffer -flags low_delay \
    -probesize 10000000 -analyzeduration 5000000 \
    -i "rtmp://127.0.0.1:1935/$PATH_NAME" \
    -map 0 \
    -c:v copy -c:a copy \
    -max_interleave_delta 0 \
    -flush_packets 1 \
    -f flv "rtmp://$SLAVE_TARGET:1935/$PATH_NAME"
