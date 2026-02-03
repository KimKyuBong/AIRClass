# AIRClass 백엔드 개발 과제 현황

**작성일:** 2025-01-27  
**프로젝트:** AIRClass - 실시간 WebRTC 스트리밍 교육 플랫폼  
**기술 스택:** FastAPI + MongoDB + Redis + MediaMTX

---

## 📊 전체 진행 상황

```
전체 API 라우터: 12개
├─ ✅ 완료 (테스트 포함): 9개 (75%)
├─ 🔄 진행 중:           1개 (8%)
└─ ❌ 미시작:            2개 (17%)

전체 진행률: ~80%
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
│   ├── ai_keys.py     ✅ 교사 AI 키 관리
│   └── metrics.py     ✅ Prometheus 메트릭
├── services/          # 비즈니스 로직
│   ├── ai/
│   │   ├── feedback.py
│   │   ├── nlp.py
│   │   ├── vision.py
│   │   └── gemini.py
│   ├── engagement_service.py
│   ├── recording_service.py
│   └── vod_service.py
├── routers/           # API 엔드포인트 (12개)
├── schemas/           # Pydantic 모델
└── tests/             # 테스트 코드
```

**성과:**
- main.py: 1,227줄 → 290줄 (-76.4%)
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
   - Quiz CRUD 메서드 추가:
     - `create_quiz()`
     - `get_quiz()`
     - `delete_quiz()`
     - `update_quiz_status()`
     - `save_quiz_response()`
     - `get_quiz_stats()`
     - `get_session_quizzes()`

3. **스키마 정의**
   - `schemas/quiz.py` - Quiz, QuizResponse 모델

---

### Phase 3: API 테스트 구축 (9개 라우터 완료)

**통과한 테스트: 201개**

| 라우터 | 테스트 수 | 상태 | 주요 기능 |
|--------|-----------|------|-----------|
| `auth.py` | 19 | ✅ PASS | 토큰 생성, 클러스터 로드 밸런싱 |
| `system.py` | 18 | ✅ PASS | 헬스체크, MediaMTX 연동 |
| `cluster.py` | 22 | ✅ PASS | 노드 등록, HMAC 인증 |
| `monitoring.py` | 13 | ✅ PASS | Prometheus 메트릭, 시청자 수 |
| `mediamtx_auth.py` | 26 | ✅ PASS | RTMP/WebRTC/RTSP 인증 |
| `quiz.py` | 18 | ✅ PASS | 퀴즈 생성/발행/응답/통계 |
| `websocket_routes.py` | 14 | ✅ PASS | 실시간 채팅/퀴즈 푸시/참여도 스트리밍 |
| `recording.py` | 23 | ✅ PASS | 녹화 시작/중지/상태/삭제 |
| `ai_analysis.py` | 31 | ✅ PASS | AI 분석 (Vision, NLP, Feedback) |
| `engagement.py` | 17 | ✅ PASS | 참여도 분석 |

---

## ✅ 최근 완료된 작업 (2025-02-03)

### Recording API 완료
- 23개 테스트 통과
- `routers/recording.py` 에러 핸들링 수정
- 녹화 시작/중지, HLS 저장, 상태 조회, 목록 관리

### VOD API 구현 (테스트 진행 중)
- API 구현 완료
- 25개 테스트 작성
- **블로커:** FastAPI Depends 의존성 주입 모킹 이슈

### WebSocket API 구현 완료

**구현 내용:**
1. ✅ 퀴즈 푸시 기능
   - Quiz 발행 시 모든 학생에게 WebSocket으로 알림
   - `POST /ws/broadcast/quiz` HTTP 엔드포인트
   - `quiz.py`의 publish_quiz와 통합

2. ✅ 참여도 스트리밍 기능
   - 학생 참여도 업데이트를 교사/모니터에게 실시간 전송
   - `POST /ws/broadcast/engagement` HTTP 엔드포인트
   - `engagement.py`의 track_chat/track_quiz와 통합

3. ✅ WebSocket 연결 관리
   - 교사/학생/모니터 연결 상태 관리
   - `GET /ws/status` 상태 조회 API

**테스트 결과:**
- 14개 WebSocket 테스트 모두 통과
- HTTP 브로드캐스트 엔드포인트 검증
- 기존 기능 유지 (실시간 채팅)

