# WebRTC Screen Streaming System

실시간 화면 스트리밍 시스템 (WebRTC/RTMP 기반)

## 🎯 시스템 구조

```
안드로이드 앱 --[RTMP]--> MediaMTX --[WebRTC]--> 웹 브라우저
     (송출)                (변환)            (시청)
```

### 전송 흐름
1. **안드로이드 앱**: 화면을 캡쳐하여 RTMP로 스트리밍
2. **MediaMTX 서버**: RTMP를 받아 WebRTC로 변환
3. **웹 브라우저**: WebRTC로 초저지연 실시간 시청

## 🚀 빠른 시작

### 1. 백엔드 서버 실행

```bash
cd backend
chmod +x start_server.sh
./start_server.sh
```

**실행되는 서비스:**
- MediaMTX (포트 1935: RTMP, 8889: WebRTC)
- FastAPI (포트 8000: 웹 인터페이스)

### 2. 웹 뷰어 접속

브라우저에서 다음 주소 중 하나로 접속:

- **일반 뷰어**: http://localhost:8000/viewer
- **교사용**: http://localhost:8000/teacher
- **학생용**: http://localhost:8000/student

### 3. 안드로이드 앱 실행

#### Android Studio에서:
1. `android` 폴더 열기
2. 기기 선택 (에뮬레이터 또는 실제 폰)
3. **▶ Run** 버튼 클릭

#### 앱에서 설정:
- **에뮬레이터**: 서버 IP에 `10.0.2.2` 입력
- **실제 폰**: PC의 내부 IP 입력 (예: `192.168.0.12`)

#### IP 확인 방법:
```bash
# Mac/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig
```

## 📡 포트 정보

| 서비스 | 포트 | 프로토콜 | 용도 |
|--------|------|---------|------|
| MediaMTX RTMP | 1935 | TCP | 안드로이드 → 서버 |
| MediaMTX WebRTC | 8889 | HTTP/UDP | 서버 → 브라우저 |
| MediaMTX RTSP | 8554 | TCP | 옵션 |
| MediaMTX HLS | 8888 | HTTP | 옵션 |
| FastAPI | 8000 | HTTP | 웹 UI |

## 🔧 설정 파일

### MediaMTX 설정 (`mediamtx.yml`)
- RTMP 입력 설정
- WebRTC 출력 설정
- 스트림 경로: `/live/stream`

### 안드로이드 앱
- RTMP URL: `rtmp://{server_ip}:1935/live/stream`
- 해상도: 1280x720 (720p)
- FPS: 30
- 비트레이트: 2.5 Mbps

## 🎥 주요 기능

### 안드로이드 앱
- ✅ 실시간 화면 캡쳐 (MediaProjection API)
- ✅ RTMP 스트리밍 (RootEncoder 라이브러리)
- ✅ 자동 재연결
- ✅ 실시간 연결 상태 알림
- ✅ Foreground Service (백그라운드 실행)

### 웹 뷰어
- ✅ WebRTC 초저지연 스트리밍 (~200ms)
- ✅ 실시간 연결 상태 표시
- ✅ 반응형 디자인 (모바일/데스크톱)
- ✅ LIVE 뱃지 표시
- ✅ 자동 재연결

## 📱 Android 앱 사용법

### 권한
앱 실행 시 다음 권한이 필요합니다:
- 화면 녹화 권한 (MediaProjection)
- 오디오 녹음 권한 (RECORD_AUDIO)
- 알림 권한 (POST_NOTIFICATIONS, Android 13+)

### 시작하기
1. 서버 IP 입력
2. **[시작]** 버튼 클릭
3. "지금 시작" 권한 승인
4. 알림 표시 확인 (스트리밍 중)

### 중지하기
- **[중지]** 버튼 클릭
- 또는 알림에서 앱 종료

## 🛠️ 트러블슈팅

### 연결 실패
1. **서버 확인**
   ```bash
   # MediaMTX 실행 확인
   lsof -i:1935
   lsof -i:8889
   ```

2. **방화벽 확인**
   - 포트 1935, 8000, 8889 열기

3. **같은 네트워크 확인**
   - 폰과 PC가 같은 와이파이에 연결되어 있는지 확인

### 화면이 안 보임
1. **웹 브라우저 콘솔 확인** (F12)
2. **MediaMTX 로그 확인**
   ```bash
   cd backend
   tail -f server.log
   ```

### 지연 시간이 길 경우
- WebRTC는 일반적으로 200ms 이하 지연
- 네트워크 상태 확인
- 비트레이트 조정 (앱의 `ScreenCaptureService.kt:122`)

## 📊 성능 정보

### 지연 시간
- **RTMP (앱→서버)**: ~1-2초
- **WebRTC (서버→브라우저)**: ~200ms
- **총 지연**: ~1.5초

### 대역폭
- **업로드 (앱)**: ~2.5 Mbps
- **다운로드 (브라우저)**: ~2.5 Mbps

### 해상도
- 720p (1280x720) @ 30fps
- 설정 변경: `ScreenCaptureService.kt:115-120`

## 🔄 업데이트 로그

### v2.0 - WebRTC 전환
- ❌ 레거시 HTTP 이미지 업로드 방식 제거
- ✅ RTMP/WebRTC 스트리밍 구현
- ✅ MediaMTX 통합
- ✅ 초저지연 달성 (~200ms)
- ✅ 파일 저장 불필요 (메모리 효율)

### v1.0 - 초기 버전 (제거됨)
- HTTP POST로 JPEG 이미지 업로드
- 5 FPS, 높은 지연 (~2초)
- 파일이 계속 쌓이는 문제

## 📝 개발 참고

### 사용 라이브러리

**Android:**
- RootEncoder 2.5.2 (RTMP 스트리밍)
- AndroidX Core, AppCompat
- Kotlin Coroutines

**Backend:**
- FastAPI (웹 서버)
- MediaMTX (RTMP/WebRTC 서버)
- Uvicorn (ASGI 서버)

### 주요 파일

**Android:**
- `MainActivity.kt`: UI 및 권한 관리
- `ScreenCaptureService.kt`: 화면 캡쳐 및 RTMP 스트리밍

**Backend:**
- `main.py`: FastAPI 서버 및 MediaMTX 관리
- `mediamtx`: RTMP/WebRTC 서버 바이너리
- `mediamtx.yml`: MediaMTX 설정
- `static_streaming/webrtc_viewer.html`: 웹 뷰어

## 🎓 교육용 활용

### 실시간 수업 중계
- 교사 화면을 학생들에게 실시간 전송
- 초저지연으로 자연스러운 수업 진행

### 1:N 방송
- 한 명의 송출자 (교사)
- 여러 명의 시청자 (학생)

### 다양한 디바이스 지원
- 안드로이드 폰/태블릿: 송출
- 모든 브라우저: 시청

## 📞 지원

문제가 발생하면:
1. 로그 확인 (`backend/server.log`)
2. MediaMTX 로그 확인
3. Android Logcat 확인

---

**최종 업데이트**: 2026-01-22
**버전**: 2.0 (WebRTC)
