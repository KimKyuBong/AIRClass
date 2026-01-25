#!/bin/bash

echo "=============================================="
echo "🎥 AIRClass Cluster RTMP Streaming Test"
echo "=============================================="
echo ""

# FFmpeg 설치 확인
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg가 설치되어 있지 않습니다"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt install ffmpeg"
    exit 1
fi

# 1. 클러스터 상태 확인
echo "📊 1. 클러스터 상태 확인..."
CLUSTER_STATUS=$(curl -s http://localhost:8000/cluster/nodes)
TOTAL_NODES=$(echo $CLUSTER_STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['total_nodes'])" 2>/dev/null)

if [ -z "$TOTAL_NODES" ]; then
    echo "❌ 클러스터 연결 실패"
    exit 1
fi

echo "✅ 클러스터 실행 중"
echo "   총 노드: $TOTAL_NODES"
echo ""

# 2. Master에 토큰 요청 (Master가 최적의 Slave 선택)
echo "📝 2. Master에게 토큰 요청 (자동 라우팅)..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/token?user_type=student&user_id=ClusterStreamTest")
TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
HLS_URL=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('hls_url', ''))" 2>/dev/null)
NODE_ID=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('node_id', 'N/A'))" 2>/dev/null)
NODE_NAME=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('node_name', 'N/A'))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ 토큰 발급 실패"
    echo "   Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ 토큰 발급 성공"
echo "   라우팅된 노드: $NODE_NAME ($NODE_ID)"
echo "   Token: ${TOKEN:0:50}..."
echo "   HLS URL: $HLS_URL"
echo ""

# 3. Slave 노드의 RTMP 포트 확인
echo "🔍 3. Slave 노드 RTMP 포트 확인..."
echo ""
docker-compose ps | grep slave | awk '{print $1, $NF}' | while read container ports; do
    RTMP_PORT=$(echo $ports | sed -n 's/.*0\.0\.0\.0:\([0-9]*\)->1935\/tcp.*/\1/p' | head -1)
    echo "   📡 $container: rtmp://localhost:$RTMP_PORT/live/stream"
done
echo ""

# 첫 번째 Slave의 RTMP 포트 사용
SLAVE1_RTMP=$(docker-compose ps | grep slave-1 | sed -n 's/.*0\.0\.0\.0:\([0-9]*\)->1935\/tcp.*/\1/p' | head -1)

if [ -z "$SLAVE1_RTMP" ]; then
    echo "❌ Slave RTMP 포트를 찾을 수 없습니다"
    exit 1
fi

RTMP_URL="rtmp://localhost:$SLAVE1_RTMP/live/stream"
echo "🎯 테스트용 RTMP URL: $RTMP_URL"
echo ""

# 4. RTMP 스트림 전송 (20초)
echo "📹 4. 테스트 패턴 RTMP 스트림 전송 (20초)..."
echo ""

ffmpeg -hide_banner -loglevel error -stats \
    -f lavfi -i "testsrc=duration=20:size=1280x720:rate=30,drawtext=text='AIRClass Cluster Test %{localtime}':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
    -f lavfi -i "sine=frequency=1000:duration=20" \
    -pix_fmt yuv420p \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -b:v 2000k -maxrate 2000k -bufsize 4000k \
    -g 60 -keyint_min 60 \
    -c:a aac -b:a 128k \
    -f flv "$RTMP_URL" &

FFMPEG_PID=$!

# 스트림 초기화 대기
echo "⏳ 스트림 초기화 중..."
sleep 5

# 5. HLS 스트림 확인
echo ""
echo "🔍 5. HLS 스트림 확인..."

# MediaMTX가 생성한 HLS 세그먼트 확인
SLAVE1_HLS=$(docker-compose ps | grep slave-1 | sed -n 's/.*0\.0\.0\.0:\([0-9]*\)->8888\/tcp.*/\1/p' | head -1)
HLS_CHECK_URL="http://localhost:$SLAVE1_HLS/live/stream/index.m3u8"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HLS_CHECK_URL" 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ HLS 스트림 생성 성공!"
    echo ""
    echo "=============================================="
    echo "🎉 클러스터 스트리밍 작동 중!"
    echo "=============================================="
    echo ""
    echo "📱 브라우저에서 확인:"
    echo "   http://localhost:5173/#/student"
    echo ""
    echo "📊 클러스터 모니터링:"
    echo "   http://localhost:5173/admin"
    echo ""
    echo "⏰ 20초 후 자동 종료됩니다..."
else
    echo "⚠️  HLS 스트림 확인 실패 (HTTP $HTTP_CODE)"
    echo "   스트림은 전송 중이지만 HLS 세그먼트가 아직 생성되지 않았을 수 있습니다"
    echo "   계속 진행합니다..."
fi

# 6. 스트리밍 중 클러스터 상태 모니터링
echo ""
echo "📊 6. 클러스터 상태 모니터링..."
sleep 3

CLUSTER_STATUS_LIVE=$(curl -s http://localhost:8000/cluster/nodes)
echo "$CLUSTER_STATUS_LIVE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"   총 연결: {data['total_connections']}/{data['total_capacity']}\")
print(f\"   사용률: {data['utilization']:.1f}%\")
print()
for node in data['nodes']:
    print(f\"   노드: {node['node_id']}\")
    print(f\"   - 연결: {node['current_connections']}/{node['max_connections']}\")
    print(f\"   - 상태: {node['status']}\")
    print()
" 2>/dev/null

# FFmpeg가 종료될 때까지 대기
wait $FFMPEG_PID 2>/dev/null

echo ""
echo "✅ 스트림 전송 완료"
echo ""

# 7. 최종 클러스터 상태 확인
echo "📊 7. 최종 클러스터 상태..."
sleep 2
FINAL_STATUS=$(curl -s http://localhost:8000/cluster/nodes)
echo "$FINAL_STATUS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"   총 연결: {data['total_connections']}/{data['total_capacity']}\")
print(f\"   사용률: {data['utilization']:.1f}%\")
" 2>/dev/null

echo ""
echo "=============================================="
echo "✅ 클러스터 스트리밍 테스트 완료"
echo "=============================================="
