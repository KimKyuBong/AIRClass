# Screen Capture Backend

FastAPI 기반 스크린샷 수신 서버 + 실시간 웹 뷰어

## 기능

- 📱 안드로이드 앱으로부터 스크린샷 수신
- 🌐 실시간 웹 뷰어 (WebSocket)
- 🎬 히스토리 재생 (타임라인 슬라이더)
- 🔴 LIVE 모드 자동 업데이트
- 📊 통계 및 관리 기능

## 설치 (uv 사용)

```bash
# uv 설치 (없는 경우): https://docs.astral.sh/uv/
# curl -LsSf https://astral.sh/uv/install.sh | sh

cd backend
uv sync   # .venv 생성 + 의존성 설치
```

## 실행

```bash
# uv로 실행 (권장)
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 또는
uv run python main.py
```

서버 실행 후:
- 웹 뷰어: `http://localhost:8000/viewer`
- API 문서: `http://localhost:8000/docs`

## 간단 부하 테스트 (AI)

```bash
# /api/ai/health 엔드포인트를 병렬로 호출합니다
python load_test_ai.py --base-url http://localhost:8000 --concurrency 20 --requests 200
```

## 웹 뷰어 사용법

### 접속
브라우저에서 `http://[서버IP]:8000/viewer` 접속

### 주요 기능

**실시간 모드 (LIVE)**
- 새 스크린샷이 업로드되면 자동으로 표시
- 우측 상단 "LIVE" 표시등이 깜박임

**히스토리 재생**
- 타임라인 슬라이더로 과거 이미지 탐색
- 재생 버튼으로 자동 재생 (1초 간격)
- 이전/다음 버튼으로 수동 탐색

**키보드 단축키**
- `←` : 이전 이미지
- `→` : 다음 이미지
- `Space` : 재생/일시정지
- `L` : LIVE 모드로 전환

## API 엔드포인트

### REST API
- `GET /` - 헬스체크
- `GET /viewer` - 웹 뷰어 페이지
- `POST /upload` - 스크린샷 업로드
- `GET /uploads/list` - 업로드된 이미지 목록
- `GET /uploads/count` - 저장된 스크린샷 개수
- `DELETE /uploads/clear` - 모든 스크린샷 삭제
- `GET /uploads/{filename}` - 이미지 파일 다운로드

### WebSocket
- `WS /ws` - 실시간 스크린샷 스트리밍

## 디렉토리 구조

```
backend/
├── main.py              # FastAPI 서버
├── requirements.txt     # Python 의존성
├── static/             # 정적 파일
│   ├── viewer.html     # 웹 뷰어 UI
│   └── viewer.js       # 뷰어 JavaScript
└── uploads/            # 업로드된 스크린샷 (자동 생성)
```

## 사용 예시

```bash
# 헬스체크
curl http://localhost:8000/

# 파일 업로드 테스트
curl -X POST -F "file=@test.jpg" http://localhost:8000/upload

# 업로드 개수 확인
curl http://localhost:8000/uploads/count

# 이미지 목록 조회
curl http://localhost:8000/uploads/list
```

## 설정

- 업로드 디렉토리: `uploads/` (자동 생성)
- 정적 파일 디렉토리: `static/` (자동 생성)
- 포트: 8000
- 호스트: 0.0.0.0 (모든 인터페이스에서 접근 가능)

## 네트워크 설정

같은 WiFi에 연결된 디바이스에서 접속하려면:

1. 서버 IP 확인:
```bash
# macOS/Linux
ifconfig | grep "inet "
# Windows
ipconfig
```

2. 브라우저에서 접속:
```
http://[서버IP]:8000/viewer
```

예: `http://192.168.1.100:8000/viewer`
