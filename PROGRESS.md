# AIRClass WebRTC 스트리밍 프로젝트 - 현재 진행 상황

**최종 업데이트:** 2025년 1월 3일 13:27  
**프로젝트 경로:** `/Users/hwansi/Project/AirClass`

---

## 📊 프로젝트 개요

**목표:** 실시간 AI 기반 인터랙티브 교육 플랫폼 (저지연 WebRTC 스트리밍)

**아키텍처:**
```
안드로이드 앱 (RTMP) 
    ↓
메인 노드 (RTMP 수신, 클러스터 관리, 녹화)
    ↓ RTSP
서브 노드 3개 (스트림 pull 후 학생들에게 WebRTC로 분배)
    ↓ WebRTC + JWT 인증
학생들 (브라우저/앱 클라이언트)
```

**용량:** 총 450명 동시 접속 (서브 노드당 150명 × 3)

---

## ✅ 완료된 작업

### 1. 클러스터 아키텍처 구현
- **파일:** `/Users/hwansi/Project/AirClass/backend/core/cluster.py`
- **내용:**
  - 메인 노드를 학생 라우팅에서 제외 (메인은 관리만 담당)
  - Rendezvous Hashing으로 서브 노드에만 분배
  - 클러스터 상태 모니터링 API 구현
- **결과:** ✅ 정상 작동 (Main 1개 + Sub 3개 등록됨)

### 2. JWT 인증 시스템
- **파일:**
  - `/Users/hwansi/Project/AirClass/backend/routers/auth.py` - 토큰 발급
  - `/Users/hwansi/Project/AirClass/backend/utils/jwt_auth.py` - JWT 생성/검증
  - `/Users/hwansi/Project/AirClass/backend/routers/mediamtx_auth.py` - MediaMTX 콜백
- **인증 플로우:**
  1. 학생 → 메인: JWT 토큰 요청
  2. 메인 → 학생: JWT + 서브 노드 WebRTC URL
  3. 학생 → 서브: `?jwt=...` query parameter로 인증
  4. 서브 → FastAPI: HTTP 콜백으로 JWT 검증
  5. FastAPI → 서브: 200 OK 반환
- **결과:** ✅ 정상 작동 (JWT 인증 100% 성공)

### 3. Docker 환경 구성
- **파일:** `/Users/hwansi/Project/AirClass/docker-compose.yml`
- **컨테이너:**
  - `airclass-main-node` (포트: 8000, 1935, 8889)
  - `airclass-sub-1` (포트: 8001, 8890, 8190/udp)
  - `airclass-sub-2` (포트: 8002, 8891, 8191/udp)
  - `airclass-sub-3` (포트: 8003, 8892, 8192/udp)
  - `airclass-mongodb`, `airclass-redis`
- **결과:** ✅ 모든 컨테이너 정상 동작

### 4. MediaMTX 설정 및 업그레이드
- **버전:** v1.9.3 → **v1.16.0** (최신)
- **주요 설정 파일:**
  - `/Users/hwansi/Project/AirClass/backend/mediamtx-main.yml` (메인 노드)
  - `/Users/hwansi/Project/AirClass/backend/mediamtx-sub.yml` (서브 노드)
- **설정 내용:**
  ```yaml
  webrtc: yes
  webrtcAddress: :8889
  webrtcEncryption: no
  webrtcAllowOrigin: '*'
  webrtcIPsFromInterfaces: no
  webrtcAdditionalHosts: [localhost]
  
  authMethod: http
  authHTTPAddress: http://127.0.0.1:8000/api/auth/mediamtx
  
  paths:
    all:
      source: rtmp://main:1935/live/stream
      webrtcDisable: no
  ```
- **결과:** ✅ v1.16.0 업그레이드 성공

### 5. 스트리밍 파이프라인
- **테스트 스트림:** FFmpeg 테스트 패턴 → Main (RTMP) → Sub 노드들 (RTSP pull)
- **명령어:**
  ```bash
  ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 \
    -f lavfi -i sine=frequency=1000:sample_rate=44100 \
    -c:v libx264 -preset veryfast -b:v 2000k \
    -c:a aac -b:a 128k \
    -f flv rtmp://localhost:1935/live/stream
  ```
- **결과:** ✅ 스트림 정상 수신 (`live/stream` ready 상태)

