# AirClass 아키텍처 - FastAPI 제어 LiveKit 클러스터

## 🎯 설계 철학

**FastAPI가 LiveKit을 제어하는 통합 노드 아키텍처**

각 노드(Main/Sub)는 **FastAPI + LiveKit**을 함께 실행하며, FastAPI가 노드 역할에 따라 LiveKit 설정을 동적으로 생성하고 프로세스를 관리합니다.

## 📐 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────┐
│  Main Node (MODE=main)                              │
│  ┌──────────────────┐    ┌─────────────────────┐   │
│  │  FastAPI :8000   │◄───│  LiveKit :7880      │   │
│  │  - 클러스터 관리  │    │  - RTC: 50000-50020 │   │
│  │  - 노드 발견      │    │  - WebSocket        │   │
│  │  - LiveKit 설정   │    │  - Room 관리        │   │
│  │    동적 생성      │    │                     │   │
│  │  - 프로세스 제어  │    │  (subprocess)       │   │
│  └──────────────────┘    └─────────────────────┘   │
└─────────────────────────────────────────────────────┘
              ↓ (mDNS + heartbeat)
┌─────────────────────────────────────────────────────┐
│  Sub Node 1 (MODE=sub, node-1)                      │
│  ┌──────────────────┐    ┌─────────────────────┐   │
│  │  FastAPI :8001   │◄───│  LiveKit :7890      │   │
│  │  - Main 등록     │    │  - RTC: 51000-51020 │   │
│  │  - LiveKit 설정   │    │  - 부하 기반 선택    │   │
│  │    동적 생성      │    │  - sysload_limit    │   │
│  │  - 프로세스 제어  │    │                     │   │
│  └──────────────────┘    └─────────────────────┘   │
└─────────────────────────────────────────────────────┘
              │
         (Redis 공유)
              ↓
┌─────────────────────────────────────────────────────┐
│  Redis :6379 - LiveKit Cluster 동기화               │
│  - Room 상태 공유                                    │
│  - Participant 정보                                  │
│  - 노드 간 메시징                                    │
└─────────────────────────────────────────────────────┘
```

## 🧩 주요 컴포넌트

### 1. LiveKit 설정 동적 생성 (`backend/core/livekit_config.py`)

**역할**: 노드 ID와 모드에 따라 LiveKit YAML 설정을 동적으로 생성

**포트 자동 계산**:
- `main`: LiveKit 7880, RTC 50000-50020
- `node-1`: LiveKit 7890, RTC 51000-51020
- `node-2`: LiveKit 7900, RTC 52000-52020
- `node-3`: LiveKit 7910, RTC 53000-53020

**클러스터 설정**:
- Redis 기반 room 동기화
- Sub 노드: `sysload_limit: 0.7` (CPU 70% 이하만 선택)
- 부하 기반 자동 라우팅

### 2. LiveKit 프로세스 관리자 (`backend/core/livekit_manager.py`)

**역할**: LiveKit 서버를 subprocess로 실행/종료

**기능**:
- FastAPI lifespan에서 LiveKit 시작/종료
- 로그 모니터링 (비동기)
- Graceful shutdown (SIGTERM → 10초 대기 → SIGKILL)
- 헬스체크 및 재시작

### 3. 클러스터 관리자 (`backend/core/cluster.py`)

**Main Node**:
- `ClusterManager`: Sub 노드 등록, 헬스체크, Rendezvous Hashing
- mDNS 광고 (`_airclass._tcp.local`)
- 노드 통계 수집 (5초마다 heartbeat)

**Sub Node**:
- `SubNodeClient`: Main 노드 자동 발견 및 등록
- HMAC-SHA256 인증
- 주기적 통계 전송 (CPU, 메모리, 연결 수)

### 4. FastAPI 라이프사이클 (`backend/main.py`)

**Startup 순서**:
1. 클러스터 모드 초기화
2. **LiveKit 서버 시작** (중요: 실패 시 전체 시작 중단)
3. 백엔드 서비스 초기화 (Cache, DB, Recording, AI 등)

**Shutdown 순서**:
1. **LiveKit 서버 종료** (graceful)
2. 클러스터 종료

## 🔧 설정 파일

### `backend/config.py`

```python
# LiveKit 설정
LIVEKIT_API_KEY = "AIRClass2025DevKey123456789ABC"
LIVEKIT_API_SECRET = "AIRclass2025DevSecretXYZ987654321"
LIVEKIT_URL = "ws://localhost:7880"
LIVEKIT_BINARY = "/usr/local/bin/livekit-server"  # Docker 내부 경로

# 포트 (노드별 자동 계산)
LIVEKIT_PORT = 7880
LIVEKIT_RTC_PORT_START = 50000
LIVEKIT_RTC_PORT_END = 50020

# 클러스터
MODE = "main"  # main | sub | standalone
NODE_NAME = "main"
REDIS_URL = "redis://redis:6379"
```

### `docker-compose.yml`

**Main Node 환경변수**:
```yaml
environment:
  MODE: main
  NODE_NAME: main
  LIVEKIT_PORT: 7880
  LIVEKIT_RTC_PORT_START: 50000
  LIVEKIT_RTC_PORT_END: 50020
