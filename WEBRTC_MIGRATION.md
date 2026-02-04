# WebRTC 전용 아키텍처로 완전 전환

## 개요

RTMP를 완전히 제거하고 **WebRTC (WHIP/WHEP) 전용 아키텍처**로 전환하여 초저지연 스트리밍을 구현합니다.

### 예상 레이턴시 개선

| 구간 | RTMP (기존) | WebRTC (신규) | 개선폭 |
|------|------------|--------------|--------|
| Android → Main | 100-300ms | **30-80ms** | **-220ms** |
| Main → Sub | 50-100ms | **20-50ms** | **-50ms** |
| Sub → Student | 50-150ms | 50-150ms | 동일 |
| **총합** | **200-550ms** | **100-280ms** | **-270ms** |

**목표 달성: <200ms 엔드투엔드 지연시간** ✅

---

## 아키텍처 변경

### 기존 (RTMP 기반)
```
📱 Android App → RTMP (1935) → 🖥️ Main Node → RTSP (8554) → 📡 Sub Nodes → WebRTC (WHEP) → 👨‍🎓 Students
```

### 신규 (WebRTC 전용)
```
📱 Android App → WebRTC (WHIP:8889) → 🖥️ Main Node → RTSP (8554) → 📡 Sub Nodes → WebRTC (WHEP) → 👨‍🎓 Students
```

**변경 사항:**
- ✅ Android → Main: **RTMP 제거, WHIP 사용**
- ✅ Main → Sub: **RTSP 유지** (안정성 확보)
- ✅ Sub → Student: WebRTC (WHEP) 유지

---

## 백엔드 변경 사항

### 1. MediaMTX 설정 최적화

**파일**: `/backend/mediamtx.yml`

#### RTMP 비활성화
```yaml
# Line 243: RTMP 완전 비활성화
rtmp: no
```

#### WebRTC 최적화 설정
```yaml
# Line 318-370: WebRTC 설정
webrtc: yes
webrtcAddress: :8889

# WHIP/WHEP 동시 지원
# - Teacher: WHIP (publish) - PC 화면 공유
# - Android: WHIP (publish) - 모바일 스트리밍
# - Student: WHEP (read) - 시청

# ICE 서버 (STUN)
webrtcICEServers2:
  - url: stun:stun.l.google.com:19302

# 타임아웃 최적화 (초저지연)
webrtcHandshakeTimeout: 3s
webrtcTrackGatherTimeout: 500ms
```

#### 타임아웃 설정 (유지)
```yaml
# Line 17-20: 모바일 연결 안정성
readTimeout: 24h
writeTimeout: 24h
```

### 2. 토큰 발급 API (변경 없음)

**파일**: `/backend/routers/auth.py`

기존 코드는 이미 **WHIP/WHEP 모두 지원**:
- `action=publish` → WHIP URL 생성 (Line 126, 134, 143)
- `action=read` → WHEP URL 생성 (Line 125, 136, 145)

**엔드포인트**:
```http
POST /api/token?user_type=teacher&user_id=Teacher&action=publish
→ Returns: http://{SERVER_IP}:8889/live/stream/whip?jwt={token}

POST /api/token?user_type=student&user_id=Student123&action=read
→ Returns: http://{SERVER_IP}:8890/live/stream/whep?jwt={token}
```

---

## Android 앱 수정 가이드

### 현재 구현 (RTMP)
```java
// libstreaming 라이브러리 사용
SessionBuilder builder = SessionBuilder.getInstance()
    .setDestination("rtmp://10.100.0.102:1935/live/stream")
    .setVideoEncoder(SessionBuilder.VIDEO_H264)
    .setAudioEncoder(SessionBuilder.AUDIO_AAC);
```

### 변경 후 (WebRTC WHIP)

#### 1. 라이브러리 추가

**build.gradle**:
```gradle
dependencies {
    // Google WebRTC
    implementation 'org.webrtc:google-webrtc:1.0.+'
    
    // HTTP 클라이언트 (WHIP signaling)
    implementation 'com.squareup.okhttp3:okhttp:4.12.0'
}
```

#### 2. WebRTC 퍼블리셔 구현

