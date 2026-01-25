#!/bin/bash
# 브라우저에서 테스트하기 위한 스크립트

echo "======================================================================"
echo "🎉 AIRClass 화면 표시 테스트"
echo "======================================================================"
echo ""
echo "1️⃣  서버 상태 확인 중..."
echo ""

# 백엔드 확인
if curl -s http://localhost:8000/api/status > /dev/null 2>&1; then
    echo "  ✅ Backend 서버: 실행 중 (http://localhost:8000)"
else
    echo "  ❌ Backend 서버: 중지됨"
    exit 1
fi

# 프론트엔드 확인
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "  ✅ Frontend 서버: 실행 중 (http://localhost:5173)"
else
    echo "  ❌ Frontend 서버: 중지됨"
    exit 1
fi

echo ""
echo "2️⃣  브라우저 열기 안내"
echo ""
echo "  다음 URL들을 브라우저에서 열어주세요:"
echo ""
echo "  👨‍🏫 교사 화면:  http://localhost:5173/#/teacher"
echo "  👨‍🎓 학생 화면:  http://localhost:5173/#/student"
echo "  📺 모니터 화면: http://localhost:5173/#/monitor"
echo ""
echo "3️⃣  화면 전송 시작"
echo ""
echo "  화면 데이터를 시뮬레이션하여 전송합니다..."
echo "  (Ctrl+C로 중지 가능)"
echo ""
echo "======================================================================"
echo ""

# 화면 시뮬레이션 시작
cd "$(dirname "$0")"
source backend/venv/bin/activate
python test_screen_send.py
