#!/bin/bash

export LANG=ko_KR.UTF-8

echo "========================================"
echo "  AIRClass GUI 실행 파일 빌드"
echo "  (macOS .app 생성)"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Python 설치 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python이 설치되어 있지 않습니다."
    echo "https://www.python.org/downloads/ 에서 설치해주세요."
    exit 1
fi

echo "[1/3] 필요한 패키지 설치 중..."
pip3 install -r requirements.txt
pip3 install pyinstaller

echo ""
echo "[2/3] 실행 파일 빌드 중..."
echo "(시간이 걸릴 수 있습니다)"
echo ""

pyinstaller --name="AIRClass" \
    --onefile \
    --windowed \
    --icon=NONE \
    --add-data="../.env:." \
    --add-data="../docker-compose.yml:." \
    --hidden-import=customtkinter \
    --hidden-import=PIL \
    --hidden-import=dotenv \
    airclass_gui.py

if [ $? -ne 0 ]; then
    echo "[오류] 빌드에 실패했습니다."
    exit 1
fi

echo ""
echo "[3/3] 빌드 완료!"
echo ""
echo "생성된 파일:"
echo "  dist/AIRClass.app"
echo ""
echo "사용 방법:"
echo "  1. dist/AIRClass.app을 Applications 폴더로 이동"
echo "  2. AIRClass.app 더블클릭으로 실행"
echo ""
