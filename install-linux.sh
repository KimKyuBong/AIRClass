#!/bin/bash

export LANG=ko_KR.UTF-8

echo "========================================"
echo "  AIRClass 완전 자동 설치 (Linux)"
echo "  (Docker + AIRClass 모두 설치)"
echo "========================================"
echo ""

# Linux 배포판 확인
if [ ! -f /etc/os-release ]; then
    echo "[오류] Linux 배포판을 확인할 수 없습니다."
    exit 1
fi

. /etc/os-release
echo "감지된 배포판: $NAME $VERSION"
echo ""

# sudo 권한 확인 및 자동 요청
if [ "$EUID" -ne 0 ]; then 
    echo "이 스크립트는 관리자 권한이 필요합니다."
    echo "자동으로 sudo 권한을 요청합니다..."
    echo ""
    
    # sudo로 자동 재실행
    exec sudo bash "$0" "$@"
    exit $?
fi

echo "[1/4] Docker 설치 확인 중..."
if command -v docker &> /dev/null; then
    echo "✓ Docker가 이미 설치되어 있습니다."
else
    echo ""
    echo "[Docker 미설치 감지]"
    echo "Docker를 자동으로 설치합니다."
    echo ""
    
    read -p "계속하시겠습니까? (y/N): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        echo "설치를 취소했습니다."
        exit 1
    fi
    
    echo ""
    echo "[2/4] 시스템 업데이트 중..."
    apt-get update -qq
    
    echo "[3/4] Docker 설치 중..."
    
    # 필수 패키지 설치
    apt-get install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Docker 공식 GPG 키 추가
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Docker 저장소 추가
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Docker 설치
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Docker 서비스 시작
    systemctl start docker
    systemctl enable docker
    
    echo "✓ Docker 설치가 완료되었습니다!"
fi

echo ""
echo "[Docker Compose 확인]"
if docker compose version &> /dev/null; then
    echo "✓ Docker Compose가 설치되어 있습니다."
elif command -v docker-compose &> /dev/null; then
    echo "✓ Docker Compose (v1)가 설치되어 있습니다."
else
    echo "Docker Compose 설치 중..."
    apt-get install -y -qq docker-compose
    echo "✓ Docker Compose 설치 완료!"
fi

echo ""
echo "[4/4] Docker 그룹 설정"

# 현재 사용자 확인 (sudo로 실행했을 때 원래 사용자)
REAL_USER=${SUDO_USER:-$USER}

if groups $REAL_USER | grep -q '\bdocker\b'; then
    echo "✓ 사용자 '$REAL_USER'가 이미 docker 그룹에 속해 있습니다."
else
    echo "사용자 '$REAL_USER'를 docker 그룹에 추가 중..."
    usermod -aG docker $REAL_USER
    echo "✓ docker 그룹에 추가되었습니다."
    echo ""
    echo "[중요] 변경사항 적용을 위해 로그아웃 후 다시 로그인해주세요."
    echo "또는 다음 명령어로 즉시 적용:"
    echo "  newgrp docker"
fi

echo ""
echo "[AIRClass 설정]"
echo ""

# setup.sh를 원래 사용자 권한으로 실행
if [ -f "setup.sh" ]; then
    sudo -u $REAL_USER bash setup.sh
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
echo "또는 docker 그룹 적용 후:"
echo "  newgrp docker"
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
