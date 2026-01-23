#!/bin/bash

# UTF-8 인코딩 설정
export LANG=ko_KR.UTF-8

echo "========================================"
echo "  AIRClass 실시간 스트리밍 시스템"
echo "========================================"
echo ""

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "[오류] Docker가 설치되어 있지 않습니다."
    echo ""
    echo "Docker를 먼저 설치해주세요:"
    echo "  macOS: https://www.docker.com/products/docker-desktop"
    echo "  Linux: sudo apt install docker.io docker-compose"
    echo ""
    exit 1
fi

# Docker 실행 확인
if ! docker ps &> /dev/null; then
    echo "[오류] Docker가 실행되고 있지 않습니다."
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Docker Desktop을 실행해주세요."
    else
        echo "Docker 서비스를 시작해주세요: sudo systemctl start docker"
    fi
    echo ""
    exit 1
fi

# docker-compose 명령어 확인 (v1: docker-compose, v2: docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "[오류] docker-compose를 찾을 수 없습니다."
    exit 1
fi

# .env 파일 존재 확인
if [ ! -f ".env" ]; then
    echo "[경고] .env 파일이 없습니다. 기본 설정으로 생성합니다."
    echo ""
    ./setup.sh
    if [ $? -ne 0 ]; then
        echo "[오류] 설정 파일 생성에 실패했습니다."
        exit 1
    fi
fi

echo "[1단계] 기존 컨테이너 중지 중..."
$DOCKER_COMPOSE down &> /dev/null

echo "[2단계] 최신 이미지 빌드 중... (최초 실행시 1-2분 소요)"
$DOCKER_COMPOSE build
if [ $? -ne 0 ]; then
    echo "[오류] 빌드에 실패했습니다."
    exit 1
fi

echo "[3단계] 서버 시작 중..."
$DOCKER_COMPOSE up -d
if [ $? -ne 0 ]; then
    echo "[오류] 서버 시작에 실패했습니다."
    exit 1
fi

echo ""
echo "========================================"
echo "  서버가 성공적으로 시작되었습니다!"
echo "========================================"
echo ""

# .env에서 SERVER_IP 읽기
SERVER_IP=$(grep "^SERVER_IP=" .env | cut -d'=' -f2)
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="localhost"
fi

echo "접속 주소:"
echo "  - 선생님 페이지: http://${SERVER_IP}:5173/teacher"
echo "  - 학생 페이지:   http://${SERVER_IP}:5173/student"
echo "  - 관리자 페이지: http://${SERVER_IP}:8000/cluster/nodes"
echo ""
echo "서버 중지: ./stop.sh 실행"
echo "로그 보기: ./logs.sh 실행"
echo ""

# 15초 대기 후 상태 확인
echo "서버 초기화 중... (15초 대기)"
sleep 15

echo ""
echo "[서버 상태 확인]"
$DOCKER_COMPOSE ps

echo ""
echo "선생님 페이지를 브라우저에서 열까요? (y/N)"
read -r OPEN_BROWSER

if [[ "$OPEN_BROWSER" =~ ^[Yy]$ ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://${SERVER_IP}:5173/teacher"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "http://${SERVER_IP}:5173/teacher" 2>/dev/null || \
        sensible-browser "http://${SERVER_IP}:5173/teacher" 2>/dev/null || \
        echo "브라우저에서 http://${SERVER_IP}:5173/teacher 를 열어주세요"
    fi
fi

echo ""
echo "실행 완료!"
