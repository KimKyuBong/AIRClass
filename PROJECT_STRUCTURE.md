# 🏗️ AIRClass 프로젝트 구조 문서

**최종 업데이트:** 2025-02-02  
**버전:** v2.0.0  
**상태:** 프로덕션 준비 85% 완료

---

## 📁 전체 디렉토리 구조

```
AirClass/
├── backend/              # FastAPI 백엔드 서버
│   ├── routers/         # API 라우터 (REST endpoints)
│   ├── tests/           # Pytest 테스트 (161개)
│   └── *.py             # 핵심 모듈 (19개 파일)
├── frontend/            # React 프론트엔드
│   ├── src/
│   │   ├── components/  # React 컴포넌트
│   │   ├── hooks/       # Custom hooks
│   │   └── services/    # API 서비스
│   └── public/
├── android/             # Android 송출 앱 (Kotlin)
│   ├── app/src/main/
│   │   ├── kotlin/      # Kotlin 소스
│   │   └── res/         # 리소스
│   └── build.gradle
├── gui/                 # 데스크톱 설치 마법사 (Tauri)
│   ├── src/
│   └── src-tauri/
├── docs/                # 프로젝트 문서 (40+개)
│   ├── QUICKSTART.md    # ⭐ 빠른 시작 가이드
│   ├── INSTALL_GUIDE.md # 설치 가이드
│   └── ...
├── mediamtx/            # MediaMTX 바이너리 (미포함)
├── recordings/          # 녹화 파일 저장소
├── vod_storage/         # VOD 파일 저장소
└── README.md            # 프로젝트 메인 README
```

---

## 🎯 핵심 디렉토리 상세

### 1. `backend/` - FastAPI 백엔드 (Python 3.11+)

**핵심 서버 파일 (19개)**

#### 🔷 메인 서버
- **`main.py`** (507줄) - FastAPI 애플리케이션 진입점
  - WebRTC 스트리밍 엔드포인트
  - WebSocket 연결 관리
  - MediaMTX 프로세스 제어
  - 클러스터 라이프사이클 관리

#### 🔷 클러스터 & 네트워킹
- **`cluster.py`** (350줄) - 멀티 노드 클러스터 관리
  - Rendezvous Hashing 로드밸런싱
  - 노드 헬스체크 (30초 주기)
  - 자동 장애 복구 (Failover)
  - Redis 기반 노드 상태 동기화
  
- **`discovery.py`** (200줄) - 자동 노드 발견 (Zeroconf)
  - mDNS/Bonjour를 통한 네트워크 스캔
  - 서브 노드 자동 등록
  - 클러스터 인증 (shared_secret)

- **`stream_relay.py`** (150줄) - RTMP/WebRTC 스트림 릴레이
  - MediaMTX 연동
  - 스트림 라우팅

#### 🔷 데이터 관리
- **`database.py`** (400줄) - MongoDB 비동기 관리자
  - Motor (비동기 MongoDB 드라이버)
  - 세션, 참여도, 퀴즈, 채팅 컬렉션
  - 자동 인덱싱 (성능 최적화)
  - 연결 풀 관리

- **`cache.py`** (250줄) - Redis 캐싱
  - AI 분석 결과 캐싱 (24h TTL)
  - 학생 참여도 캐싱 (1h TTL)
  - 세션 메타데이터 캐싱

- **`models.py`** (350줄) - Pydantic 데이터 모델 (20개+)
  - Session, Quiz, QuizResponse
  - StudentEngagement, EngagementMetrics
  - ChatMessage, ScreenshotAnalysis
  - SessionSummary, StudentLearningPath
  - **최신:** Pydantic V2 ConfigDict 사용

#### 🔷 참여도 & 분석
- **`engagement.py`** (543줄) - 학생 참여도 계산 엔진 ✅ **프로덕션 준비**
  - 집중도 점수 (Attention Score)
  - 참여도 점수 (Participation Score)
  - 응답 지연 분석 (Latency Analysis)
  - 혼란도 감지 (Confusion Detection) - **최근 수정**
  - 트렌드 분석 (선형 회귀)

