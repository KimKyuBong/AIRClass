# AirClass Backend 개발 환경 설정 (uv 사용)

## 📦 uv란?

**uv**는 Rust로 작성된 초고속 Python 패키지 관리자입니다.
- pip보다 **10-100배 빠름**
- pyproject.toml 네이티브 지원
- 자동 가상환경 관리
- lock 파일 지원

공식 문서: https://github.com/astral-sh/uv

## 🚀 빠른 시작

### 1. uv 설치

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# pip으로 설치 (fallback)
pip install uv
```

### 2. 프로젝트 의존성 설치

```bash
cd backend

# 프로덕션 의존성만 설치
uv sync

# 개발 의존성 포함 (pytest, ruff, mypy 등)
uv sync --dev

# 또는 수동으로 설치
uv pip install -e .
uv pip install -e ".[dev]"
```

### 3. 서버 실행

```bash
# uv로 직접 실행 (가상환경 자동 활성화)
uv run uvicorn main:app --reload

# 또는 가상환경 활성화 후 실행
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows
python main.py
```

## 🔧 일반적인 작업

### 패키지 추가

```bash
# 프로덕션 의존성 추가
uv add fastapi

# 개발 의존성 추가
uv add --dev pytest

# 특정 버전 설치
uv add "fastapi>=0.109.0"
```

### 패키지 제거

```bash
uv remove fastapi
```

### 패키지 업데이트

```bash
# 모든 패키지 업데이트
uv sync --upgrade

# 특정 패키지만 업데이트
uv add --upgrade fastapi
```

### Lock 파일 관리

```bash
# uv.lock 생성/업데이트 (자동으로 생성됨)
uv sync

# lock 파일 기반으로 정확히 재현
uv sync --locked
```

### 가상환경 관리

```bash
# 가상환경 생성 (자동)
uv venv

# 특정 Python 버전 사용
uv venv --python 3.11

# 가상환경 삭제
rm -rf .venv
```

## 🧪 테스트 실행

```bash
# pytest 실행
uv run pytest

# 커버리지 포함
uv run pytest --cov=core --cov=routers

# 특정 테스트 파일만
uv run pytest tests/test_cluster.py
```

## 🎨 코드 품질 도구

```bash
# Ruff로 린팅
uv run ruff check .

# Ruff로 포맷팅
uv run ruff format .

# Mypy로 타입 체크
uv run mypy core/ routers/ services/
```

## 📋 requirements.txt와의 호환

### pyproject.toml → requirements.txt 생성

```bash
# 프로덕션 의존성만
uv pip compile pyproject.toml -o requirements.txt

# 개발 의존성 포함
uv pip compile pyproject.toml --extra dev -o requirements-dev.txt
```

### requirements.txt → pyproject.toml 변환

```bash
# requirements.txt를 읽어서 설치
uv pip install -r requirements.txt

# pyproject.toml에 추가하려면 수동 작업 필요
# (uv add 명령어 사용 권장)
```

## 🐳 Docker에서 uv 사용

현재 `backend/Dockerfile`은 이미 uv를 사용하고 있습니다:

```dockerfile
# uv 설치
RUN pip install --no-cache-dir uv

# 의존성 설치
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt
```

### pyproject.toml 기반으로 변경하려면:

```dockerfile
# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치 (lock 파일 기반)
RUN uv sync --frozen --no-dev

# 애플리케이션 복사
COPY . .
```

## 🔄 기존 프로젝트 마이그레이션

### Step 1: pyproject.toml 확인

`backend/pyproject.toml`이 이미 존재하므로 바로 사용 가능합니다.

### Step 2: uv.lock 생성

```bash
cd backend
uv sync
```

`uv.lock` 파일이 생성되며, 이것을 Git에 커밋하면 팀원들이 동일한 환경을 재현할 수 있습니다.

### Step 3: requirements.txt 제거 (선택)

`uv.lock`을 사용하면 `requirements.txt`가 불필요합니다.
단, Docker 빌드나 CI/CD 호환성을 위해 유지할 수도 있습니다.

```bash
# requirements.txt 업데이트 (필요시)
uv pip compile pyproject.toml -o requirements.txt
```

## 💡 팁과 트릭

### 빠른 설치 (캐시 활용)

```bash
# 로컬 캐시 확인
uv cache dir

# 캐시 정리 (디스크 공간 확보)
uv cache clean
```

### 스크립트 실행

```bash
# main.py 실행
uv run python main.py

# 환경변수 포함
MODE=standalone uv run python main.py
```

### 의존성 트리 확인

```bash
# pip-tree 스타일 출력
uv tree
```

## 🆚 pip vs uv 비교

| 기능 | pip | uv |
|------|-----|-----|
| 설치 속도 | 느림 | **10-100배 빠름** |
| 의존성 해결 | 느림 | 병렬 처리 |
| Lock 파일 | pip-tools 필요 | 네이티브 지원 |
| 가상환경 | venv 수동 생성 | 자동 생성 |
| pyproject.toml | 부분 지원 | 완전 지원 |

## 📚 추가 자료

- [uv 공식 문서](https://docs.astral.sh/uv/)
- [uv vs pip 벤치마크](https://github.com/astral-sh/uv#benchmarks)
- [pyproject.toml 가이드](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

## ❓ 문제 해결

### "uv: command not found"

```bash
# PATH 확인
echo $PATH | grep .local/bin

# 없으면 추가 (macOS/Linux)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 가상환경 충돌

```bash
# 기존 venv 삭제
rm -rf .venv

# uv로 재생성
uv venv
uv sync
```

### Lock 파일 충돌

```bash
# lock 파일 무시하고 재생성
rm uv.lock
uv sync
```
