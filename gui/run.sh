#!/bin/bash
# 프로젝트 루트의 .venv만 사용 (다른 경로에서 실행해도 동일 동작)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ ! -d ".venv" ]; then
  echo "가상환경이 없습니다. 생성 후 설치합니다..."
  python3 -m venv .venv
fi
"$ROOT/.venv/bin/pip" install -q -r gui/requirements.txt
exec "$ROOT/.venv/bin/python" gui/airclass_gui.py
