# AirClass

실시간 화면 캡쳐 및 스트리밍 시스템

## 프로젝트 개요

AirClass는 Android 기기의 화면을 실시간으로 캡쳐하여 웹 브라우저에서 모니터링할 수 있는 통합 솔루션입니다.

## 프로젝트 구조

```
AirClass/
└── ScreenCaptureApp/     # 화면 캡쳐 애플리케이션
    ├── android/          # Android 클라이언트 앱 (Kotlin)
    ├── backend/          # FastAPI 백엔드 서버
    └── 문서/
        ├── README.md                      # 프로젝트 개요
        ├── SETUP_GUIDE.md                # 설치 가이드
        ├── TESTING_GUIDE.md              # 테스트 가이드
        ├── PERFORMANCE_TESTING_GUIDE.md  # 성능 테스트 가이드
        ├── README_WebRTC.md              # WebRTC 통합 가이드
        └── NEXT_STEPS.md                 # 향후 개발 계획
```

## 주요 기능

### Android 클라이언트
- 📱 백그라운드 화면 캡쳐 (MediaProjection API)
- 🔄 설정 가능한 캡쳐 주기 (최소 100ms)
- 📤 자동 이미지 압축 및 서버 전송
- 🔔 Foreground Service 기반 안정적 실행

### 백엔드 서버
- 🌐 실시간 웹 뷰어 (WebSocket)
- 🎬 히스토리 타임라인 및 재생 기능
- 🔴 LIVE 모드 자동 업데이트
- 📊 통계 및 관리 대시보드
- 🗂️ 이미지 저장 및 관리

## 빠른 시작

### 1. 백엔드 서버 실행

```bash
cd ScreenCaptureApp/backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 2. 웹 뷰어 접속

브라우저에서 `http://localhost:8000/viewer` 접속

### 3. Android 앱 실행

1. Android Studio로 `ScreenCaptureApp/android/` 프로젝트 열기
2. 빌드 및 디바이스/에뮬레이터에 설치
3. 앱 실행 후 서버 URL 입력: `http://[서버IP]:8000`
4. 권한 허용 후 화면 캡쳐 시작

## 상세 문서

- [설치 가이드](ScreenCaptureApp/SETUP_GUIDE.md) - 상세한 설치 및 설정 방법
- [테스트 가이드](ScreenCaptureApp/TESTING_GUIDE.md) - 테스트 방법 및 절차
- [성능 테스트 가이드](ScreenCaptureApp/PERFORMANCE_TESTING_GUIDE.md) - 성능 측정 및 최적화
- [WebRTC 가이드](ScreenCaptureApp/README_WebRTC.md) - WebRTC 통합 방법
- [향후 계획](ScreenCaptureApp/NEXT_STEPS.md) - 개발 로드맵

## 기술 스택

### Android 클라이언트
- **언어**: Kotlin
- **주요 라이브러리**: 
  - MediaProjection API
  - Retrofit (HTTP 클라이언트)
  - Coroutines (비동기 처리)

### 백엔드
- **프레임워크**: FastAPI
- **통신**: WebSocket, REST API
- **서버**: Uvicorn

### 프론트엔드
- **기술**: Vanilla JavaScript, HTML5, CSS3
- **실시간 통신**: WebSocket API

## 시스템 요구사항

### Android 앱
- Android 5.0 (API 21) 이상
- 화면 캡쳐 권한 (MediaProjection)

### 백엔드 서버
- Python 3.8 이상
- 최소 1GB RAM
- 이미지 저장을 위한 충분한 디스크 공간

## 라이선스

이 프로젝트는 교육 목적으로 개발되었습니다.

## 기여

이슈 및 개선 사항은 프로젝트 관리자에게 문의해주세요.
