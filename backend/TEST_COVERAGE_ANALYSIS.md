# AIRClass Backend Test Coverage Analysis

## 현재 테스트 구조

### 테스트 파일 현황 (9개)
1. `test_ai_analysis.py` - 486 lines, 31 test cases
2. `test_confusion_detection.py` - 344 lines, 19 test cases  
3. `test_dashboard_router.py` - 415 lines, 23 test cases
4. `test_database_performance.py` - 262 lines, 8 test cases
5. `test_engagement_calculator.py` - 391 lines, 32 test cases
6. `test_engagement_router.py` - 334 lines, 18 test cases
7. `test_integration_engagement.py` - 475 lines, 11 test cases
8. `test_recording.py` - 334 lines, 18 test cases
9. `test_teacher_ai_keys.py` - 32 lines, 2 test cases

**총 162 test cases**

---

## 라우터별 엔드포인트 현황 (12개 라우터)

| Router | Endpoints | 현재 테스트 | 커버리지 | 상태 |
|--------|-----------|------------|----------|------|
| ai_analysis.py | 16 | test_ai_analysis.py (31 cases) | ✅ GOOD | 충분 |
| auth.py | 1 | ❌ MISSING | ❌ 0% | 없음 |
| cluster.py | 4 | ❌ MISSING | ❌ 0% | 없음 |
| dashboard.py | 6 | test_dashboard_router.py (23 cases) | ✅ GOOD | 충분 |
| engagement.py | 12 | test_engagement_router.py (18 cases) | ⚠️ PARTIAL | 부족 |
| mediamtx_auth.py | 1 | ❌ MISSING | ❌ 0% | 없음 |
| monitoring.py | 2 | ❌ MISSING | ❌ 0% | 없음 |
| quiz.py | 6 | ❌ MISSING | ❌ 0% | 없음 |
| recording.py | 7 | test_recording.py (18 cases) | ⚠️ PARTIAL | services만 테스트 |
| system.py | 3 | ❌ MISSING | ❌ 0% | 없음 |
| vod.py | 9 | test_recording.py에 일부 포함 | ⚠️ PARTIAL | 부족 |
| websocket_routes.py | 3 | ❌ MISSING | ❌ 0% | 없음 |

---

## 주요 문제점

### 1. **라우터 테스트 누락** (7개 라우터 미테스트)
- ❌ `auth.py` - POST /api/token (클러스터 토큰 발급)
- ❌ `cluster.py` - 4개 클러스터 관리 엔드포인트
- ❌ `mediamtx_auth.py` - MediaMTX 인증
- ❌ `monitoring.py` - /metrics, /api/viewers
- ❌ `quiz.py` - 6개 퀴즈 엔드포인트
- ❌ `system.py` - /, /health, /api/status
- ❌ `websocket_routes.py` - 3개 WebSocket 엔드포인트

### 2. **테스트 파일 구조 문제**
- 현재: 평평한 구조 (tests/*.py)
- 문제: 라우터와 매칭되지 않음
- 일부 테스트는 services만 테스트 (router 미포함)

### 3. **Integration vs Unit Test 혼재**
- `test_integration_engagement.py` - 통합 테스트
- `test_engagement_calculator.py` - 유닛 테스트
- `test_engagement_router.py` - 라우터 테스트
- → 같은 기능에 대해 3개 파일로 분산

### 4. **Core/Services 테스트 누락**
- ✅ services/ai/* - test_ai_analysis.py
- ✅ services/recording_service.py - test_recording.py
- ✅ services/engagement_service.py - test_engagement_*.py
- ⚠️ core/database.py - test_database_performance.py (성능만)
- ❌ core/cache.py - 없음
- ❌ core/cluster.py - 없음
- ❌ core/messaging.py - 없음
- ❌ core/ai_keys.py - test_teacher_ai_keys.py (2 cases만)
- ❌ utils/* - 대부분 없음

---

## 권장 테스트 구조

```
tests/
├── conftest.py                  # 공통 fixtures
├── unit/                        # 단위 테스트
│   ├── core/
│   │   ├── test_cache.py
│   │   ├── test_cluster.py
│   │   ├── test_database.py
│   │   ├── test_messaging.py
│   │   ├── test_metrics.py
│   │   └── test_ai_keys.py
│   ├── utils/
│   │   ├── test_jwt_auth.py
│   │   ├── test_websocket.py
│   │   ├── test_network.py
│   │   └── test_qr_code.py
│   └── services/
│       ├── test_engagement_service.py
│       ├── test_recording_service.py
│       ├── test_vod_service.py
│       └── ai/
│           ├── test_feedback.py
│           ├── test_nlp.py
│           └── test_vision.py
│
├── routers/                     # API 엔드포인트 테스트
│   ├── test_ai_analysis.py     # ✅ 이미 존재
│   ├── test_auth.py             # 🆕 생성 필요
│   ├── test_cluster.py          # 🆕 생성 필요
│   ├── test_dashboard.py        # ✅ 이미 존재
│   ├── test_engagement.py       # ✅ 이미 존재
│   ├── test_mediamtx_auth.py    # 🆕 생성 필요
│   ├── test_monitoring.py       # 🆕 생성 필요
│   ├── test_quiz.py             # 🆕 생성 필요
│   ├── test_recording.py        # ✅ 이미 존재 (이동)
│   ├── test_system.py           # 🆕 생성 필요
│   ├── test_vod.py              # 🆕 생성 필요
│   └── test_websocket.py        # 🆕 생성 필요
│
├── integration/                 # 통합 테스트
│   ├── test_engagement_flow.py  # 기존 test_integration_engagement.py 이동
│   ├── test_quiz_flow.py        # 🆕 생성
│   └── test_streaming_flow.py   # 🆕 생성
│
└── load/                        # 로드 테스트 (✅ 이미 존재)
    ├── load_test_ai.py
    └── load_test_database.py
```

---

## 우선순위별 작업 계획

### Priority 1: 누락된 라우터 테스트 생성 (필수)
1. `tests/routers/test_quiz.py` - 퀴즈 핵심 기능
2. `tests/routers/test_auth.py` - 토큰 발급
3. `tests/routers/test_system.py` - 헬스체크
4. `tests/routers/test_cluster.py` - 클러스터 관리
5. `tests/routers/test_monitoring.py` - 메트릭/뷰어

### Priority 2: 기존 테스트 재구성
1. 현재 테스트 파일 → tests/routers/로 이동
2. services 테스트 → tests/unit/services/로 분리
3. integration 테스트 → tests/integration/로 이동

### Priority 3: Core/Utils 테스트 추가
1. `tests/unit/core/test_cache.py`
2. `tests/unit/core/test_cluster.py`
3. `tests/unit/utils/test_jwt_auth.py`
4. `tests/unit/utils/test_websocket.py`

---

## 테스트 커버리지 목표

| Category | Current | Target |
|----------|---------|--------|
| Routers | 33% (4/12) | **100% (12/12)** |
| Services | 60% (6/10) | **100% (10/10)** |
| Core | 20% (1/5) | **80% (4/5)** |
| Utils | 0% (0/6) | **60% (4/6)** |
| **Overall** | **40%** | **85%+** |

---

## 다음 단계

1. ✅ 이 분석 리포트 검토
2. 🔄 테스트 디렉토리 구조 재구성
3. 🆕 누락된 라우터 테스트 생성
4. ✅ 전체 테스트 실행 및 검증
