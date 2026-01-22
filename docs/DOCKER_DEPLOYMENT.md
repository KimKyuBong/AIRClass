# AIRClass Docker 배포 가이드 🐳

**Master-Slave 아키텍처로 자동 확장되는 스트리밍 시스템**

---

## 🎯 배포 모드

### 1. Standalone 모드 (테스트/소규모)
- **용도**: 빠른 테스트, 50명 이하 소규모 교실
- **구성**: 서버 1대
- **시간**: 1분 배포

### 2. Cluster 모드 (프로덕션/대규모)
- **용도**: 100명 이상 대규모 환경, 자동 확장
- **구성**: Master 1대 + Slave N대
- **시간**: 2분 배포

---

## ⚡ 빠른 시작 (Standalone)

### 1분 배포
```bash
# 1. 프로젝트 클론
git clone https://github.com/your-repo/airclass
cd AirClass

# 2. Docker Compose 실행
docker-compose -f docker-compose.simple.yml up -d

# 3. 접속
# RTMP: rtmp://localhost:1935/live/stream
# HLS:  http://localhost:8888/live/stream/index.m3u8
# API:  http://localhost:8000
```

**끝!** Android 앱에서 `rtmp://서버IP:1935/live/stream`으로 스트리밍 시작하세요.

---

## 🚀 프로덕션 배포 (Cluster 모드)

### 아키텍처

```
               [Internet/Intranet]
                       |
                 [Master Node]
              http://master:8000
                       |
    +------------------+------------------+
    |                  |                  |
[Slave 1]         [Slave 2]          [Slave 3]
150명 처리        150명 처리         150명 처리
    |                  |                  |
RTMP + HLS       RTMP + HLS         RTMP + HLS
```

**특징**:
- ✅ 자동 로드 밸런싱 (접속자 수 기반)
- ✅ 자동 헬스 체크 (장애 노드 자동 제외)
- ✅ 무중단 확장 (서버 추가/제거)
- ✅ 최대 500명+ 지원 (Slave 3대 기준)

---

## 📦 설치 방법

### 사전 요구사항

```bash
# Docker 설치 확인
docker --version
docker-compose --version

# 최소 요구사항:
# - Docker 20.10+
# - Docker Compose 2.0+
```

### Step 1: 프로젝트 준비

```bash
git clone https://github.com/your-repo/airclass
cd AirClass
```

### Step 2: 환경 변수 설정

```bash
# .env 파일 생성
cat > .env <<EOF
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
EOF
```

**중요**: 프로덕션에서는 반드시 강력한 비밀키로 변경!

```bash
# 랜덤 비밀키 생성
openssl rand -hex 32
```

### Step 3: 배포

#### Option 1: 기본 구성 (Master 1 + Slave 3)

```bash
docker-compose up -d
```

#### Option 2: Slave 개수 조정

```bash
# 5대의 Slave로 확장 (750명 수용)
docker-compose up -d --scale slave=5

# 10대의 Slave로 확장 (1500명 수용)
docker-compose up -d --scale slave=10
```

#### Option 3: 특정 서버에 배포

```bash
# 서버 1: Master
docker-compose up -d master

# 서버 2-4: Slave만 실행
docker-compose up -d --scale slave=3 --no-deps slave
```

---

## 🔍 상태 확인

### 1. 컨테이너 상태
```bash
docker-compose ps
```

출력 예시:
```
NAME                   STATUS              PORTS
airclass-master        Up 2 minutes        0.0.0.0:8000->8000/tcp
airclass-slave-1       Up 2 minutes        0.0.0.0:49153->8000/tcp
airclass-slave-2       Up 2 minutes        0.0.0.0:49154->8000/tcp
airclass-slave-3       Up 2 minutes        0.0.0.0:49155->8000/tcp
```

### 2. 클러스터 상태 조회
```bash
curl http://localhost:8000/cluster/nodes | jq
```

출력 예시:
```json
{
  "total_nodes": 3,
  "healthy_nodes": 3,
  "offline_nodes": 0,
  "total_connections": 45,
  "total_capacity": 450,
  "utilization": 10.0,
  "nodes": [
    {
      "node_id": "slave-1",
      "node_name": "slave-1",
      "current_connections": 15,
      "max_connections": 150,
      "load_percentage": 10.0,
      "status": "healthy"
    },
    // ...
  ]
}
```

### 3. 로그 확인
```bash
# 전체 로그
docker-compose logs -f

# Master 로그만
docker-compose logs -f master

# 특정 Slave 로그
docker-compose logs -f airclass-slave-1
```

### 4. 헬스 체크
```bash
# Master
curl http://localhost:8000/health

# Slave (포트는 docker ps로 확인)
curl http://localhost:49153/health
```

---

## 🎓 사용 방법

### Android 앱 설정

