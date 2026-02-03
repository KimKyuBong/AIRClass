# AIRClass 백엔드 개발 과제 현황

**작성일:** 2026-02-03  
**프로젝트:** AIRClass - 실시간 WebRTC 스트리밍 교육 플랫폼  
**기술 스택:** FastAPI + MongoDB + Redis + MediaMTX

---

## 📊 전체 진행 상황

```
전체 API 라우터: 12개
├─ ✅ 완료 (테스트 포함): 10개 (83%)
├─ 🔄 진행 중:           1개 (8%)
└─ ❌ 미시작:            1개 (8%)

전체 진행률: ~92%
```

---

## ✅ 완료된 작업

### Phase 1: 백엔드 모듈화 (100% 완료)

**목표:** 1,227줄의 monolithic main.py를 기능별 모듈로 분리

**결과:**
```
backend/
├── core/               # 핵심 기능
│   ├── database.py    ✅ MongoDB 비동기 작업
│   ├── cache.py       ✅ Redis 작업
│   ├── cluster.py     ✅ 다중 노드 클러스터 관리
│   ├── discovery.py   ✅ 노드 자동 탐색
│   ├── messaging.py   ✅ 메시징 큐
│   ├── ai_keys.py     ✅ 교사 AI 키 관리
│   └── metrics.py     ✅ Prometheus 메트릭
├── services/          # 비즈니스 로직
│   ├── ai/
│   │   ├── feedback.py    ✅ AI 피드백
│   │   ├── nlp.py         ✅ 자연어 처리
│   │   ├── vision.py      ✅ 이미지 분석
│   │   └── gemini.py      ✅ Gemini API
│   ├── engagement_service.py     ✅ 참여도 계산
│   ├── engagement_listener.py    ✅ 참여도 리스너
│   ├── recording_service.py      ✅ 녹화 관리
│   └── vod_service.py            ✅ VOD 저장소
├── routers/           # API 엔드포인트 (12개)
├── schemas/           # Pydantic 모델
│   ├── chat.py        ✅ 채팅 스키마
│   ├── engagement.py  ✅ 참여도 스키마
│   ├── quiz.py        ✅ 퀴즈 스키마
│   ├── session.py     ✅ 세션 스키마
│   └── common.py      ✅ 공통 스키마
├── utils/             # 유틸리티
│   ├── jwt_auth.py    ✅ JWT 인증
│   ├── mediamtx.py    ✅ MediaMTX 유틸
│   ├── network.py     ✅ 네트워크 유틸
│   ├── qr_code.py     ✅ QR 코드
│   ├── websocket.py   ✅ WebSocket 관리
│   └── stream_relay.py ✅ 스트림 릴레이
└── tests/             # 테스트 코드
    ├── unit/          ✅ 단위 테스트
    ├── integration/   ✅ 통합 테스트
    ├── routers/       ✅ 라우터 테스트
    └── load/          ✅ 부하 테스트
```

**성과:**
- main.py: 1,227줄 → 330줄 (-76.4%)
- 루트 Python 파일: 16개 → 2개 (-87.5%)
- 코드 가독성 및 유지보수성 향상

---

### Phase 2: MongoDB 통합 (100% 완료)

**작업 내용:**

1. **Docker 환경 설정**
   ```yaml
   # docker-compose.yml
   mongodb:
     image: mongo:7
     environment:
       MONGO_INITDB_ROOT_USERNAME: airclass
       MONGO_INITDB_ROOT_PASSWORD: airclass2025
     ports:
       - "27017:27017"
   ```

2. **데이터베이스 매니저 구현**
   - `core/database.py` - Motor 기반 비동기 MongoDB 클라이언트
   - Quiz CRUD 메서드
   - Engagement 데이터 저장
   - Recording 메타데이터 관리
   - VOD 파일 정보 저장

3. **스키마 정의**
   - `schemas/quiz.py` - Quiz, QuizResponse 모델
   - `schemas/engagement.py` - EngagementData 모델
   - `schemas/session.py` - Session 모델

**결과:** ✅ MongoDB 완전 통합

---

### Phase 3: API 테스트 구축 (10개 라우터 완료)

