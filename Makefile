# AIRClass - Unified Management Interface
# Usage: make <command>

.PHONY: help install start stop logs status clean dev test

help:
	@echo "AIRClass - 실시간 온라인 교실 플랫폼"
	@echo ""
	@echo "사용법: make <command>"
	@echo ""
	@echo "주요 명령어:"
	@echo "  make install    - 초기 설치 및 설정"
	@echo "  make start      - 서버 시작"
	@echo "  make stop       - 서버 중지"
	@echo "  make logs       - 로그 확인"
	@echo "  make status     - 서버 상태 확인"
	@echo ""
	@echo "개발 명령어:"
	@echo "  make dev        - 개발 모드로 시작"
	@echo "  make test       - 테스트 실행"
	@echo "  make clean      - 임시 파일 정리"
	@echo ""

install:
	@echo "🚀 AIRClass 설치 시작..."
	@bash scripts/install/setup.sh

start:
	@echo "▶️  AIRClass 시작..."
	@bash scripts/start.sh

stop:
	@echo "⏹️  AIRClass 중지..."
	@bash scripts/stop.sh

logs:
	@bash scripts/logs.sh

status:
	@bash scripts/dev/status.sh

dev:
	@echo "🔧 개발 모드로 시작..."
	@bash scripts/dev/start-dev.sh

dev-stop:
	@echo "🔧 개발 서버 중지..."
	@bash scripts/dev/stop-dev.sh

test:
	@echo "🧪 테스트 실행 (uv)..."
	@cd backend && uv run pytest tests/ -v

clean:
	@echo "🧹 임시 파일 정리..."
	@rm -rf backend/__pycache__ backend/.pytest_cache backend/.venv
	@rm -rf frontend/dist frontend/.svelte-kit
	@rm -rf logs/*.log
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 정리 완료"

# Windows users: Use scripts/start.bat, scripts/stop.bat directly