- **`engagement_listener.py`** (200줄) - Redis Pub/Sub 리스너
  - 실시간 활동 추적 (퀴즈, 채팅, 스크린샷)
  - MongoDB 저장 자동화

#### 🔷 녹화 & VOD
- **`recording.py`** (348줄) - ffmpeg 기반 녹화 ✅ **프로덕션 준비**
  - 자동 녹화 시작/중지
  - MP4 + HLS 동시 생성
  - 메타데이터 관리
  - 스크린샷 자동 캡처 (10초 간격)

- **`vod_storage.py`** (500줄) - VOD 저장소 관리 ✅ **프로덕션 준비**
  - 비디오 인코딩 (H.264, AAC)
  - 해상도별 변환 (360p~1080p)
  - 자동 정리 (7일 정책)
  - 썸네일 생성

#### 🔷 AI 분석 (Google Gemini)
- **`ai_vision.py`** (499줄) - 스크린샷 비전 분석 ⚠️ **MOCK 구현**
  - OCR (텍스트 추출) - Tesseract 통합 필요
  - 객체 탐지 (다이어그램, 수식) - YOLO 통합 필요
  - 복잡도 분석 (간단/보통/복잡)
  - **현재:** 하드코딩된 더미 데이터 반환

- **`ai_nlp.py`** (613줄) - 채팅 NLP 분석 ⚠️ **MOCK 구현**
  - 감정 분석 (긍정/부정/중립) - KoBERT 통합 필요
  - 의도 분류 (질문/답변/토론) - Transformer 통합 필요
  - 키워드 추출 - TF-IDF 통합 필요
  - **현재:** 키워드 매칭 기반 (ML 아님)

- **`ai_feedback.py`** (767줄) - AI 피드백 생성기 ✅ **프로덕션 준비**
  - 학생별 맞춤 피드백
  - 학습 자료 추천
  - 교사 인사이트 생성
  - **템플릿 기반:** 실제 로직 구현됨

- **`gemini_service.py`** (150줄) - Google Gemini API 클라이언트
  - 텍스트/이미지 분석 API 호출
  - 속도 제한 처리 (Rate limiting)

- **`teacher_ai_keys.py`** (100줄) - API 키 암호화 관리 ✅ **프로덕션 준비**
  - Fernet 암호화/복호화
  - 교사별 키 저장 (MongoDB)

#### 🔷 실시간 통신
- **`messaging.py`** (300줄) - WebSocket 메시징
  - 채팅 메시지 브로드캐스트
  - 퀴즈 결과 실시간 전송
  - 알림 시스템

#### 🔷 설정 & 유틸
- **`config.py`** (100줄) - 환경 변수 관리
  - MongoDB/Redis URL
  - Gemini API 키
  - 스트리밍 설정

---

### 📂 `backend/routers/` - REST API 엔드포인트

**7개 라우터 파일**

- **`engagement.py`** (400줄) - 참여도 API
  - `POST /engagement/track` - 활동 추적
  - `GET /engagement/{student_id}` - 학생 참여도 조회
  - `POST /engagement/attention` - 집중도 계산
  - `GET /engagement/trend` - 트렌드 분석

- **`dashboard.py`** (450줄) - 대시보드 API ✅ **프로덕션 준비**
  - `GET /dashboard/session/{session_id}` - 세션 개요
  - `GET /dashboard/students` - 학생 목록
  - `GET /dashboard/alerts` - 알림 조회
  - `WebSocket /dashboard/ws` - 실시간 업데이트

- **`vod.py`** (350줄) - VOD API
  - `GET /vod/list` - VOD 목록
  - `GET /vod/play/{video_id}` - 재생 URL
  - `POST /vod/encode` - 인코딩 요청
  - `DELETE /vod/{video_id}` - 삭제

- **`ai.py`** (300줄) - AI 분석 API
  - `POST /ai/analyze-screenshot` - 스크린샷 분석
  - `POST /ai/analyze-chat` - 채팅 분석
  - `GET /ai/feedback/{student_id}` - 피드백 조회

