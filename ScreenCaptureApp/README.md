# Screen Capture App

실시간 화면 캡쳐, 전송 및 웹 뷰어 시스템

## 프로젝트 구조

```
ScreenCaptureApp/
├── android/          # Android Kotlin 앱
│   └── app/
│       ├── MainActivity.kt
│       └── service/
│           └── ScreenCaptureService.kt
├── backend/          # FastAPI 백엔드
│   ├── main.py
│   ├── static/
│   │   ├── viewer.html
│   │   └── viewer.js
│   └── uploads/
└── SETUP_GUIDE.md   # 상세 설치 가이드
```

## 주요 기능

### 안드로이드 앱
- 📱 백그라운드에서 실시간 화면 캡쳐
- 🔄 설정 가능한 캡쳐 간격 (100ms~)
- 📤 자동 이미지 압축 및 서버 전송
- 🔔 Foreground Service로 안정적 실행

### 백엔드 서버
- 🌐 실시간 웹 뷰어 (WebSocket 기반)
- 🎬 히스토리 타임라인으로 과거 화면 재생
- 🔴 LIVE 모드 자동 업데이트
- 📊 통계 및 관리 대시보드
- 🗂️ 이미지 저장 및 관리

## 빠른 시작

### 1. Backend 서버 실행
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 2. 웹 뷰어 접속
브라우저에서: `http://localhost:8000/viewer`

### 3. Android 앱 실행
1. Android Studio로 `android/` 프로젝트 열기
2. 빌드 및 실행
3. 서버 URL 입력: `http://[서버IP]:8000`
4. 캡쳐 시작

## 상세 가이드

모든 설치 및 사용 방법은 [SETUP_GUIDE.md](SETUP_GUIDE.md)를 참고하세요.

## 스크린샷

**웹 뷰어**
- 실시간 화면 모니터링
- 타임라인 슬라이더로 과거 화면 탐색
- 재생/일시정지 컨트롤
- 통계 대시보드

## 기술 스택

- **Android**: Kotlin, MediaProjection API, Retrofit, Coroutines
- **Backend**: FastAPI, WebSocket, Uvicorn
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
