#!/bin/bash

export LANG=ko_KR.UTF-8

echo "========================================"
echo "  AIRClass 완전 자동 설치"
echo "  (Docker + AIRClass 모두 설치)"
echo "========================================"
echo ""

# macOS 버전 확인
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "[오류] 이 스크립트는 macOS 전용입니다."
    echo "Linux는 install-linux.sh를 사용하세요."
    exit 1
fi

# Docker 설치 여부 확인하여 sudo 필요 여부 판단
NEED_SUDO=false
if ! command -v docker &> /dev/null; then
    NEED_SUDO=true
fi

# sudo 권한이 필요한 경우 미리 요청
if [ "$NEED_SUDO" = true ]; then
    echo "Docker 설치를 위해 관리자 권한이 필요합니다."
    echo "macOS 비밀번호를 입력해주세요:"
    echo ""
    
    # sudo 권한 미리 확보 (타임아웃 연장)
    sudo -v
    
    # sudo 타임아웃 방지 (백그라운드에서 5분마다 갱신)
    while true; do
        sleep 300
        sudo -v
    done 2>/dev/null &
    SUDO_REFRESH_PID=$!
    
    # 스크립트 종료 시 백그라운드 프로세스 정리
    trap "kill $SUDO_REFRESH_PID 2>/dev/null" EXIT
fi

echo ""

echo "[1/3] Docker 설치 확인 중..."
if command -v docker &> /dev/null; then
    echo "✓ Docker가 이미 설치되어 있습니다."
    
    # Docker 실행 확인
    if docker ps &> /dev/null; then
        echo "✓ Docker가 실행 중입니다."
    else
        echo ""
        echo "[Docker 실행 필요]"
        echo "Docker Desktop을 시작하는 중..."
        open -a Docker
        
        echo "Docker Engine이 시작될 때까지 대기 중... (최대 60초)"
        for i in {1..12}; do
            sleep 5
            if docker ps &> /dev/null; then
                echo "✓ Docker가 정상적으로 시작되었습니다!"
                break
            fi
            if [ $i -eq 12 ]; then
                echo ""
                echo "[타임아웃] Docker가 60초 내에 시작되지 않았습니다."
                echo ""
                echo "수동으로 Docker Desktop을 실행한 후"
                echo "./start.sh를 실행해주세요."
                echo ""
                exit 1
            fi
        done
    fi
else
    echo ""
    echo "[Docker 미설치 감지]"
    echo "Docker Desktop을 자동으로 다운로드하고 설치합니다."
    echo ""
    
    # Mac 칩 종류 확인
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        echo "감지된 시스템: Apple Silicon (M1/M2/M3)"
        DOCKER_URL="https://desktop.docker.com/mac/main/arm64/Docker.dmg"
    else
        echo "감지된 시스템: Intel Mac"
        DOCKER_URL="https://desktop.docker.com/mac/main/amd64/Docker.dmg"
    fi
    
    echo ""
    read -p "계속하시겠습니까? (y/N): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        echo "설치를 취소했습니다."
        exit 1
    fi
    
    echo ""
    echo "[2/3] Docker Desktop 다운로드 중..."
    echo "(약 500MB, 시간이 걸릴 수 있습니다)"
    echo ""
    
    TEMP_DIR="/tmp/airclass-install"
    mkdir -p "$TEMP_DIR"
    
    curl -L "$DOCKER_URL" -o "$TEMP_DIR/Docker.dmg"
    
    if [ ! -f "$TEMP_DIR/Docker.dmg" ]; then
        echo "[오류] Docker Desktop 다운로드에 실패했습니다."
        echo ""
        echo "수동 설치 방법:"
        echo "1. https://www.docker.com/products/docker-desktop 접속"
        echo "2. 'Download for Mac' 클릭"
        if [ "$ARCH" = "arm64" ]; then
            echo "3. 'Mac with Apple chip' 선택"
        else
            echo "3. 'Mac with Intel chip' 선택"
        fi
        echo "4. 다운로드한 파일 실행"
        echo "5. 설치 후 이 스크립트를 다시 실행하세요."
        echo ""
        exit 1
    fi
    
    echo ""
    echo "[3/3] Docker Desktop 설치 중..."
    echo ""
    
    # DMG 마운트
    hdiutil attach "$TEMP_DIR/Docker.dmg" -nobrowse -quiet
    
    # Docker.app을 Applications로 복사
    echo "Docker를 Applications 폴더에 복사 중..."
    sudo cp -R "/Volumes/Docker/Docker.app" /Applications/
    
    # DMG 언마운트
    hdiutil detach "/Volumes/Docker" -quiet
    
    # 임시 파일 삭제
    rm "$TEMP_DIR/Docker.dmg"
    
    echo "✓ Docker Desktop 설치가 완료되었습니다!"
    echo ""
    echo "Docker Desktop을 시작하는 중..."
    open -a Docker
    
    echo "Docker Engine이 시작될 때까지 대기 중... (최대 60초)"
    for i in {1..12}; do
        sleep 5
        if docker ps &> /dev/null 2>&1; then
            echo "✓ Docker가 정상적으로 시작되었습니다!"
            break
        fi
        if [ $i -eq 12 ]; then
            echo ""
            echo "[타임아웃] Docker가 60초 내에 시작되지 않았습니다."
            echo ""
            echo "Docker Desktop이 백그라운드에서 시작되고 있을 수 있습니다."
            echo "몇 분 후 ./start.sh를 실행해주세요."
            echo ""
            exit 1
        fi
    done
fi

echo ""
echo "[AIRClass 설정]"
echo ""

# setup.sh 실행
if [ -f "setup.sh" ]; then
    ./setup.sh
    if [ $? -ne 0 ]; then
        echo "[오류] AIRClass 설정에 실패했습니다."
        exit 1
    fi
else
    echo "[오류] setup.sh 파일을 찾을 수 없습니다."
    echo "AIRClass 폴더에서 이 스크립트를 실행해주세요."
    exit 1
fi

echo ""
echo "========================================"
echo "  설치가 완료되었습니다!"
echo "========================================"
echo ""
echo "다음 명령어로 서버를 시작하세요:"
echo "  ./start.sh"
echo ""

# .env에서 SERVER_IP 읽기
SERVER_IP=$(grep "^SERVER_IP=" .env 2>/dev/null | cut -d'=' -f2)
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="localhost"
fi

echo "서버 시작 후 브라우저에서 접속:"
echo "  - 선생님: http://${SERVER_IP}:5173/teacher"
echo "  - 학생:   http://${SERVER_IP}:5173/student"
echo ""
