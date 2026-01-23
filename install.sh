#!/bin/bash

# AIRClass 올인원 자동 설치 스크립트
# OS를 자동 감지하고 적절한 설치 스크립트 실행

export LANG=ko_KR.UTF-8

echo "========================================"
echo "  AIRClass 자동 설치"
echo "========================================"
echo ""

# OS 감지
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "감지된 OS: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "감지된 OS: Linux"
else
    echo "[오류] 지원하지 않는 운영체제입니다: $OSTYPE"
    echo ""
    echo "지원 OS:"
    echo "  - macOS"
    echo "  - Linux (Ubuntu/Debian)"
    echo "  - Windows (install.bat 사용)"
    exit 1
fi

echo ""

# 적절한 설치 스크립트 실행
if [ "$OS" = "macos" ]; then
    if [ -f "install-macos.sh" ]; then
        bash install-macos.sh
    else
        echo "[오류] install-macos.sh 파일을 찾을 수 없습니다."
        exit 1
    fi
elif [ "$OS" = "linux" ]; then
    if [ -f "install-linux.sh" ]; then
        bash install-linux.sh
    else
        echo "[오류] install-linux.sh 파일을 찾을 수 없습니다."
        exit 1
    fi
fi