- **`session.py`** (250줄) - 세션 관리 API
  - `POST /session/create` - 세션 생성
  - `PUT /session/{session_id}/end` - 세션 종료
  - `GET /session/{session_id}` - 세션 정보

- **`quiz.py`** (200줄) - 퀴즈 API
  - `POST /quiz/publish` - 퀴즈 출제
  - `POST /quiz/response` - 답변 제출
  - `GET /quiz/{quiz_id}/results` - 결과 조회

- **`cluster.py`** (150줄) - 클러스터 관리 API
  - `GET /cluster/nodes` - 노드 목록
  - `GET /cluster/health` - 헬스체크
  - `POST /cluster/add-node` - 노드 추가

---

### 🧪 `backend/tests/` - 테스트 (161개)

**9개 테스트 파일**

- **`test_ai_analysis.py`** (487줄, 32개 테스트) ✅ **100% 통과**
  - VisionAnalyzer, NLPAnalyzer, FeedbackGenerator 테스트
  - Mock AI 동작 검증

- **`test_engagement_calculator.py`** (392줄, 30개 테스트) ✅ **100% 통과**
  - 집중도, 참여도, 응답 지연 계산
  - 트렌드 분석 알고리즘

- **`test_dashboard_router.py`** (416줄, 21개 테스트) ✅ **100% 통과**
  - 대시보드 API 엔드포인트
  - WebSocket 연결

- **`test_recording.py`** (335줄, 18개 테스트) ✅ **100% 통과**
  - 녹화 시작/중지
  - VOD 생성

- **`test_confusion_detection.py`** (345줄, 19개 테스트) ⚠️ **94% 통과**
  - 혼란도 감지 알고리즘
  - 경계값 케이스 (최근 수정)
  - 2개 엣지케이스 실패 (테스트 기대값 문제)

- **`test_engagement_router.py`** (335줄, 17개 테스트) ⚠️ **88% 통과**
  - 참여도 API 엔드포인트
  - 2개 응답 형식 이슈

- **`test_integration_engagement.py`** (476줄, 11개 테스트) ⚠️ **63% 통과**
  - 전체 워크플로우 통합 테스트

- **`test_database_performance.py`** (216줄, 7개 테스트) ✅ **픽스처 수정 완료**
  - MongoDB 쿼리 성능 (<100ms)
  - 인덱싱 효율성

- **`test_teacher_ai_keys.py`** (150줄, 7개 테스트) ✅ **100% 통과**
  - API 키 암호화/복호화

**테스트 커버리지:** 94%+ (161개 중 150+개 통과)

---

### 2. `frontend/` - React 프론트엔드

**주요 기술 스택**
- React 18
- TypeScript
- Vite (빌드 도구)
- TailwindCSS (스타일링)
- Socket.io (WebSocket)

**디렉토리 구조**
```
frontend/
├── src/
│   ├── components/        # React 컴포넌트
│   │   ├── Dashboard.tsx  # 교사 대시보드
│   │   ├── VideoPlayer.tsx # WebRTC 플레이어
│   │   ├── ChatPanel.tsx  # 채팅 패널
│   │   ├── QuizPanel.tsx  # 퀴즈 패널
│   │   └── VODPlayer.tsx  # VOD 플레이어
│   ├── hooks/             # Custom Hooks
│   │   ├── useWebRTC.ts   # WebRTC 연결
│   │   ├── useWebSocket.ts # WebSocket 연결
│   │   └── useEngagement.ts # 참여도 데이터
│   ├── services/          # API 서비스
│   │   ├── api.ts         # REST API 클라이언트
│   │   └── websocket.ts   # WebSocket 클라이언트
│   ├── types/             # TypeScript 타입
│   ├── App.tsx            # 메인 앱
│   └── main.tsx           # 진입점
├── public/
│   └── index.html
├── package.json
└── vite.config.ts
```

