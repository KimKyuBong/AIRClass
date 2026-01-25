#!/bin/bash
# 다수 클라이언트 동시 접속 테스트

set -e

BASE_URL="http://localhost:8000"
NUM_CLIENTS=10

echo "================================================================================"
echo "🧪 다수 클라이언트 동시 접속 테스트"
echo "📊 테스트 클라이언트 수: $NUM_CLIENTS"
echo "🕐 시작 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================================"
echo ""

# 테스트 전 MediaMTX 상태 확인
echo "📡 테스트 전 MediaMTX 상태:"
docker exec airclass-main-node curl -s http://localhost:9997/v3/paths/list | jq '.items[0] | {name, ready, readers: (.readers | length), tracks}'
echo ""

echo "Press Enter to start the concurrent test..."
read

echo ""
echo "🚀 동시 접속 테스트 시작..."
echo ""

# 임시 디렉토리 생성
TEMP_DIR=$(mktemp -d)
SUCCESS_COUNT=0
FAIL_COUNT=0

# 병렬로 토큰 요청
for i in $(seq 1 $NUM_CLIENTS); do
    (
        START_TIME=$(date +%s%N)
        
        # 토큰 요청
        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/token?user_type=student&user_id=test_user_$i" 2>/dev/null)
        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        BODY=$(echo "$RESPONSE" | head -n-1)
        
        END_TIME=$(date +%s%N)
        ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))
        
        if [ "$HTTP_CODE" == "200" ]; then
            WEBRTC_URL=$(echo "$BODY" | jq -r '.webrtc_url')
            
            if [ -n "$WEBRTC_URL" ] && [ "$WEBRTC_URL" != "null" ]; then
                echo "✅ Client $i: OK (${ELAPSED_MS}ms) - $WEBRTC_URL" | tee "$TEMP_DIR/success_$i"
            else
                echo "❌ Client $i: No webrtc_url" | tee "$TEMP_DIR/fail_$i"
            fi
        else
            echo "❌ Client $i: HTTP $HTTP_CODE" | tee "$TEMP_DIR/fail_$i"
        fi
    ) &
done

# Teacher 클라이언트 추가
(
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/token?user_type=teacher&user_id=teacher_test" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    if [ "$HTTP_CODE" == "200" ]; then
        echo "✅ Teacher: OK" | tee "$TEMP_DIR/success_teacher"
    else
        echo "❌ Teacher: HTTP $HTTP_CODE" | tee "$TEMP_DIR/fail_teacher"
    fi
) &

# Monitor 클라이언트 추가
(
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/token?user_type=monitor&user_id=monitor_test" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    if [ "$HTTP_CODE" == "200" ]; then
        echo "✅ Monitor: OK" | tee "$TEMP_DIR/success_monitor"
    else
        echo "❌ Monitor: HTTP $HTTP_CODE" | tee "$TEMP_DIR/fail_monitor"
    fi
) &

# 모든 백그라운드 작업 대기
wait

echo ""
echo "================================================================================"
echo "📊 테스트 결과 분석"
echo "================================================================================"

# 결과 집계
SUCCESS_COUNT=$(ls $TEMP_DIR/success_* 2>/dev/null | wc -l | tr -d ' ')
FAIL_COUNT=$(ls $TEMP_DIR/fail_* 2>/dev/null | wc -l | tr -d ' ')
TOTAL=$((NUM_CLIENTS + 2))  # students + teacher + monitor

echo "✅ 성공: $SUCCESS_COUNT/$TOTAL"
echo "❌ 실패: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
    echo "❌ 실패한 요청:"
    cat $TEMP_DIR/fail_* 2>/dev/null
    echo ""
fi

# 정리
rm -rf $TEMP_DIR

echo "⏳ WebRTC 연결 확립 대기 중 (5초)..."
sleep 5

echo ""
echo "📡 테스트 후 MediaMTX 상태:"
docker exec airclass-main-node curl -s http://localhost:9997/v3/paths/list | jq '.items[0] | {name, ready, readers: (.readers | length), tracks, bytesReceived, bytesSent}'

echo ""
echo "================================================================================"
echo "🎯 최종 결과"
echo "================================================================================"
echo "총 테스트 클라이언트: $TOTAL"
echo "성공한 토큰 발급: $SUCCESS_COUNT"
echo "실패: $FAIL_COUNT"

if [ $SUCCESS_COUNT -eq $TOTAL ] && [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo "✅ 모든 클라이언트가 정상적으로 토큰을 받았습니다!"
else
    echo ""
    echo "⚠️  일부 클라이언트에서 문제가 발생했습니다."
fi

echo "================================================================================"