### 6. WebRTC 테스트 환경
- **테스트 페이지:** `/tmp/webrtc_test.html`
- **HTTP 서버:** 포트 8080
- **접속 URL:** `http://localhost:8080/webrtc_test.html`
- **결과:** ✅ 페이지 로드 및 JWT 발급 성공

---

## ✅ WHEP 시그널링 해결 (2025-02 적용)

### 적용한 수정
1. **MediaMTX Sub path:** `mediamtx-sub.yml`의 path를 `all` → `"live/stream"`으로 변경 (URL `/live/stream/whep`와 일치).
2. **Sub ICE 설정:** `docker-entrypoint.sh`에서 Sub가 사용하는 **mediamtx-sub.yml**에 `webrtcAdditionalHosts`, `webrtcLocalUDPAddress` 반영 (기존에는 mediamtx.yml만 수정되어 ICE 후보가 비어 있음).
3. **테스트 페이지:** Transceiver 추가(video/audio recvonly), WHEP fetch 타임아웃(15초), SDP 정리(cleanSdpForMediaMTX) 적용.

### 현재 테스트 절차 (테스트 영상 송출 + 수신)
1. **메인으로 테스트 영상 송출 (필수)**  
   FFmpeg가 Main RTMP로 송출 중이어야 Sub가 스트림을 받을 수 있음.
   ```bash
   ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 \
     -f lavfi -i sine=frequency=1000:sample_rate=44100 \
     -c:v libx264 -preset veryfast -b:v 2000k -c:a aac -b:a 128k \
     -f flv rtmp://localhost:1935/live/stream
   ```
2. **agent-browser로 수신 테스트**
   ```bash
   agent-browser open http://localhost:8080/webrtc_test.html
   agent-browser find role button click --name "연결"
   # 10~15초 후 상태/콘솔 확인
   agent-browser get text "#status"
   agent-browser console | grep -E "WHEP|ICE|트랙|스트리밍"
   ```
3. **확인 사항**
   - WHEP 응답 **201 Created**, SDP Answer 수신 → 시그널링 성공.
   - ICE 연결/트랙 수신은 Docker·NAT 환경에 따라 로컬에서 실패할 수 있음. 같은 머신에서 브라우저로 직접 접속해 비디오 재생 여부 확인 권장.

---

## ❌ 이전 문제: WebRTC SDP 호환성 실패 (해결됨)

### 당시 증상
```
브라우저 WebRTC 연결 시도
    ↓
JWT 인증 성공 ✅
    ↓
WHEP POST 요청 전송
    ↓
❌ 400 Bad Request 응답 (또는 타임아웃)
```

### 진단 결과

#### ✅ 성공: curl WHEP 테스트
```bash
# curl로 minimal SDP 전송
curl -X POST "http://localhost:8892/live/stream/whep?jwt=$TOKEN" \
  -H "Content-Type: application/sdp" \
  --data-binary @- << 'SDP'
v=0
o=- 123456789 987654321 IN IP4 0.0.0.0
s=-
t=0 0
a=group:BUNDLE 0
a=ice-lite
m=video 9 UDP/TLS/RTP/SAVPF 96
c=IN IP4 0.0.0.0
a=mid:0
a=recvonly
a=rtcp-mux
a=rtpmap:96 H264/90000
a=fmtp:96 level-asymmetry-allowed=1;packetization-mode=1;profile-level-id=42e01f
a=ice-ufrag:abcdefgh
a=ice-pwd:abcdefghijklmnopqrstuvwx
a=fingerprint:sha-256 AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99
a=setup:active
SDP

# 결과: ✅ HTTP 200 OK + SDP Answer 반환!
```

#### ❌ 실패: 브라우저 WebRTC
```javascript
// /tmp/webrtc_test.html
const pc = new RTCPeerConnection({
    iceServers: []
});
pc.addTransceiver('video', {direction: 'recvonly'});
pc.addTransceiver('audio', {direction: 'recvonly'});

const offer = await pc.createOffer();
await pc.setLocalDescription(offer);

// 브라우저가 생성한 SDP (처음 500자):
// v=0 o=- 4647525398726937122 2 IN IP4 127.0.0.1 s=- t=0 0 a=extmap-allow-mixed a=msid-semantic: WMS

fetch(whepUrl, {
    method: 'POST',
    headers: {'Content-Type': 'application/sdp'},
    body: offer.sdp
});

// 결과: ❌ 400 Bad Request
```

### 로그 분석