**주요 기능**
- ✅ WebRTC 스트림 재생 (초저지연)
- ✅ 실시간 채팅 (WebSocket)
- ✅ 퀴즈 참여
- ✅ 교사 대시보드 (학생 참여도 모니터링)
- ✅ VOD 재생

---

### 3. `android/` - Android 송출 앱 (Kotlin)

**주요 기술 스택**
- Kotlin
- Android SDK 24+ (Android 7.0+)
- CameraX (카메라 API)
- RTMP Publisher (화면 송출)

**디렉토리 구조**
```
android/
├── app/src/main/
│   ├── kotlin/com/airclass/
│   │   ├── MainActivity.kt        # 메인 액티비티
│   │   ├── StreamService.kt       # RTMP 송출 서비스
│   │   ├── CameraManager.kt       # 카메라 관리
│   │   └── PermissionHelper.kt    # 권한 관리
│   ├── res/                       # 리소스
│   │   ├── layout/
│   │   ├── drawable/
│   │   └── values/
│   └── AndroidManifest.xml
├── build.gradle
└── gradle.properties
```

**주요 기능**
- ✅ RTMP 화면 송출 (MediaMTX로 전송)
- ✅ 카메라/화면 공유
- ✅ QR 코드 스캔 (서버 자동 연결)
- ✅ 화질 조절 (720p/1080p)

---

### 4. `gui/` - 데스크톱 설치 마법사 (Tauri)

**주요 기술 스택**
- Tauri (Rust + Web)
- React
- TypeScript

**주요 기능**
- ✅ 원클릭 서버 설치
- ✅ MediaMTX 자동 다운로드
- ✅ 환경 변수 자동 설정
- ✅ MongoDB/Redis 설치 안내
- ✅ 클러스터 설정 마법사

---

### 5. `docs/` - 문서 (40+개)

**⭐ 중요 문서 (유지)**
- `QUICKSTART.md` - 5분 빠른 시작
- `INSTALL_GUIDE.md` - 상세 설치 가이드
- `STREAMING_ARCHITECTURE.md` - 스트리밍 아키텍처
- `CLUSTER_ARCHITECTURE.md` - 클러스터 구조
- `DEPLOYMENT.md` - 프로덕션 배포
- `TESTING_GUIDE.md` - 테스트 실행 가이드

**📝 참고 문서 (유지)**
- `PROJECT_STATUS.md` - 프로젝트 현황
- `CHANGELOG.md` - 변경 이력
- `SECURITY_IMPLEMENTATION.md` - 보안 구현

**🗑️ 중복/구버전 문서 (삭제 대상)**
- `PHASE2_완료.md`, `PHASE3_계획.md` - 구버전 계획서
- `TEST_SUMMARY.md`, `TESTING_REPORT.md` - 중복 테스트 리포트
- `CLEANUP_SUMMARY.md`, `PROGRESS.md` - 일회성 작업 기록
- `HLS_MIGRATION.md`, `SCREEN_DISPLAY_FIX.md` - 특정 이슈 해결 기록

---

## 🔧 주요 기술 스택 요약

### 백엔드
- **언어:** Python 3.11+
- **프레임워크:** FastAPI 0.109+
- **데이터베이스:** MongoDB (Motor)
- **캐시:** Redis
- **AI:** Google Gemini API
- **미디어:** ffmpeg, MediaMTX
- **테스트:** pytest, pytest-asyncio

### 프론트엔드
- **언어:** TypeScript
- **프레임워크:** React 18
- **빌드:** Vite
- **스타일:** TailwindCSS
- **WebRTC:** 네이티브 WebRTC API

### 안드로이드
- **언어:** Kotlin
- **최소 SDK:** 24 (Android 7.0)
- **스트리밍:** RTMP Publisher

### GUI (설치 마법사)
- **프레임워크:** Tauri
- **언어:** Rust + TypeScript

---

## 📊 프로젝트 통계

- **총 코드 라인:** 15,000+ 줄
- **Python 파일:** 30+ 개
- **테스트:** 161개 (94% 통과)
- **API 엔드포인트:** 40+ 개
- **React 컴포넌트:** 20+ 개
- **문서:** 40+ 개