**핵심 변경사항:**
```python
# utils/websocket.py
async def broadcast_quiz(quiz_data: dict):
    """퀴즈 발행 알림을 모든 학생에게 전송"""
    message = {"type": "quiz_published", "data": quiz_data}
    await self.send_to_all_students(message)

async def broadcast_engagement_update(engagement_data: dict):
    """참여도 업데이트를 교사/모니터에게 전송"""
    message = {"type": "engagement_update", "data": engagement_data}
    await self.teacher.send_json(message)
    await self.send_to_monitors(message)
```

---

### Quiz API 블로커 해결 (2025-02-03 완료)

**문제:**
- 이벤트 루프 충돌로 인한 테스트 실패
- `RuntimeError: Task got Future attached to a different loop`

**해결 방법 (옵션 1 선택):**
1. ✅ `conftest.py` 비동기 fixture로 변환
   - `@pytest_asyncio.fixture` 사용
   - `async with AsyncClient` 패턴 적용
   - DB 초기화 로직 추가
2. ✅ `pytest.ini` 생성 (`asyncio_mode = auto`)
3. ✅ 18개 Quiz 테스트 모두 통과

**결과:**
- Quiz API 완전히 작동
- 실제 MongoDB 연동 테스트
- 프로덕션 환경과 동일한 조건 검증

---

## ❌ 미시작 작업 (6개 라우터)

### 우선순위 1: 핵심 기능

#### 1. Recording API (`recording.py`) ⭐⭐⭐⭐
- **기능:** 수업 녹화, HLS 스트림 저장
- **예상 소요:** 1일
- **의존성:** MediaMTX 연동
- **상태:** ❌ 미시작

---

### 우선순위 2: 부가 기능

#### 2. VOD API (`vod.py`) ⭐⭐⭐
- **기능:** 녹화 영상 관리, 재생
- **예상 소요:** 1일
- **의존성:** Recording 완료 필요
- **상태:** ❌ 미시작

#### 3. Dashboard API (`dashboard.py`) ⭐⭐⭐
- **기능:** 통계 대시보드, 수업 요약
- **예상 소요:** 1일
- **의존성:** 모든 데이터 수집 완료
- **상태:** ❌ 미시작 (테스트 파일 존재, 구현 필요)

---

## 🎯 권장 작업 순서

### ~~Week 1: Quiz 블로커 해결 + WebSocket~~ ✅ 완료
```
✅ Day 1-2: Quiz 테스트 수정 (비동기 fixture 구현)
✅ Day 3:   WebSocket 구현 + 테스트 (퀴즈 푸시, 참여도 스트리밍)
✅ Day 4:   Recording API + 테스트 (23 tests)
✅ Day 5:   VOD API 구현 (25 tests 작성, 의존성 이슈)
```

### Week 2: 완료 작업
```
Day 6: VOD 테스트 의존성 이슈 해결
Day 7: Dashboard API + 테스트
Day 8: 통합 테스트, 버그 수정
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

# 통과하는 테스트 실행
pytest tests/routers/test_auth.py -v
pytest tests/routers/test_system.py -v
pytest tests/routers/test_cluster.py -v
pytest tests/routers/test_monitoring.py -v
pytest tests/routers/test_mediamtx_auth.py -v

# Quiz 테스트 실행 (현재 실패)
pytest tests/routers/test_quiz.py -v --tb=short
```

---

## 🤝 의사결정 필요

### 즉시 결정해야 할 사항

**질문 1: Quiz 테스트 해결 방법**
- [ ] 옵션 1: 비동기 테스트 제대로 구현 (2-3시간, 완전한 테스트)
- [ ] 옵션 2: Mock 사용 (30분, 빠른 진행)

**질문 2: 다음 작업 우선순위**
- [ ] WebSocket 먼저 (실시간 기능 완성)
- [ ] Engagement 먼저 (AI 분석 기능)
- [ ] Recording 먼저 (녹화 기능)

---

## 📚 참고 문서

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Motor (MongoDB Async) 문서](https://motor.readthedocs.io/)
- [pytest-asyncio 가이드](https://pytest-asyncio.readthedocs.io/)
- [HTTPX AsyncClient](https://www.python-httpx.org/async/)

---

## 📞 문의 사항

- 기술적 질문: Quiz 테스트 이벤트 루프 충돌 해결 방법
- 우선순위 조정 필요 시 상의

**다음 회의 안건:**
1. Quiz 테스트 해결 방법 선택
2. WebSocket 구현 일정 협의
3. AI 분석 기능 범위 확정
