# AIRClass

**AI Interactive Responsive Class** - 인공지능 기반 양방향 스마트 교실

## 프로젝트 개요

AIRClass는 **AI 기반 양방향 교육 환경을 위한 실시간 화면 공유 시스템**입니다. Android 기기의 화면을 무선으로 캡쳐하여 웹 브라우저에서 실시간으로 모니터링할 수 있으며, 교사와 학생 간의 원활한 화면 공유를 지원합니다.

### AIRClass의 의미
- **AI Interactive Responsive Class**
- **AI**: 인공지능 기반 스마트 교육
- **Interactive**: 양방향 실시간 소통
- **Responsive**: 반응형 다중 디바이스 지원
- **Class**: 교실 환경 최적화

### 주요 사용 사례
- 📚 **교육**: 교사의 태블릿 화면을 학생들에게 실시간 공유
- 💼 **프레젠테이션**: 무선으로 스마트폰 화면 시연
- 🔍 **모니터링**: 원격지 Android 기기 화면 관찰
- 🎮 **데모**: 앱 시연 및 사용법 안내

## 프로젝트 구조

```
AIRClass/
├── android/                            # Android 클라이언트 앱
│   ├── app/
│   │   └── src/main/java/com/example/screencapture/
│   │       ├── MainActivity.kt
│   │       └── service/ScreenCaptureService.kt
│   └── build.gradle.kts
│
├── backend/                            # FastAPI 백엔드 서버
│   ├── main.py                         # 메인 서버
│   ├── streaming_server.py             # 스트리밍 서버
│   ├── webrtc_web_server.py           # WebRTC 서버
│   ├── static_streaming/               # 레거시 웹 뷰어 HTML
│   ├── stream/                         # HLS 스트림 세그먼트
│   └── requirements.txt
│
├── frontend/                           # Svelte 프론트엔드 (신규)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Teacher.svelte         # 👨‍🏫 교사용 대시보드
│   │   │   ├── Student.svelte         # 🎓 학생용 뷰어
│   │   │   └── Monitor.svelte         # 📺 모니터 전용 뷰어
│   │   ├── components/                # 재사용 컴포넌트
│   │   └── App.svelte                 # 메인 앱 (라우팅)
│   ├── package.json
│   └── vite.config.js
│
├── docs/                               # 문서
│   ├── README.md                       # 상세 프로젝트 설명
│   ├── SETUP_GUIDE.md                 # 설치 가이드
│   ├── TESTING_GUIDE.md               # 테스트 가이드
│   ├── PERFORMANCE_TESTING_GUIDE.md   # 성능 테스트 가이드
│   ├── README_WebRTC.md               # WebRTC 통합 가이드
│   └── NEXT_STEPS.md                  # 개발 로드맵
│
├── README.md                           # 프로젝트 개요 (이 파일)
├── LICENSE                             # GPL-3.0 라이선스
└── .gitignore                          # Git 제외 파일
```

## 주요 기능

### Android 클라이언트
- 📱 백그라운드 화면 캡쳐 (MediaProjection API)
- 🔄 설정 가능한 캡쳐 주기 (최소 100ms)
- 📤 자동 이미지 압축 및 서버 전송
- 🔔 Foreground Service 기반 안정적 실행

### 백엔드 서버
- 🌐 실시간 WebSocket 통신
- 🎬 히스토리 타임라인 및 재생 기능
- 🔴 LIVE 모드 자동 업데이트
- 📊 통계 및 관리 대시보드
- 🗂️ 이미지 저장 및 관리

### 프론트엔드 (Svelte)
- 👨‍🏫 **Teacher 페이지**: 화면 미리보기, 학생 목록, 실시간 채팅
- 🎓 **Student 페이지**: 교사 화면 시청, 질문/답변 채팅
- 📺 **Monitor 페이지**: 전체화면 모니터링 전용 뷰어
- ⚡ 빠른 반응속도와 모던 UI/UX
- 📱 반응형 디자인 (모바일/태블릿/데스크톱)

## 빠른 시작

### 개발 환경 설정

**필요한 도구:**
- Python 3.8 이상
- Node.js 16 이상
- Android Studio (앱 개발용)

### 1. Backend 서버 실행 (터미널 1)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

서버가 `http://localhost:8000`에서 실행됩니다.

### 2. Frontend 실행 (터미널 2)

```bash
cd frontend
npm install
npm run dev
```

프론트엔드가 `http://localhost:5173`에서 실행됩니다.

**접속 URL:**
- 교사용: http://localhost:5173/#/teacher
- 학생용: http://localhost:5173/#/student
- 모니터: http://localhost:5173/#/monitor

### 3. Android 앱 실행

1. Android Studio로 `android/` 프로젝트 열기
2. 빌드 및 디바이스/에뮬레이터에 설치
3. 앱 실행 후 서버 URL 입력: `http://[서버IP]:8000`
4. 권한 허용 후 화면 캡쳐 시작

> 📖 더 자세한 개발 서버 실행 방법은 [DEV_SERVER.md](DEV_SERVER.md)를 참고하세요.

## 상세 문서

- [설치 가이드](docs/SETUP_GUIDE.md) - 상세한 설치 및 설정 방법
- [테스트 가이드](docs/TESTING_GUIDE.md) - 테스트 방법 및 절차
- [성능 테스트 가이드](docs/PERFORMANCE_TESTING_GUIDE.md) - 성능 측정 및 최적화
- [WebRTC 가이드](docs/README_WebRTC.md) - WebRTC 통합 방법
- [향후 계획](docs/NEXT_STEPS.md) - 개발 로드맵

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
- **프레임워크**: Svelte 5 + Vite
- **스타일링**: Tailwind CSS
- **라우팅**: svelte-spa-router
- **실시간 통신**: WebSocket API
- **빌드 도구**: Vite

## 시스템 요구사항

### Android 앱
- Android 5.0 (API 21) 이상
- 화면 캡쳐 권한 (MediaProjection)

### 백엔드 서버
- Python 3.8 이상
- 최소 1GB RAM
- 이미지 저장을 위한 충분한 디스크 공간

## 라이선스

이 프로젝트는 **GNU General Public License v3.0 (GPL-3.0)** 라이선스 하에 배포됩니다.

### 주요 조건
- ✅ **자유로운 사용**: 개인, 교육, 연구 목적으로 자유롭게 사용 가능
- ✅ **소스코드 공개**: 이 프로그램을 수정하거나 배포할 경우 소스코드를 반드시 공개해야 합니다
- ✅ **동일 라이선스 적용**: 파생 작업물도 GPL-3.0 라이선스를 따라야 합니다
- ❌ **상업적 이용 시 제약**: 상업적으로 이용할 경우에도 소스코드를 공개해야 하며 동일한 라이선스를 적용해야 합니다
- ⚠️ **무보증**: 이 소프트웨어는 "있는 그대로" 제공되며, 어떠한 보증도 제공하지 않습니다

자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

### 상업적 이용 관련
이 프로젝트를 상업적으로 이용하려는 경우, GPL-3.0 라이선스 조건을 준수해야 합니다. 즉, 파생 소프트웨어의 소스코드를 공개하고 동일한 라이선스를 적용해야 합니다.

## 기여

이슈 및 개선 사항은 프로젝트 관리자에게 문의해주세요.

### 기여 방법
1. 이 저장소를 Fork합니다
2. 새로운 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`)
4. 브랜치에 Push합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

모든 기여는 GPL-3.0 라이선스 하에 배포됩니다.