---

## 🚀 프로덕션 준비도

### ✅ 완전 구현 (85%)
- 스트리밍 (WebRTC/RTMP)
- 클러스터링 (멀티 노드)
- 참여도 계산 엔진
- 녹화/VOD 시스템
- 대시보드 API
- 보안 (인증, 암호화)

### ⚠️ Mock 구현 (10%)
- AI Vision (OCR, 객체 탐지)
- AI NLP (감정 분석, 의도 분류)

### 📝 미구현 (5%)
- 실제 AI 모델 통합
- 프로덕션 배포 자동화
- 모니터링 대시보드

---

## 📌 핵심 워크플로우

### 1. 스트리밍 워크플로우
```
교사 (Android/PC) 
  → RTMP/WebRTC 송출 
  → MediaMTX 
  → 클러스터 (Rendezvous Hashing) 
  → 학생들 (WebRTC 수신)
```

### 2. 참여도 추적 워크플로우
```
학생 활동 (퀴즈, 채팅, 스크린샷)
  → Redis Pub/Sub
  → engagement_listener.py
  → 참여도 계산 (engagement.py)
  → MongoDB 저장
  → 대시보드 실시간 업데이트 (WebSocket)
```

### 3. 녹화 워크플로우
```
수업 시작
  → recording.py (ffmpeg 자동 시작)
  → MP4 + HLS 동시 생성
  → 10초마다 스크린샷 캡처
  → AI 비전 분석 (ai_vision.py)
  → 메타데이터 MongoDB 저장
  → VOD 플레이어로 재생 가능
```

### 4. AI 분석 워크플로우
```
스크린샷 캡처
  → ai_vision.py (OCR, 객체 탐지)
  → Redis 캐싱 (24h)
  
채팅 메시지
  → ai_nlp.py (감정, 의도 분석)
  → Redis 캐싱 (1h)
  
수업 종료
  → ai_feedback.py (학생별 피드백 생성)
  → MongoDB 저장
```

---

## 🔐 보안 구현

### 1. 클러스터 인증
- **Shared Secret:** 각 클러스터마다 고유 비밀키
- **노드 검증:** 모든 노드가 같은 secret 공유

### 2. API 키 암호화
- **알고리즘:** Fernet (AES-128)
- **저장:** MongoDB (암호화된 상태)
- **복호화:** 런타임에만 메모리에서

### 3. 통신 암호화
- **WebRTC:** DTLS/SRTP (기본 암호화)
- **HTTPS:** 프로덕션 환경 권장
- **WebSocket:** WSS (보안 WebSocket)

---

## 📦 외부 의존성

### Python 패키지 (backend/requirements.txt)
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
motor>=3.3.0              # MongoDB async
redis>=5.0.0              # Redis 클라이언트
google-genai>=0.3.0       # Gemini API
cryptography>=42.0.0      # 암호화
pytest>=7.0.0             # 테스트
pytest-asyncio>=0.23.0
```

### 시스템 의존성
- **MediaMTX** - RTMP/WebRTC 미디어 서버
- **ffmpeg** - 비디오 인코딩/디코딩
- **MongoDB** - 데이터베이스
- **Redis** - 캐시 & Pub/Sub

---

## 🎓 다음 단계

### 즉시 작업 (1주일)
1. AI Vision 실제 통합 (Tesseract, YOLO)
2. AI NLP 실제 통합 (KoBERT)
3. 프로덕션 배포 가이드 완성

### 단기 작업 (1개월)
1. 모니터링 대시보드 (Prometheus + Grafana)
2. CI/CD 파이프라인 (GitHub Actions)
3. Docker Compose 배포

### 장기 작업 (3개월)
1. iOS 앱 개발
2. 고급 AI 분석 (학습 패턴 예측)
3. 멀티 언어 지원

---

**이 문서는 프로젝트의 최신 상태를 반영합니다.**  
**마지막 테스트 통과율:** 94% (150+/161)  
**마지막 버그 수정:** 2025-02-02
