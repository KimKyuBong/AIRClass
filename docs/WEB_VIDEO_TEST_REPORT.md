# 웹 영상 시청 결과 보고

## 1. 웹에서 영상 볼 수 있나요?

**네. 구현은 되어 있습니다.**

- **학생 페이지** (`/student`): 토큰 발급 → WebRTC(WHEP) 연결 → 서버에서 내려준 영상/음성 트랙을 `<video>`에 붙여 재생합니다.
- **모니터 페이지** (`/monitor`): 동일하게 WHEP으로 스트림 수신 후 재생합니다.
- **교사 페이지** (`/teacher`): 화면 공유 후 WHIP으로 퍼블리시하고, 자신의 미리보기도 WebRTC로 재생합니다.

영상이 **실제로 보이려면** 아래가 모두 만족되어야 합니다.

| 조건 | 설명 |
|------|------|
| 백엔드 실행 | `http://localhost:8000` (토큰 API, 상태 확인) |
| 프론트엔드 실행 | `http://localhost:5173` (Student/Monitor/Teacher 페이지) |
| MediaMTX 실행 | 백엔드 기동 시 자동 실행 (RTMP/WebRTC 처리) |
| **스트림 소스** | **교사가 화면 공유(푸시)를 시작한 상태** |

스트림이 없으면 WHEP 시그널링(201 + SDP Answer)은 성공해도 **영상/음성 트랙이 없어** 화면은 검은 채로일 수 있습니다.

---

## 2. 테스트했나요?

### 2.1 자동 테스트 (현재 상태)

- **백엔드 단위/통합 테스트** (pytest 339개): API, 라우터, 참여도, VOD 등만 검증합니다. **브라우저에서 영상 재생 여부는 다루지 않습니다.**
- **Playwright 스크립트** (`scripts/tests/webrtc_ice_result.js`):  
  학생 페이지를 열고, WebRTC로 트랙 수신 또는 `video` 재생까지 되는지 확인합니다.  
  - **실행 조건**: 백엔드(8000) + 프론트엔드(5173) 실행 중, 가능하면 **교사가 스트림을 푸시한 상태**에서 실행해야 “영상 재생”까지 성공할 수 있습니다.
  - 스트림 없이 실행하면: 토큰·WHEP 201은 성공해도 트랙이 없어 타임아웃으로 실패할 수 있습니다.

즉, **“웹에서 영상이 재생되는지”를 끝까지 검증하는 E2E는, 지금은 수동 또는 위 Playwright를 스트림 켠 뒤 돌리는 방식**입니다.

### 2.2 수동 테스트 방법 (권장)

1. **개발 서버 실행**
   ```bash
   # 프로젝트 루트에서
   ./scripts/dev/start-dev.sh
   ```
   또는 백엔드(8000) + 프론트(5173) 각각 실행.

2. **교사 화면에서 스트림 시작**
   - 브라우저에서 `http://localhost:5173/#/teacher` 접속
   - 이름 입력 후 입장 → **화면 공유 시작** (브라우저 “화면 공유” 허용)

3. **학생/모니터에서 영상 확인**
   - 새 탭에서 `http://localhost:5173/#/student?name=테스트학생` 접속
   - 또는 `http://localhost:5173/#/monitor`
   - 교사가 공유한 화면이 재생되면 **웹에서 영상 보기 성공**입니다.

4. **(선택) Playwright로 자동 검증**
   ```bash
   # 프론트엔드에서 Playwright 설치 후 (한 번만)
   cd frontend && npx playwright install chromium

   # 프로젝트 루트에서, 위 1~2 단계 완료한 뒤
   node scripts/tests/webrtc_ice_result.js
   ```
   - 성공 시: `✅ RESULT: SUCCESS` 및 트랙/영상 정보 출력.
   - 실패 시: 콘솔 로그와 `RESULT: FAILED`로 원인 확인 가능.

---

## 3. 요약

| 질문 | 답변 |
|------|------|
| 웹에서 영상 볼 수 있어? | **가능합니다.** Student/Monitor가 WHEP으로 수신한 스트림을 `<video>`에 재생하도록 구현되어 있습니다. |
| 테스트했어? | **자동 테스트**: pytest는 “영상 재생”을 보지 않고, Playwright 스크립트는 “스트림이 켜진 상태”에서만 영상까지 검증 가능합니다. **수동 테스트**: 교사 화면 공유 → 학생/모니터 페이지에서 재생 확인하는 절차를 권장합니다. |

실제로 “지금 이 환경에서 영상이 나오는지” 확인하려면, 위 **2.2 수동 테스트**를 한 번 진행하는 것이 가장 확실합니다.

---

## 5. 테스트 영상 자동 전송 + 재생 검증

**스크립트**: `scripts/tests/send_test_video_and_verify.js`

- ffmpeg으로 **테스트 패턴 영상**(testsrc + 1kHz 사인파)을 RTMP(`rtmp://localhost:1935/live/stream`)로 전송한 뒤, Playwright로 학생 페이지에서 WebRTC 재생 여부를 검증합니다.
- **요구**: ffmpeg, Node, frontend에 Playwright 설치됨.

### HTTPS 프론트엔드에서 통과하려면

페이지가 `https://localhost:5175`인데 WHEP URL이 `http://localhost:8891`이면 **Mixed Content**로 fetch가 차단됩니다. 백엔드 재기동 시 `MODE=standalone` `WHEP_BASE_URL=https://localhost:5175` 로 두면, WHEP 요청이 프론트와 같은 origin으로 가서 Vite proxy(`/live` → 8889)로 전달됩니다.

### 실행 예시

```bash
# 1) 백엔드를 standalone + WHEP_BASE_URL 로 기동 (한 터미널)
MODE=standalone WHEP_BASE_URL=https://localhost:5175 ./scripts/dev/start-dev.sh

# 2) 다른 터미널에서 테스트 영상 전송 + Playwright 검증
INSECURE_HTTPS=1 node scripts/tests/send_test_video_and_verify.js
```

성공 시 `✅ Test video was sent and student page received/played the stream.` 출력.
