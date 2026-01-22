#!/bin/bash

echo "=============================================="
echo "🎥 AIRClass RTMP Stream Test"
echo "=============================================="
echo ""

# Backend에서 가상환경 활성화 및 토큰 발급
echo "📝 1. JWT 토큰 발급..."
cd backend && source .venv/bin/activate && cd ..
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/token?user_type=student&user_id=StreamTest")
TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null)
HLS_URL=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['hls_url'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ 토큰 발급 실패"
    exit 1
fi

echo "✅ 토큰 발급 성공"
echo "   Token: ${TOKEN:0:50}..."
echo "   HLS URL: $HLS_URL"
echo ""

# RTMP 스트림 전송
echo "📹 2. 테스트 패턴 RTMP 스트림 전송 (20초)..."
echo "   RTMP URL: rtmp://localhost:1935/live/stream"
echo ""

ffmpeg -hide_banner -loglevel error \
    -f lavfi -i "testsrc=duration=20:size=1280x720:rate=30,drawtext=text='AIRClass Test Stream %{localtime}':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
    -f lavfi -i "sine=frequency=1000:duration=20" \
    -pix_fmt yuv420p \
    -c:v libx264 -preset ultrafast -tune zerolatency \
    -b:v 2000k -maxrate 2000k -bufsize 4000k \
    -g 60 -keyint_min 60 \
    -c:a aac -b:a 128k \
    -f flv rtmp://localhost:1935/live/stream &

FFMPEG_PID=$!

# 스트림 초기화 대기
echo "⏳ 스트림 초기화 중..."
sleep 5

# HLS 스트림 확인
echo ""
echo "🔍 3. HLS 스트림 확인..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HLS_URL")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ HLS 스트림 생성 성공!"
    echo ""
    echo "=============================================="
    echo "🎉 스트림 재생 가능!"
    echo "=============================================="
    echo ""
    echo "📱 브라우저에서 확인하세요:"
    echo "   http://localhost:5173/#/student"
    echo ""
    echo "1. 이름 입력 (예: TestUser)"
    echo "2. '수업 참여하기' 클릭"
    echo "3. 비디오가 자동 재생됩니다"
    echo ""
    echo "⏰ 20초 후 자동 종료됩니다..."
else
    echo "❌ HLS 스트림 생성 실패 (HTTP $HTTP_CODE)"
    kill $FFMPEG_PID 2>/dev/null
    exit 1
fi

# FFmpeg가 종료될 때까지 대기
wait $FFMPEG_PID 2>/dev/null

echo ""
echo "✅ 스트림 전송 완료"
echo "=============================================="