```

**Sub Node 환경변수**:
```yaml
environment:
  MODE: sub
  NODE_NAME: node-1
  MAIN_NODE_URL: http://main:8000
  LIVEKIT_PORT: 7890
  LIVEKIT_RTC_PORT_START: 51000
  LIVEKIT_RTC_PORT_END: 51020
```

## 🚀 실행 방법

### 로컬 개발 (Standalone)

```bash
# 1. Redis 시작
docker run -d -p 6379:6379 redis:7-alpine

# 2. MongoDB 시작
docker run -d -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=airclass \
  -e MONGO_INITDB_ROOT_PASSWORD=airclass2025 \
  mongo:7

# 3. LiveKit 바이너리 설치 (macOS/Linux)
wget https://github.com/livekit/livekit/releases/download/v1.5.3/livekit-server_v1.5.3_linux_amd64.tar.gz
tar -xzf livekit-server_v1.5.3_linux_amd64.tar.gz
sudo mv livekit-server /usr/local/bin/

# 4. Backend 시작
cd backend
export MODE=standalone
export NODE_NAME=dev
export REDIS_URL=redis://localhost:6379
python main.py

# 5. Frontend 시작
cd frontend
npm install
npm run dev
```

### Docker Compose (Main + Sub)

```bash
# 1. Main 노드만 시작
docker-compose up main frontend mongodb redis

# 2. Sub 노드 추가 (별도 터미널)
docker-compose up -d sub-1

# 3. 전체 종료
docker-compose down
```

## 📊 노드 상태 확인

### API 엔드포인트

```bash
# 클러스터 상태
curl http://localhost:8000/api/cluster/status

# Main 노드 정보
curl http://localhost:8000/api/cluster/nodes

# LiveKit Room 목록
curl http://localhost:8000/api/livekit/rooms
```

### 로그 확인

```bash
# FastAPI 로그
docker logs -f airclass-main-node

# LiveKit 로그 (FastAPI 로그에 포함됨)
# [LiveKit] 접두사로 출력
```

## 🔍 트러블슈팅

### LiveKit 시작 실패

**증상**: `LiveKit 서버 시작 실패` 에러
**원인**: LiveKit 바이너리 없음
**해결**:
```bash
# Dockerfile 빌드 시 자동 설치됨
# 로컬 개발 시:
wget https://github.com/livekit/livekit/releases/download/v1.5.3/livekit-server_v1.5.3_linux_amd64.tar.gz
tar -xzf livekit-server_v1.5.3_linux_amd64.tar.gz
sudo mv livekit-server /usr/local/bin/
```

### Sub 노드가 Main을 찾지 못함

**증상**: `Main Node not found` 에러
**원인**: mDNS 실패 또는 `MAIN_NODE_URL` 미설정
**해결**:
```bash
# docker-compose에서는 자동 설정됨
export MAIN_NODE_URL=http://main:8000

# 로컬 개발 시 명시적 설정 필요
export MAIN_NODE_URL=http://localhost:8000
```

### 포트 충돌

**증상**: `Address already in use`
**원인**: LiveKit RTC 포트 중복
**해결**:
```bash
# docker-compose.yml에서 포트 범위 수정
# Main: 50000-50020
# Sub1: 51000-51020
# Sub2: 52000-52020
```

## 🎓 핵심 개념

### Rendezvous Hashing

**목적**: 일관성 있는 노드 선택 (Sticky Session)
**구현**: `ClusterManager.get_node_rendezvous()`
**알고리즘**: `hash(stream_id:node_id)` 최대값 노드 선택

### sysload_limit

**목적**: 과부하 노드 제외
**설정**: `livekit.yaml` - `rtc.node_selector.sysload_limit: 0.7`
**효과**: CPU 70% 초과 노드는 새 participant 수신 거부

### Redis 기반 클러스터링

**목적**: LiveKit 노드 간 room 상태 공유
**설정**: `redis.use_cluster: false` (단일 Redis 사용)
**효과**: 모든 노드가 같은 room 정보 조회 가능

## 📚 참고 자료

- [LiveKit 공식 문서](https://docs.livekit.io/)
- [LiveKit 클러스터 설정](https://docs.livekit.io/realtime/server/scaling/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)

## 🛠 개발 로드맵

- [x] LiveKit 설정 동적 생성
- [x] LiveKit 프로세스 관리자
- [x] cluster.py MediaMTX 레거시 제거
- [x] main.py lifespan 통합
- [x] config.py LiveKit 설정
- [x] docker-compose.yml 수정
- [ ] Frontend LiveKit 클라이언트 개선
- [ ] 녹화 서비스 LiveKit 통합
- [ ] AI 분석 LiveKit 스트림 연동
- [ ] 모니터링 대시보드 LiveKit 메트릭 추가