```kotlin
// Master 주소로 RTMP 전송
val masterUrl = "http://192.168.1.100:8000"

// 1. Master에게 최적의 Slave 요청
val response = httpClient.get("$masterUrl/cluster/best-node")
val node = response.json()

// 2. 선택된 Slave로 RTMP 스트리밍
val rtmpUrl = node["rtmp_url"]  // rtmp://slave-host:1935/live/stream
startStreaming(rtmpUrl)
```

### 학생 접속 (Frontend)

```javascript
// Master에게 토큰 요청 (자동으로 최적의 Slave 선택)
const response = await fetch(
  'http://192.168.1.100:8000/api/token?user_type=student&user_id=홍길동',
  { method: 'POST' }
);

const data = await response.json();
// data.hls_url: http://slave-2:8888/live/stream/index.m3u8?jwt=...
// data.node_name: "slave-2" (어느 서버에 연결됐는지)

// HLS 재생
initHLS(data.hls_url);
```

**자동으로**:
- Master가 부하가 적은 Slave 선택
- 해당 Slave의 HLS URL 반환
- 학생은 선택된 Slave에서 직접 스트림 수신

---

## 📊 모니터링

### 실시간 대시보드

```bash
# Prometheus + Grafana 활성화 (docker-compose.yml 주석 해제 후)
docker-compose up -d prometheus grafana

# Grafana 접속
open http://localhost:3000
# ID: admin
# PW: admin
```

### 간단한 모니터링 스크립트

```bash
#!/bin/bash
# monitor.sh - 클러스터 상태 실시간 모니터링

watch -n 5 '
echo "=== AIRClass Cluster Status ==="
curl -s http://localhost:8000/cluster/nodes | jq ".nodes[] | {
  name: .node_name,
  connections: .current_connections,
  load: (.load_percentage | tostring + \"%\"),
  status: .status
}"
'
```

실행:
```bash
chmod +x monitor.sh
./monitor.sh
```

---

## 🔧 운영 관리

### 서버 추가 (무중단 확장)

```bash
# 현재 Slave 개수 확인
docker-compose ps | grep slave | wc -l

# Slave 2대 추가 (3 → 5대)
docker-compose up -d --scale slave=5 --no-recreate
```

**자동으로**:
- 새 Slave가 시작하면 Master에 자동 등록
- 5초 후부터 자동으로 트래픽 분산 시작

### 서버 제거 (무중단 축소)

```bash
# Slave 1대 제거 (5 → 4대)
docker-compose up -d --scale slave=4 --no-recreate
```

**자동으로**:
- 제거된 Slave의 기존 시청자는 끊김
- 새 접속은 남은 Slave로 자동 분산

### 장애 복구

```bash
# 문제가 생긴 Slave 재시작
docker-compose restart airclass-slave-2

# 또는 특정 컨테이너만 재생성
docker-compose up -d --force-recreate airclass-slave-2
```

### 전체 재시작

```bash
# 무중단 재시작 (1대씩 순차 재시작)
docker-compose up -d --no-deps --scale slave=3 slave
docker-compose restart master

# 전체 재시작 (서비스 중단)
docker-compose restart
```

### 백업

```bash
# 설정 파일 백업
tar -czf airclass-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  .env \
  backend/mediamtx.yml

# 로그 백업
docker-compose logs > airclass-logs-$(date +%Y%m%d).log
```

---

## 🛠️ 문제 해결

### 문제 1: Slave가 Master에 등록 안 됨

**증상**:
```bash
docker-compose logs slave | grep "Failed to register"
```

**원인**: Master URL 잘못 설정 또는 네트워크 문제

**해결**:
```bash
# Master 접속 가능한지 확인
docker-compose exec slave curl -v http://master:8000/health

# 안 되면 네트워크 재생성
docker-compose down
docker-compose up -d
```

### 문제 2: "No healthy nodes available"

**증상**: 학생이 접속 시 503 에러

**원인**: 모든 Slave가 offline 또는 과부하

**해결**:
```bash
# 1. Slave 상태 확인
curl http://localhost:8000/cluster/nodes | jq '.nodes[] | {name, status}'

# 2. Offline 노드 재시작
docker-compose restart airclass-slave-1

# 3. 또는 Slave 추가
docker-compose up -d --scale slave=5
```

### 문제 3: 특정 Slave만 과부하

**증상**: 한 Slave만 150명, 나머지는 10명

**원인**: Heartbeat 전송 실패로 Master가 로드 감지 못함

**해결**:
```bash
# 문제 Slave 재시작
docker-compose restart airclass-slave-2

# 로그 확인
docker-compose logs -f airclass-slave-2 | grep heartbeat
```

### 문제 4: MediaMTX가 시작 안 됨

**증상**:
```
curl: (7) Failed to connect to localhost port 1935
```