**MediaMTX 로그 (sub-3):**
```
✅ JWT 인증 콜백 호출됨
✅ FastAPI가 200 OK 응답
✅ "Allowing WebRTC read for test-student-001"
❌ 그 이후 WHEP POST 처리 로그 없음 (요청이 MediaMTX에 도달하지 못함)
```

### 핵심 문제

**curl의 SDP는 MediaMTX가 수락하지만, 브라우저의 SDP는 거부합니다.**

**가능한 원인:**
1. **SDP 포맷 차이**
   - curl: 최소한의 필수 속성만 포함 (`a=ice-lite`, `a=setup:active`, 등)
   - 브라우저: 브라우저 특화 속성 포함 (`a=extmap-allow-mixed`, `a=msid-semantic: WMS`, 등)

2. **ICE 설정 차이**
   - curl: `a=ice-lite` 사용
   - 브라우저: Full ICE candidate 생성 시도

3. **DTLS/Fingerprint 포맷**
   - MediaMTX가 특정 fingerprint 알고리즘만 지원할 가능성

4. **Codec 협상**
   - 브라우저가 제안한 codec을 MediaMTX가 지원하지 않을 가능성

---

## 🎯 해결해야 할 과제

### 우선순위 1: SDP 호환성 해결 (현재 진행 중)

**목표:** 브라우저 WebRTC ↔ MediaMTX 간 SDP 협상 성공

**제약 조건:**
- ❌ HLS 사용 불가 (딜레이 2-10초, 실시간 인터랙션 불가능)
- ✅ WebRTC 필수 (딜레이 < 500ms 목표)

**시도한 해결책:**
1. ✅ MediaMTX v1.9.3 → v1.16.0 업그레이드 (문제 지속)
2. ✅ Authorization Bearer 헤더 추가 (MediaMTX가 지원 안 함, query parameter만 작동)
3. ✅ WHEP 엔드포인트 직접 테스트 (curl은 성공, 브라우저는 실패)
4. ⏳ **현재:** SDP 포맷 차이 분석 필요

**다음 단계:**
1. 브라우저가 생성한 전체 SDP 덤프 확인
2. MediaMTX가 요구하는 SDP 요구사항 파악
3. RTCPeerConnection 설정 조정 또는 SDP munging

### 우선순위 2: 프로덕션 배포 준비
- 안드로이드 앱 → Main 노드 RTMP 전송 테스트
- HTTPS/WSS 설정 (암호화 통신)
- 모니터링 및 로깅 시스템 구축

---

## 📁 주요 파일 위치

| 파일/디렉토리 | 경로 | 용도 |
|--------------|------|------|
| **Docker Compose** | `/Users/hwansi/Project/AirClass/docker-compose.yml` | 컨테이너 오케스트레이션 |
| **Dockerfile** | `/Users/hwansi/Project/AirClass/backend/Dockerfile` | 이미지 빌드 (MediaMTX v1.16.0) |
| **MediaMTX 메인** | `/Users/hwansi/Project/AirClass/backend/mediamtx-main.yml` | 메인 노드 설정 |
| **MediaMTX 서브** | `/Users/hwansi/Project/AirClass/backend/mediamtx-sub.yml` | 서브 노드 설정 |
| **클러스터 로직** | `/Users/hwansi/Project/AirClass/backend/core/cluster.py` | 라우팅/로드밸런싱 |
| **JWT 인증** | `/Users/hwansi/Project/AirClass/backend/routers/mediamtx_auth.py` | MediaMTX 콜백 |
| **토큰 발급** | `/Users/hwansi/Project/AirClass/backend/routers/auth.py` | JWT 생성 API |
| **테스트 페이지** | `/tmp/webrtc_test.html` | 브라우저 WebRTC 클라이언트 |

---

## 🔧 유용한 명령어

### 컨테이너 관리
```bash
# 전체 재시작
cd /Users/hwansi/Project/AirClass
docker compose down
docker compose up -d

# 특정 노드 재빌드
docker compose build --no-cache sub-1 sub-2 sub-3
docker compose up -d
```

### 클러스터 상태 확인
```bash
curl -s http://localhost:8000/cluster/nodes | python3 -m json.tool
```

### JWT 토큰 발급 테스트
```bash
curl -X POST "http://localhost:8000/api/token?user_type=student&user_id=test001&action=read"
```

