# TURN 서버 설정 가이드

## TURN 서버가 필요한 이유

**WebRTC NAT Traversal 문제:**
- 방화벽/NAT 뒤의 클라이언트는 직접 P2P 연결 불가
- STUN만으로는 Symmetric NAT 통과 불가
- **TURN 서버가 중계 역할** 수행

**언제 필요한가?**
- ✅ 프로덕션 환경 (필수)
- ✅ 외부 네트워크 접속 (필수)
- ❌ 로컬 테스트 (LAN 환경에서는 불필요)

---

## 옵션 1: Coturn 자체 호스팅 (권장)

### 1. Coturn 설치

#### Docker Compose에 추가
```yaml
# docker-compose.yml
services:
  coturn:
    image: coturn/coturn:latest
    container_name: airclass-coturn
    restart: unless-stopped
    network_mode: host  # TURN은 host 네트워크 필요
    volumes:
      - ./coturn/turnserver.conf:/etc/coturn/turnserver.conf:ro
    environment:
      - DETECT_EXTERNAL_IP=yes
```

#### Coturn 설정 파일 생성
```bash
mkdir -p coturn
cat > coturn/turnserver.conf << 'EOF'
# TURN 서버 기본 설정
listening-port=3478
tls-listening-port=5349

# 외부 IP (자동 감지 또는 수동 설정)
# external-ip=YOUR_PUBLIC_IP

# Realm (도메인)
realm=turn.airclass.example.com

# 인증 정보
user=airclass:YOUR_STRONG_PASSWORD
lt-cred-mech

# 로그
verbose
log-file=/var/log/turnserver.log

# 보안
fingerprint
no-multicast-peers
no-cli

# 포트 범위
min-port=49152
max-port=65535

# TLS 인증서 (Let's Encrypt 사용 권장)
# cert=/etc/letsencrypt/live/turn.airclass.example.com/fullchain.pem
# pkey=/etc/letsencrypt/live/turn.airclass.example.com/privkey.pem
EOF
```

### 2. LiveKit 환경 변수 설정

```bash
# .env 파일에 추가
TURN_ENABLED=true
TURN_DOMAIN=turn.airclass.example.com
TURN_TLS_PORT=5349
TURN_UDP_PORT=3478
TURN_EXTERNAL_TLS=true
```

### 3. 서비스 시작

```bash
docker-compose up -d coturn
docker-compose restart main sub-1
```

### 4. 테스트

```bash
# TURN 서버 연결 테스트
turnutils_uclient -v -u airclass -w YOUR_STRONG_PASSWORD turn.airclass.example.com

# 브라우저에서 확인
# chrome://webrtc-internals/ → ICE candidates에 "relay" 타입 확인
```

---

## 옵션 2: LiveKit Cloud TURN (간편)

LiveKit Cloud를 사용하면 TURN 서버가 자동 제공됩니다.

### 1. LiveKit Cloud 가입
https://cloud.livekit.io/

### 2. 프로젝트 생성 및 API 키 발급

### 3. 환경 변수 업데이트
```bash
# .env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# TURN은 자동 제공되므로 별도 설정 불필요
```

### 4. 코드 수정 (선택사항)
LiveKit Cloud를 사용하면 자체 서버 불필요. Frontend만 Cloud에 연결.

---

## 옵션 3: 공개 TURN 서버 (테스트용)

**⚠️ 프로덕션 사용 금지 (보안/성능 문제)**

### Google STUN/TURN 서버
```javascript
// Frontend에서 사용
const iceServers = [
  { urls: 'stun:stun.l.google.com:19302' },
  { urls: 'stun:stun1.l.google.com:19302' },
];
```

### Twilio TURN (무료 티어)
https://www.twilio.com/stun-turn

---

## 프로덕션 체크리스트

### 필수 설정
- [ ] TURN 서버 설치 (Coturn 또는 LiveKit Cloud)
- [ ] TLS 인증서 설정 (Let's Encrypt)
- [ ] 방화벽 포트 오픈
  - UDP 3478 (TURN)
  - TCP 5349 (TURN over TLS)
  - UDP 49152-65535 (RTC 미디어)
- [ ] 도메인 DNS 설정
- [ ] 강력한 TURN 비밀번호 설정

### 보안 설정
- [ ] TURN 인증 활성화 (`lt-cred-mech`)
- [ ] TLS 강제 (`external-tls=true`)
- [ ] Rate limiting 설정
- [ ] 로그 모니터링

### 성능 최적화
- [ ] TURN 서버를 LiveKit 서버와 가까운 리전에 배치
- [ ] 충분한 대역폭 확보 (사용자당 ~2Mbps)
- [ ] 서버 리소스 모니터링 (CPU, 메모리, 네트워크)

---

## 문제 해결

### 문제 1: "ICE connection failed"

**원인:** TURN 서버 연결 실패

**해결:**
```bash
# 1. TURN 서버 상태 확인
docker logs airclass-coturn

# 2. 포트 오픈 확인
sudo netstat -tulnp | grep -E "3478|5349"

# 3. 방화벽 규칙 확인
sudo ufw status
```

### 문제 2: "TURN credentials invalid"

**원인:** 인증 정보 불일치

**해결:**
1. `turnserver.conf`의 `user=` 확인
2. LiveKit 설정의 TURN 자격증명 확인
3. 서비스 재시작

### 문제 3: 높은 지연 시간

**원인:** TURN 중계로 인한 추가 홉

**해결:**
- TURN 서버를 사용자와 가까운 위치에 배치
- 직접 P2P 연결 우선 시도 (STUN)
- TURN은 최후의 수단으로만 사용

---

## 비용 예측

### Coturn 자체 호스팅
- **서버 비용:** $20-50/월 (AWS t3.medium)
- **대역폭:** $0.09/GB (AWS)
- **예상 총 비용:** $100-200/월 (100명 동시 접속 기준)

### LiveKit Cloud
- **무료 티어:** 월 50GB 무료
- **유료:** $0.10/GB
- **예상 총 비용:** $50-150/월 (100명 동시 접속 기준)

---

## 참고 자료

- Coturn 공식 문서: https://github.com/coturn/coturn
- LiveKit TURN 설정: https://docs.livekit.io/deploy/turn/
- WebRTC ICE 디버깅: chrome://webrtc-internals/
- STUN/TURN 테스트: https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/