**통과한 테스트: 201개**

| 라우터 | 테스트 수 | 상태 | 주요 기능 |
|--------|-----------|------|-----------|
| `auth.py` | 19 | ✅ PASS | JWT 토큰, 클러스터 로드 밸런싱 |
| `system.py` | 18 | ✅ PASS | 헬스체크, MediaMTX 연동 |
| `cluster.py` | 22 | ✅ PASS | 노드 등록, HMAC 인증 |
| `monitoring.py` | 13 | ✅ PASS | Prometheus 메트릭 |
| `mediamtx_auth.py` | 26 | ✅ PASS | RTMP/WebRTC/RTSP 인증 |
| `quiz.py` | 18 | ✅ PASS | 퀴즈 생성/발행/응답/통계 |
| `websocket_routes.py` | 14 | ✅ PASS | 채팅/퀴즈 푸시/참여도 스트리밍 |
| `recording.py` | 23 | ✅ PASS | 녹화 시작/중지/상태/삭제 |
| `ai_analysis.py` | 31 | ✅ PASS | AI 분석 (Vision, NLP, Feedback) |
| `engagement.py` | 17 | ✅ PASS | 참여도 분석 |

**테스트 커버리지:** 주요 모듈 90%+

---

## 🔄 진행 중인 작업

### VOD API 테스트 수정 (90% 완료)

**현재 상태:**
- ✅ API 구현 완료 (`routers/vod.py`)
- ✅ 25개 테스트 작성
- ⚠️ FastAPI Depends 의존성 주입 모킹 이슈

**블로커:**
```python
# 문제: 테스트에서 Depends(get_vod_service)를 모킹할 때
# FastAPI가 실제 의존성을 주입하려고 시도함

# 해결 방법 (진행 중):
# 1. app.dependency_overrides 사용
# 2. pytest fixture로 mock 서비스 주입
# 3. 테스트용 TestClient 설정
```

**예상 해결 시간:** 2-3시간

**남은 작업:**
1. `conftest.py`에 `mock_vod_service` fixture 추가
2. `app.dependency_overrides` 설정
3. 25개 테스트 실행 및 검증

---

## ❌ 미시작 작업

### Dashboard API (`dashboard.py`) ⭐⭐⭐

**기능:**
- 수업 통계 대시보드
- 참여도 요약
- 퀴즈 통계
- 녹화 목록
- 시스템 상태

**예상 소요:** 1일

**의존성:**
- ✅ Quiz API (완료)
- ✅ Engagement API (완료)
- ✅ Recording API (완료)
- 🔄 VOD API (진행 중)

**상태:** ❌ 미시작 (테스트 파일 존재, 구현 필요)

**우선순위:** 중간 (프로덕션 배포 전 필수)

---

## 🎯 권장 작업 순서

### ✅ Week 1-2: 핵심 기능 완료 (완료)
```
✅ 백엔드 구조 계층화
✅ MongoDB 통합
✅ Auth, System, Cluster API
✅ Monitoring, MediaMTX Auth
✅ Quiz API (비동기 fixture 구현)
✅ WebSocket 구현 (퀴즈 푸시, 참여도 스트리밍)
✅ Recording API (23 tests)
✅ AI Analysis API (31 tests)
✅ Engagement API (17 tests)
```

### 🔄 Week 3: VOD 및 Dashboard (진행 중)
```
🔄 Day 1-2: VOD 테스트 의존성 이슈 해결 (진행 중)
❌ Day 3-4: Dashboard API 구현 + 테스트
❌ Day 5:   통합 테스트, 버그 수정
```

### ❌ Week 4: 프로덕션 준비 (계획)
```
❌ Day 1-2: 부하 테스트 (100명 동시 접속)
❌ Day 3:   HTTPS/TLS 설정
❌ Day 4:   Grafana 대시보드
❌ Day 5:   최종 검수
```

---

## 📝 즉시 실행 가능한 명령어

### MongoDB 확인
```bash
# MongoDB 실행 확인
docker ps | grep mongodb

# MongoDB 연결 테스트
docker exec airclass-mongodb mongosh \
  --username airclass \
  --password airclass2025 \
  --authenticationDatabase admin \
  --eval "db.adminCommand('ping')"
```