### FFmpeg 테스트 스트림 시작
```bash
ffmpeg -re -f lavfi -i testsrc=size=1280x720:rate=30 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -c:v libx264 -preset veryfast -b:v 2000k \
  -c:a aac -b:a 128k \
  -f flv rtmp://localhost:1935/live/stream > /tmp/ffmpeg.log 2>&1 &
echo $! > /tmp/ffmpeg.pid
```

### 테스트 페이지 접속
```bash
cd /tmp
python3 -m http.server 8080 &
# 브라우저: http://localhost:8080/webrtc_test.html
```

### MediaMTX 로그 확인
```bash
docker logs airclass-sub-1 2>&1 | tail -30
```

### curl WHEP 테스트
```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/token?user_type=student&user_id=test&action=read" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

curl -X POST "http://localhost:8890/live/stream/whep?jwt=$TOKEN" \
  -H "Content-Type: application/sdp" \
  --data-binary @sdp_offer.txt
```

---

## 📊 시스템 상태

### 현재 실행 중인 서비스
- ✅ MongoDB (포트 27017)
- ✅ Redis (포트 6379)
- ✅ Main 노드 (FastAPI: 8000, RTMP: 1935)
- ✅ Sub-1 노드 (FastAPI: 8001, WebRTC: 8890)
- ✅ Sub-2 노드 (FastAPI: 8002, WebRTC: 8891)
- ✅ Sub-3 노드 (FastAPI: 8003, WebRTC: 8892)
- ✅ FFmpeg 테스트 스트림 (PID: `/tmp/ffmpeg.pid`)
- ✅ HTTP 서버 (포트 8080, PID: `/tmp/http_server.pid`)

### 클러스터 통계
- **총 노드:** 4개 (Main 1 + Sub 3)
- **학생 라우팅 대상:** Sub 3개만
- **총 용량:** 450명
- **현재 연결:** 0명

---

## 🚨 알려진 이슈

### 1. WebRTC 시그널링 (심각도: 🟢 해결)
- **상태:** WHEP 201 + SDP Answer 수신까지 정상
- **수정:** path `live/stream`, Sub용 mediamtx-sub.yml ICE 설정 반영

### 2. ICE/실제 영상 수신 (심각도: 🟡 진행 중)
- **상태:** WHEP 201 + SDP Answer 수신 후 ICE가 `new`에서 진행되지 않음 (2~20초 로그에서 계속 `new`)
- **원인 추정:** Docker·호스트 환경에서 ICE 후보(localhost/UDP 포트) 수신 또는 연결 실패
- **조치:** Sub-1 재시작 시 WHEP 타임아웃 해소됨. Sub-2는 curl로 201 즉시 응답 확인. 브라우저에서 직접 접속해 비디오 재생 여부 확인 권장

### 3. Authorization Bearer 헤더 미지원 (심각도: 🟡 중간)
- **상태:** 해결됨 (query parameter 사용)
- **내용:** MediaMTX가 Authorization 헤더를 인식하지 못함
- **해결:** `?jwt=...` query parameter로 전환

---

## 📈 다음 마일스톤

### 단기 (현재 주)
- [x] **WebRTC 시그널링 해결** (path `live/stream`, Sub ICE 설정, WHEP 201·Answer 성공)
- [x] **테스트 영상 송출 + 수신 테스트 절차** (FFmpeg → Main, agent-browser 연결 테스트)
- [ ] **ICE 연결 완료** (현재 `new` 유지, 환경별 조사)
- [ ] 비디오 재생 품질 및 지연 시간 측정

### 중기 (2-4주)
- [ ] 안드로이드 앱 통합 테스트
- [ ] HTTPS/WSS 암호화 적용
- [ ] 프로덕션 환경 배포
- [ ] 부하 테스트 (동시 접속 100명+)

### 장기 (1-3개월)
- [ ] AI 기능 통합 (음성 인식, 자막 생성 등)
- [ ] 녹화 및 VOD 기능
- [ ] 다중 교실 지원
- [ ] 모니터링 대시보드

---

## 💡 참고 자료

- **MediaMTX GitHub:** https://github.com/bluenviron/mediamtx
- **WHEP 스펙:** https://datatracker.ietf.org/doc/draft-ietf-wish-whep/
- **WebRTC MDN:** https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API
- **MediaMTX 버전:** v1.16.0 (2025-01-31 릴리스)

---

**작성자:** AI Assistant  
**최종 검토:** 진행 중
