#!/bin/bash

# AIRClass 서버 중지 스크립트

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

PID_DIR="./.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

echo -e "${RED}╔═══════════════════════════════════════════╗${NC}"
echo -e "${RED}║         AIRClass 서버 중지 중...         ║${NC}"
echo -e "${RED}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Backend 서버 중지
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID"
        log_success "Backend 서버 종료됨 (PID: $BACKEND_PID)"
    else
        log_info "Backend 서버가 이미 종료되어 있습니다."
    fi
    rm -f "$BACKEND_PID_FILE"
else
    log_info "Backend PID 파일이 없습니다."
fi

# Frontend 서버 중지
if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID"
        log_success "Frontend 서버 종료됨 (PID: $FRONTEND_PID)"
    else
        log_info "Frontend 서버가 이미 종료되어 있습니다."
    fi
    rm -f "$FRONTEND_PID_FILE"
else
    log_info "Frontend PID 파일이 없습니다."
fi

# PID 디렉토리 정리
if [ -d "$PID_DIR" ]; then
    rmdir "$PID_DIR" 2>/dev/null || true
fi

echo ""
log_success "모든 서버가 중지되었습니다."
