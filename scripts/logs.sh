#!/bin/bash

export LANG=ko_KR.UTF-8

echo "========================================"
echo "  AIRClass 서버 로그"
echo "========================================"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo ""

# docker-compose 명령어 확인
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "[오류] docker-compose를 찾을 수 없습니다."
    exit 1
fi

$DOCKER_COMPOSE logs -f --tail=100
