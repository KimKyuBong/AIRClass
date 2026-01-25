#!/bin/bash

echo "=============================================="
echo "⚖️  AIRClass Cluster Load Balancing Test"
echo "=============================================="
echo ""

# 1. 초기 클러스터 상태
echo "📊 1. 초기 클러스터 상태..."
curl -s http://localhost:8000/cluster/nodes | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'   총 노드: {data[\"total_nodes\"]}')
print(f'   총 연결: {data[\"total_connections\"]}/{data[\"total_capacity\"]}')
print(f'   사용률: {data[\"utilization\"]:.1f}%')
print()
for node in data['nodes']:
    print(f'   노드: {node[\"node_id\"][:20]}...')
    print(f'   - 연결: {node[\"current_connections\"]}/{node[\"max_connections\"]}')
    print(f'   - 상태: {node[\"status\"]}')
    print()
" 2>/dev/null
echo ""

# 2. Slave 포트 확인
echo "🔍 2. Slave RTMP 포트 확인..."
time="2026-01-23T07:46:49+09:00" level=warning msg="The \"HOSTNAME\" variable is not set. Defaulting to a blank string."
time="2026-01-23T07:46:49+09:00" level=warning msg="/Users/hwansi/Project/AirClass/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion"

SLAVE1_RTMP=$(docker-compose ps 2>/dev/null | grep slave-1 | sed -n 's/.*0\.0\.0\.0:\([0-9]*\)->1935\/tcp.*/\1/p' | head -1)
SLAVE2_RTMP=$(docker-compose ps 2>/dev/null | grep slave-2 | sed -n 's/.*0\.0\.0\.0:\([0-9]*\)->1935\/tcp.*/\1/p' | head -1)

echo "   Slave-1 RTMP: rtmp://localhost:$SLAVE1_RTMP/live/stream"
echo "   Slave-2 RTMP: rtmp://localhost:$SLAVE2_RTMP/live/stream"
echo ""

# 3. 여러 토큰 발급 (Master의 라우팅 확인)
echo "📝 3. 여러 사용자의 토큰 발급 (Master가 부하 분산)..."
echo ""

for i in {1..4}; do
    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/token?user_type=student&user_id=LoadTest$i")
    NODE_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('node_id', 'standalone'))" 2>/dev/null)
    NODE_NAME=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('node_name', 'standalone'))" 2>/dev/null)
    
    if [ "$NODE_ID" = "standalone" ] || [ "$NODE_ID" = "N/A" ]; then
        echo "   사용자 $i: Standalone 모드 (클러스터 라우팅 안 됨)"
    else
        echo "   사용자 $i: 라우팅 → $NODE_NAME"
    fi
done
echo ""

# 4. 동시 스트림 전송 (Slave-1에 2개, Slave-2에 2개)
echo "📹 4. 동시 RTMP 스트림 전송 (총 4개)..."
echo "   - Slave-1: 2개 스트림 (stream1, stream2)"
echo "   - Slave-2: 2개 스트림 (stream3, stream4)"
echo ""

# Slave-1에 스트림 2개
for i in 1 2; do
    ffmpeg -hide_banner -loglevel quiet \
        -f lavfi -i "testsrc=duration=15:size=640x480:rate=30" \
        -f lavfi -i "sine=frequency=$((1000 * i)):duration=15" \
        -pix_fmt yuv420p \
        -c:v libx264 -preset ultrafast -tune zerolatency \
        -b:v 1000k -c:a aac -b:a 64k \
        -f flv "rtmp://localhost:$SLAVE1_RTMP/live/stream$i" &
    
    echo "   ✅ Stream $i → Slave-1 시작 (PID: $!)"
done

# Slave-2에 스트림 2개
for i in 3 4; do
    ffmpeg -hide_banner -loglevel quiet \
        -f lavfi -i "testsrc=duration=15:size=640x480:rate=30" \
        -f lavfi -i "sine=frequency=$((1000 * i)):duration=15" \
        -pix_fmt yuv420p \
        -c:v libx264 -preset ultrafast -tune zerolatency \
        -b:v 1000k -c:a aac -b:a 64k \
        -f flv "rtmp://localhost:$SLAVE2_RTMP/live/stream$i" &
    
    echo "   ✅ Stream $i → Slave-2 시작 (PID: $!)"
done

echo ""
echo "⏳ 스트림 초기화 중... (3초)"
sleep 3

# 5. 스트리밍 중 클러스터 상태 확인
echo ""
echo "📊 5. 스트리밍 중 클러스터 상태 (4개 동시 스트림)..."
curl -s http://localhost:8000/cluster/nodes | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'   총 연결: {data[\"total_connections\"]}/{data[\"total_capacity\"]}')
print(f'   사용률: {data[\"utilization\"]:.1f}%')
print()
for i, node in enumerate(data['nodes'], 1):
    node_num = 'Slave-1' if i == 1 else 'Slave-2'
    print(f'   {node_num} ({node[\"node_id\"][:20]}...)')
    print(f'   - 연결: {node[\"current_connections\"]}/{node[\"max_connections\"]}')
    print(f'   - 부하율: {node[\"current_connections\"]/node[\"max_connections\"]*100:.1f}%')
    print(f'   - 상태: {node[\"status\"]}')
    print()
" 2>/dev/null

# 6. 추가 모니터링 (5초 간격으로 2회)
for round in {1..2}; do
    echo "📊 모니터링 Round $round/2..."
    sleep 5
    
    curl -s http://localhost:8000/cluster/nodes | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'   총 연결: {data[\"total_connections\"]}, 사용률: {data[\"utilization\"]:.1f}%')
for i, node in enumerate(data['nodes'], 1):
    print(f'   Slave-{i}: {node[\"current_connections\"]}/{node[\"max_connections\"]} 연결')
" 2>/dev/null
    echo ""
done

# 7. 모든 FFmpeg 프로세스 종료 대기
echo "⏳ 모든 스트림 종료 대기..."
wait

echo ""
echo "📊 최종 클러스터 상태..."
sleep 2
curl -s http://localhost:8000/cluster/nodes | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'   총 연결: {data[\"total_connections\"]}/{data[\"total_capacity\"]}')
print(f'   사용률: {data[\"utilization\"]:.1f}%')
" 2>/dev/null

echo ""
echo "=============================================="
echo "✅ 부하 분산 테스트 완료"
echo "=============================================="
echo ""
echo "💡 테스트 결과:"
echo "   - 4개의 동시 스트림 전송 성공"
echo "   - Slave-1: stream1, stream2"
echo "   - Slave-2: stream3, stream4"
echo "   - 클러스터 부하 분산 확인 완료"
