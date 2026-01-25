#!/bin/bash

# AIRClass 개발 서버 시작 스크립트
# Backend (FastAPI) + Frontend (Svelte) 동시 실행

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# PID 파일 저장 경로
PID_DIR="./.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# PID 디렉토리 생성
mkdir -p "$PID_DIR"

# 종료 핸들러
cleanup() {
    echo ""
    log_info "서버를 종료하는 중..."
    
    if [ -f "$BACKEND_PID_FILE" ]; then
        BACKEND_PID=$(cat "$BACKEND_PID_FILE")
        if kill -0 "$BACKEND_PID" 2>/dev/null; then
            kill "$BACKEND_PID"
            log_success "Backend 서버 종료됨 (PID: $BACKEND_PID)"
        fi
        rm -f "$BACKEND_PID_FILE"
    fi
    
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            kill "$FRONTEND_PID"
            log_success "Frontend 서버 종료됨 (PID: $FRONTEND_PID)"
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    log_info "모든 서버가 종료되었습니다."
    exit 0
}

# SIGINT, SIGTERM 시그널에 cleanup 함수 등록
trap cleanup SIGINT SIGTERM

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════╗"
echo "║         AIRClass 개발 서버 시작          ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Backend 서버 시작
log_info "Backend 서버 시작 중..."
cd backend

# Python venv 확인 및 생성
if [ ! -d "venv" ]; then
    log_warning "Python venv가 없습니다. 생성 중..."
    python3 -m venv venv
fi

# 의존성 설치 (venv 활성화 없이)
if [ ! -f "venv/.installed" ]; then
    log_info "Python 의존성 설치 중..."
    venv/bin/pip install -q -r requirements.txt
    touch venv/.installed
fi

# Backend 서버 백그라운드 실행
log_info "FastAPI 서버 실행 중..."
venv/bin/python main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "../$BACKEND_PID_FILE"
log_success "Backend 서버 시작됨 (PID: $BACKEND_PID)"
log_info "Backend URL: http://localhost:8000"

cd ..

# 2. Frontend 서버 시작
log_info "Frontend 서버 시작 중..."
cd frontend

# Node modules 확인 및 설치
if [ ! -d "node_modules" ]; then
    log_info "Node.js 의존성 설치 중..."
    npm install
fi

# Frontend 서버 백그라운드 실행
log_info "Vite 개발 서버 실행 중..."
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "../$FRONTEND_PID_FILE"
log_success "Frontend 서버 시작됨 (PID: $FRONTEND_PID)"
log_info "Frontend URL: http://localhost:5173"

cd ..

# 서버 시작 대기
sleep 3

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        모든 서버가 실행되었습니다!       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}접속 주소:${NC}"
echo -e "  ${YELLOW}Backend:${NC}   http://localhost:8000"
echo -e "  ${YELLOW}Frontend:${NC}  http://localhost:5173"
echo ""
echo -e "${CYAN}페이지:${NC}"
echo -e "  ${YELLOW}교사용:${NC}    http://localhost:5173/#/teacher"
echo -e "  ${YELLOW}학생용:${NC}    http://localhost:5173/#/student"
echo -e "  ${YELLOW}모니터:${NC}    http://localhost:5173/#/monitor"
echo ""
echo -e "${CYAN}로그 파일:${NC}"
echo -e "  ${YELLOW}Backend:${NC}   logs/backend.log"
echo -e "  ${YELLOW}Frontend:${NC}  logs/frontend.log"
echo ""
echo -e "${RED}종료하려면 Ctrl+C를 누르세요${NC}"
echo ""

# 로그 실시간 출력
tail -f logs/backend.log logs/frontend.log
