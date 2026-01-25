#!/bin/bash
# AIRClass - Unified CLI Interface (Cross-platform)
# Windows users: Use airclass.bat instead

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_help() {
    cat << EOF
AIRClass - 실시간 온라인 교실 플랫폼

사용법: ./airclass.sh <command>

주요 명령어:
  install     초기 설치 및 설정
  start       서버 시작
  stop        서버 중지
  restart     서버 재시작
  logs        로그 확인
  status      서버 상태 확인

개발 명령어:
  dev         개발 모드로 시작
  dev-stop    개발 서버 중지
  test        테스트 실행
  clean       임시 파일 정리

도움말:
  help        이 메시지 출력

EOF
}

case "${1:-help}" in
    install)
        echo "🚀 AIRClass 설치 시작..."
        bash scripts/install/setup.sh
        ;;
    start)
        echo "▶️  AIRClass 시작..."
        bash scripts/start.sh
        ;;
    stop)
        echo "⏹️  AIRClass 중지..."
        bash scripts/stop.sh
        ;;
    restart)
        echo "🔄 AIRClass 재시작..."
        bash scripts/stop.sh
        sleep 2
        bash scripts/start.sh
        ;;
    logs)
        bash scripts/logs.sh
        ;;
    status)
        bash scripts/dev/status.sh
        ;;
    dev)
        echo "🔧 개발 모드로 시작..."
        bash scripts/dev/start-dev.sh
        ;;
    dev-stop)
        echo "🔧 개발 서버 중지..."
        bash scripts/dev/stop-dev.sh
        ;;
    test)
        echo "🧪 테스트 실행..."
        cd backend && python -m pytest tests/ -v
        ;;
    clean)
        echo "🧹 임시 파일 정리..."
        rm -rf backend/__pycache__ backend/.pytest_cache
        rm -rf frontend/dist frontend/.svelte-kit
        rm -rf logs/*.log
        find . -name "*.pyc" -delete
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        echo "✅ 정리 완료"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ 알 수 없는 명령어: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
