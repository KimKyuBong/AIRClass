#!/bin/bash

# AIRClass 서버 상태 확인 스크립트

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PID_DIR="./.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

echo -e "${CYAN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         AIRClass 서버 상태 확인          ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Backend 서버 상태
echo -e "${YELLOW}Backend 서버:${NC}"
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "  상태: ${GREEN}실행 중${NC}"
        echo -e "  PID: $BACKEND_PID"
        echo -e "  URL: http://localhost:8000"
    else
        echo -e "  상태: ${RED}중지됨${NC} (PID 파일이 남아있지만 프로세스가 없음)"
    fi
else
    echo -e "  상태: ${RED}중지됨${NC}"
fi

echo ""

# Frontend 서버 상태
echo -e "${YELLOW}Frontend 서버:${NC}"
if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "  상태: ${GREEN}실행 중${NC}"
        echo -e "  PID: $FRONTEND_PID"
        echo -e "  URL: http://localhost:5173"
    else
        echo -e "  상태: ${RED}중지됨${NC} (PID 파일이 남아있지만 프로세스가 없음)"
    fi
else
    echo -e "  상태: ${RED}중지됨${NC}"
fi

echo ""

# 포트 사용 확인
echo -e "${YELLOW}포트 사용 현황:${NC}"
if lsof -i :8000 >/dev/null 2>&1; then
    echo -e "  8000 (Backend):  ${GREEN}사용 중${NC}"
else
    echo -e "  8000 (Backend):  ${RED}사용 안 함${NC}"
fi

if lsof -i :5173 >/dev/null 2>&1; then
    echo -e "  5173 (Frontend): ${GREEN}사용 중${NC}"
else
    echo -e "  5173 (Frontend): ${RED}사용 안 함${NC}"
fi

echo ""