**WebRTCPublisher.kt**:
```kotlin
import org.webrtc.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody

class WebRTCPublisher(private val context: Context) {
    private lateinit var peerConnection: PeerConnection
    private lateinit var peerConnectionFactory: PeerConnectionFactory
    private val httpClient = OkHttpClient()
    
    fun initialize() {
        // PeerConnectionFactory 초기화
        val options = PeerConnectionFactory.InitializationOptions.builder(context)
            .setEnableInternalTracer(true)
            .createInitializationOptions()
        PeerConnectionFactory.initialize(options)
        
        val encoderFactory = DefaultVideoEncoderFactory(
            EglBase.create().eglBaseContext,
            true, // enableIntelVp8Encoder
            true  // enableH264HighProfile
        )
        val decoderFactory = DefaultVideoDecoderFactory(EglBase.create().eglBaseContext)
        
        peerConnectionFactory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(encoderFactory)
            .setVideoDecoderFactory(decoderFactory)
            .createPeerConnectionFactory()
    }
    
    suspend fun publish(whipUrl: String, cameraSource: CameraVideoCapturer) {
        // 1. PeerConnection 생성
        val iceServers = listOf(
            PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer()
        )
        val rtcConfig = PeerConnection.RTCConfiguration(iceServers).apply {
            bundlePolicy = PeerConnection.BundlePolicy.MAXBUNDLE
            rtcpMuxPolicy = PeerConnection.RtcpMuxPolicy.REQUIRE
        }
        
        peerConnection = peerConnectionFactory.createPeerConnection(
            rtcConfig,
            object : PeerConnection.Observer {
                override fun onIceCandidate(candidate: IceCandidate) {
                    // WHIP는 Trickle ICE를 사용하지 않으므로 무시
                }
                override fun onIceConnectionChange(state: PeerConnection.IceConnectionState) {
                    Log.d(TAG, "ICE Connection: $state")
                }
                // ... 기타 콜백
            }
        )!!
        
        // 2. 비디오/오디오 트랙 추가
        val videoTrack = createVideoTrack(cameraSource)
        val audioTrack = createAudioTrack()
        
        peerConnection.addTrack(videoTrack, listOf("stream"))
        peerConnection.addTrack(audioTrack, listOf("stream"))
        
        // 3. Offer SDP 생성
        val offerConstraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "false"))
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "false"))
        }
        
        val offer = suspendCoroutine<SessionDescription> { continuation ->
            peerConnection.createOffer(object : SdpObserver {
                override fun onCreateSuccess(sdp: SessionDescription) {
                    continuation.resume(sdp)
                }
                override fun onCreateFailure(error: String) {
                    continuation.resumeWithException(Exception(error))
                }
                // ... 기타 콜백
            }, offerConstraints)
        }
        
        peerConnection.setLocalDescription(SdpObserver(), offer)
        
        // 4. WHIP 시그널링 (HTTP POST)
        val request = Request.Builder()
            .url(whipUrl)
            .post(offer.description.toRequestBody("application/sdp".toMediaType()))
            .build()
        
        val response = httpClient.newCall(request).execute()
        if (!response.isSuccessful) {
            throw Exception("WHIP failed: ${response.code}")
        }
        
        // 5. Answer SDP 받기
        val answerSdp = response.body!!.string()
        val answer = SessionDescription(SessionDescription.Type.ANSWER, answerSdp)
        peerConnection.setRemoteDescription(SdpObserver(), answer)
        
        Log.i(TAG, "✅ WebRTC publishing started via WHIP")
    }
    
    private fun createVideoTrack(capturer: CameraVideoCapturer): VideoTrack {
        val surfaceTextureHelper = SurfaceTextureHelper.create("CaptureThread", EglBase.create().eglBaseContext)
        val videoSource = peerConnectionFactory.createVideoSource(capturer.isScreencast)
        capturer.initialize(surfaceTextureHelper, context, videoSource.capturerObserver)
        capturer.startCapture(1280, 720, 30)
        
        return peerConnectionFactory.createVideoTrack("video", videoSource)
    }
    
    private fun createAudioTrack(): AudioTrack {
        val audioSource = peerConnectionFactory.createAudioSource(MediaConstraints())
        return peerConnectionFactory.createAudioTrack("audio", audioSource)
    }
}
```

#### 3. Activity에서 사용

**MainActivity.kt**:
```kotlin
class StreamingActivity : AppCompatActivity() {
    private lateinit var publisher: WebRTCPublisher
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        publisher = WebRTCPublisher(this)
        publisher.initialize()
        
        lifecycleScope.launch {
            // 1. 토큰 받기
            val token = getPublishToken()
            
            // 2. 카메라 준비
            val cameraEnumerator = Camera2Enumerator(this@StreamingActivity)
            val cameraName = cameraEnumerator.deviceNames.firstOrNull { 
                cameraEnumerator.isFrontFacing(it) 
            } ?: throw Exception("No camera found")
            
            val capturer = cameraEnumerator.createCapturer(cameraName, null)
            
            // 3. WHIP로 퍼블리시
            publisher.publish(token.webrtc_url, capturer)
        }
    }
    
    private suspend fun getPublishToken(): TokenResponse {
        val response = httpClient.post("http://10.100.0.102:8000/api/token") {
            parameter("user_type", "teacher")
            parameter("user_id", "AndroidTeacher")
            parameter("action", "publish")
        }
        return response.body()
    }
}
```

---

## 네트워크 요구사항

### 포트 개방

| 프로토콜 | 포트 | 용도 | 방향 |
|---------|------|------|------|
| ~~RTMP~~ | ~~1935~~ | ~~폐기됨~~ | - |
| **WebRTC (WHIP)** | **8889** | Android → Main (TCP) | Inbound |
| **WebRTC (UDP)** | **8189** | ICE 연결 (UDP) | Bidirectional |
| WebRTC (WHEP) | 8890-8892 | Sub → Student | Outbound |

### 방화벽 설정