**원인**: 포트 충돌 또는 권한 문제

**해결**:
```bash
# 1. 포트 사용 확인
sudo lsof -i :1935
sudo lsof -i :8888

# 2. 충돌 프로세스 종료 후 재시작
docker-compose restart

# 3. 권한 문제 시
chmod +x backend/docker-entrypoint.sh
chmod +x backend/mediamtx
docker-compose build --no-cache
docker-compose up -d
```

---

## 🎯 성능 튜닝

### 1. Slave당 최대 연결 수 조정

```yaml
# docker-compose.yml
services:
  slave:
    environment:
      MAX_CONNECTIONS: 200  # 기본 150 → 200
```

### 2. CPU/메모리 제한 조정

```yaml
services:
  slave:
    deploy:
      resources:
        limits:
          cpus: '4.0'      # 기본 2.0 → 4.0
          memory: 4G       # 기본 2G → 4G
```

### 3. MediaMTX 설정 최적화

```yaml
# backend/mediamtx.yml
hlsSegmentCount: 5        # 지연시간 감소 (7 → 5)
hlsSegmentDuration: 2s    # 안정성 증가 (1s → 2s)
```

### 4. 네트워크 대역폭 제한

```yaml
services:
  slave:
    deploy:
      resources:
        limits:
          # 네트워크 제한 (tc 명령어 사용)
          network: 200m  # 200 Mbps
```

---

## 📈 확장 시나리오

### 시나리오 1: 100명 → 500명 확장

```bash
# 현재: Master 1 + Slave 1 (100명)
docker-compose ps

# 목표: 500명 지원

# Step 1: Slave 3대 추가 (총 4대 = 600명 수용)
docker-compose up -d --scale slave=4

# Step 2: 확인
curl http://localhost:8000/cluster/nodes | jq '.total_capacity'
# 출력: 600

# 완료! 자동으로 분산됨
```

### 시나리오 2: 여러 물리 서버에 분산

**환경**: 서버 4대 (각각 IP 다름)

```bash
# 서버 1 (192.168.1.10): Master
docker-compose up -d master

# 서버 2 (192.168.1.11): Slave 2대
MASTER_URL=http://192.168.1.10:8000 \
NODE_HOST=192.168.1.11 \
docker-compose up -d --scale slave=2 --no-deps slave

# 서버 3 (192.168.1.12): Slave 2대
MASTER_URL=http://192.168.1.10:8000 \
NODE_HOST=192.168.1.12 \
docker-compose up -d --scale slave=2 --no-deps slave

# 서버 4 (192.168.1.13): Slave 2대
MASTER_URL=http://192.168.1.10:8000 \
NODE_HOST=192.168.1.13 \
docker-compose up -d --scale slave=2 --no-deps slave

# 총: Master 1 + Slave 6 = 900명 수용
```

---

## 🔐 보안 설정

### 1. JWT 비밀키 변경

```bash
# 강력한 랜덤 키 생성
openssl rand -hex 32 > .jwt_secret

# .env에 적용
echo "JWT_SECRET_KEY=$(cat .jwt_secret)" >> .env

# 재시작
docker-compose up -d
```

### 2. 방화벽 설정

```bash
# Master 포트만 외부 노출 (8000)
# Slave는 내부 네트워크만 (RTMP 1935, HLS 8888)

sudo ufw allow 8000/tcp
sudo ufw enable
```

### 3. HTTPS 적용 (nginx reverse proxy)

```nginx
# /etc/nginx/sites-available/airclass
server {
    listen 443 ssl;
    server_name stream.yourschool.com;
    
    ssl_certificate /etc/letsencrypt/live/yourschool.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourschool.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📚 다음 단계

1. ✅ **모니터링 설정**: Prometheus + Grafana
2. ✅ **자동 확장**: Kubernetes 배포 (고급)
3. ✅ **CDN 연동**: Cloudflare Stream 통합
4. ✅ **녹화 기능**: HLS 세그먼트 자동 저장

---

## 💡 팁

### 개발 환경에서 빠르게 테스트

```bash
# Standalone 모드로 1초 시작
docker-compose -f docker-compose.simple.yml up

# 코드 수정 후 빠른 재빌드
docker-compose build --no-cache backend
docker-compose up -d
```

### 프로덕션 배포 체크리스트

- [ ] JWT 비밀키 변경
- [ ] 방화벽 설정
- [ ] 백업 스크립트 설정
- [ ] 모니터링 대시보드 구성
- [ ] 부하 테스트 수행 (100명 동시 접속)
- [ ] 장애 복구 테스트
- [ ] 문서화 (운영 매뉴얼)

---

**작성**: AIRClass 개발팀  
**최종 수정**: 2026-01-22  
**버전**: 2.0.0