### 테스트 실행
```bash
# 백엔드 디렉토리로 이동
cd /Users/hwansi/Project/AirClass/backend
source .venv/bin/activate

# 환경 변수 설정
export MONGO_URL="mongodb://airclass:airclass2025@localhost:27017/airclass_test?authSource=admin"

# 전체 테스트 실행 (201개)
pytest tests/ -v

# 특정 라우터 테스트
pytest tests/routers/test_auth.py -v
pytest tests/routers/test_quiz.py -v
pytest tests/routers/test_recording.py -v

# VOD 테스트 (현재 실패)
pytest tests/routers/test_vod.py -v --tb=short
```

### 클러스터 상태 확인
```bash
# 노드 목록
curl http://localhost:8000/cluster/nodes | jq

# 시스템 상태
curl http://localhost:8000/health | jq

# JWT 토큰 발급
curl -X POST "http://localhost:8000/api/token?user_type=student&user_id=test001&action=read"
```

---

## 🎓 완료 기준

### VOD API
- [x] API 구현 완료
- [x] 25개 테스트 작성
- [ ] 25개 테스트 통과
- [ ] 코드 리뷰 완료

### Dashboard API
- [ ] API 구현 완료
- [ ] 15-20개 테스트 작성
- [ ] 테스트 100% 통과
- [ ] 문서화 완료

### 프로덕션 준비
- [x] 201개 테스트 통과
- [ ] VOD, Dashboard 완료
- [ ] 부하 테스트 (100명+)
- [ ] HTTPS/TLS 설정
- [ ] Grafana 대시보드

---

## 📚 참고 문서

### 기술 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Motor (MongoDB Async) 문서](https://motor.readthedocs.io/)
- [pytest-asyncio 가이드](https://pytest-asyncio.readthedocs.io/)
- [HTTPX AsyncClient](https://www.python-httpx.org/async/)

### 프로젝트 문서
- `PROJECT_STRUCTURE.md` - 전체 구조
- `PROGRESS.md` - 진행 상황
- `TEST_ANALYSIS_REPORT.md` - 테스트 분석
- `docs/CLUSTER_ARCHITECTURE.md` - 클러스터 구조

---

## 🤝 의사결정 필요

### 즉시 결정해야 할 사항

**질문 1: VOD 테스트 해결 우선순위**
- [ ] 옵션 1: 지금 즉시 해결 (2-3시간 소요)
- [ ] 옵션 2: Dashboard 먼저 구현 후 해결

**질문 2: Dashboard API 범위**
- [ ] 옵션 1: 기본 통계만 (빠른 완성)
- [ ] 옵션 2: 상세 분석 포함 (시간 소요)

**질문 3: 프로덕션 배포 일정**
- [ ] 옵션 1: VOD/Dashboard 완료 후 즉시
- [ ] 옵션 2: 부하 테스트 완료 후

---

## 📞 문의 사항

### 기술적 질문
1. VOD 테스트 Depends 모킹 방법
2. Dashboard API 통계 범위
3. 부하 테스트 목표 (동시 접속자 수)

### 우선순위 조정
- 현재 우선순위: VOD 테스트 → Dashboard → 프로덕션
- 조정 필요 시 협의

---

## 📈 성과 지표

### 완료된 작업
- ✅ 코드 구조 계층화 (76% 코드 감소)
- ✅ MongoDB 완전 통합
- ✅ 201개 테스트 100% 통과
- ✅ 10개 API 라우터 완성

### 남은 작업
- 🔄 VOD 테스트 수정 (90% 완료)
- ❌ Dashboard API (미시작)
- ❌ 프로덕션 배포 준비

### 전체 진행률
**92% 완료** (10/12 라우터, 201개 테스트 통과)

---

**다음 회의 안건:**
1. VOD 테스트 해결 방법 논의
2. Dashboard API 범위 확정
3. 프로덕션 배포 일정 협의

**작성자:** AIRClass Team  
**최종 업데이트:** 2026-02-03