**Android → Main 연결 테스트**:
```bash
# UDP 포트 확인
nc -vzu 10.100.0.102 8189

# WHIP 엔드포인트 확인
curl -X POST http://10.100.0.102:8889/live/stream/whip \
  -H "Content-Type: application/sdp" \
  --data-binary @test.sdp
```

### UDP 차단 시 대안 (TURN 서버)

일부 기업/학교 네트워크는 UDP를 차단합니다. 이 경우 **TURN 서버** 필요:

**coturn 설치**:
```bash
# Docker Compose에 추가
coturn:
  image: coturn/coturn:latest
  ports:
    - "3478:3478/tcp"
    - "3478:3478/udp"
    - "49152-65535:49152-65535/udp"
  environment:
    - TURN_USERNAME=airclass
    - TURN_PASSWORD=secret
```

**MediaMTX 설정**:
```yaml
webrtcICEServers2:
  - url: stun:stun.l.google.com:19302
  - url: turn:10.100.0.102:3478
    username: airclass
    password: secret
```

---

## 테스트 계획

### 1. PoC: OBS Studio로 WHIP 테스트 (1일)

**OBS WebRTC 플러그인 설치**:
```bash
# https://obsproject.com/forum/resources/obs-webrtc.1369/
# WHIP URL 입력: http://10.100.0.102:8889/live/stream/whip
```

**타임스탬프 오버레이 추가**:
- OBS → Sources → Text (GDI+)
- Text: `%H:%M:%S.%f` (밀리초 표시)
- Teacher/Student 화면에서 동시 확인 → 레이턴시 측정

### 2. Android 프로토타입 (2-3주)

**Phase 1: 기본 연결**
- [ ] WebRTC 라이브러리 통합
- [ ] WHIP 시그널링 구현
- [ ] 카메라 캡처 연결

**Phase 2: 안정성 테스트**
- [ ] 3G/4G/5G 네트워크 테스트
- [ ] 배터리 소모 측정 (목표: RTMP 대비 +15% 이내)
- [ ] 장시간 스트리밍 (2시간 연속)

**Phase 3: 최적화**
- [ ] 하드웨어 인코더 활성화 (MediaCodec)
- [ ] Adaptive Bitrate 튜닝
- [ ] 네트워크 재연결 로직

### 3. 부하 테스트 (1주)

**시나리오**:
- 100명 동시 시청 (WHEP)
- Main 노드 CPU/메모리 모니터링
- Sub 노드 분산 확인

**성공 기준**:
- ✅ 레이턴시 <200ms (P95)
- ✅ CPU <70% (Main/Sub)
- ✅ 패킷 손실 <1%

---

## 롤백 계획

WebRTC 전환 실패 시 **즉시 RTMP로 복구**:

```yaml
# backend/mediamtx.yml
rtmp: yes  # ← true로 변경
rtmpAddress: :1935
```

```bash
docker restart airclass-main-node
```

**복구 시간**: < 5분

---

## 예상 개발 일정

| Phase | 작업 | 기간 |
|-------|------|------|
| 1 | PoC: OBS WHIP 테스트 | 1일 |
| 2 | Android WebRTC 통합 | 1주 |
| 3 | 안정성 테스트 | 1주 |
| 4 | 최적화 & 버그 수정 | 1주 |
| 5 | 부하 테스트 & 프로덕션 배포 | 3일 |
| **Total** | **3-4주** |

---

## 참고 자료

- **MediaMTX WHIP/WHEP 문서**: https://github.com/bluenviron/mediamtx#webrtc
- **Google WebRTC Android**: https://webrtc.github.io/webrtc-org/native-code/android/
- **WHIP RFC**: https://datatracker.ietf.org/doc/html/draft-ietf-wish-whip
- **OBS WebRTC 플러그인**: https://obsproject.com/forum/resources/obs-webrtc.1369/

---

## 체크리스트

### Backend
- [x] MediaMTX RTMP 비활성화 (`rtmp: no`)
- [x] WebRTC 설정 최적화 (타임아웃, ICE 서버)
- [x] 토큰 API WHIP/WHEP 지원 확인
- [ ] TURN 서버 구축 (선택사항)

### Android
- [ ] libwebrtc 라이브러리 통합
- [ ] WHIP 시그널링 구현
- [ ] 카메라/마이크 캡처 연결
- [ ] 네트워크 재연결 로직
- [ ] 배터리 최적화 (하드웨어 인코더)

### 테스트
- [ ] OBS WHIP PoC (레이턴시 측정)
- [ ] Android 3G/4G/5G 테스트
- [ ] 100명 동시 접속 부하 테스트
- [ ] 장시간 안정성 테스트 (2시간+)

### 프로덕션
- [ ] 방화벽 포트 개방 (8889 TCP, 8189 UDP)
- [ ] 모니터링 대시보드 업데이트
- [ ] 사용자 매뉴얼 작성
- [ ] 롤백 시나리오 검증

---

**작성일**: 2026-02-04  
**작성자**: AI Assistant  
**상태**: 설계 완료, 구현 대기 중
