#!/bin/bash
# 무한 루프로 테스트 스트림을 MediaMTX에 전송하는 스크립트
# 스트림이 끊어지면 자동으로 재시작

RTMP_URL="${RTMP_URL:-rtmp://localhost:1935/live/stream}"
LOG_FILE="${LOG_FILE:-/tmp/stream_test_loop.log}"

echo "=== Test Stream Loop Started ===" | tee -a "$LOG_FILE"
echo "RTMP URL: $RTMP_URL" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Press Ctrl+C to stop" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Cleanup on exit
cleanup() {
    echo "" | tee -a "$LOG_FILE"
    echo "=== Stopping stream ===" | tee -a "$LOG_FILE"
    pkill -P $$ ffmpeg 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# 무한 루프
while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$TIMESTAMP] Starting ffmpeg stream..." | tee -a "$LOG_FILE"
    
    # ffmpeg 실행 (10분 스트림, 끊어지면 재시작)
    ffmpeg -re \
        -f lavfi -i "testsrc=duration=600:size=1280x720:rate=30" \
        -f lavfi -i "sine=frequency=1000:duration=600" \
        -c:v libx264 -preset ultrafast -tune zerolatency \
        -pix_fmt yuv420p \
        -c:a aac -b:a 128k \
        -f flv "$RTMP_URL" \
        >> "$LOG_FILE" 2>&1
    
    EXIT_CODE=$?
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$TIMESTAMP] Stream completed normally, restarting in 2 seconds..." | tee -a "$LOG_FILE"
    else
        echo "[$TIMESTAMP] Stream failed (exit code: $EXIT_CODE), restarting in 5 seconds..." | tee -a "$LOG_FILE"
        sleep 5
        continue
    fi
    
    sleep 2
done
