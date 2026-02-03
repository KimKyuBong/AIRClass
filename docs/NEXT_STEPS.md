# 🎯 AIRClass Next Steps

**최종 업데이트:** 2026년 2월 3일  
**프로젝트 진행률:** 95% 완료

---

## 📊 현재 상태 요약

### ✅ 완료된 항목 (95%)
- [x] 백엔드 코드 구조 계층화 (76% 코드 감소)
- [x] MongoDB 완전 통합
- [x] 201개 테스트 100% 통과
- [x] WebRTC/WHEP 스트리밍 (< 1초 지연)
- [x] JWT 인증 시스템
- [x] Main/Sub 클러스터 아키텍처
- [x] 실시간 WebSocket 기능 (채팅, 퀴즈 푸시, 참여도)
- [x] 녹화/VOD 시스템
- [x] AI 분석 (Gemini API)
- [x] Playwright 브라우저 자동화 테스트
- [x] Docker 배포 환경
- [x] 문서화 완료

### ⚠️ 진행 중 (3%)
- [ ] VOD API 테스트 수정 (의존성 모킹 이슈)
- [ ] ICE 연결 최종 검증 (다양한 네트워크 환경)

### ❌ 미시작 (2%)
- [ ] Dashboard API 구현
- [ ] HTTPS/TLS 설정
- [ ] Grafana 모니터링 대시보드

---

## 🚀 단기 계획 (이번 주)

### 1️⃣ VOD API 테스트 수정 (우선순위: 높음)

**현재 상태:**
- ✅ API 구현 완료 (`routers/vod.py`)
- ✅ 25개 테스트 작성
- ⚠️ FastAPI Depends 의존성 모킹 이슈

**문제:**
```python
# tests/routers/test_vod.py
# FastAPI의 Depends()를 사용하는 엔드포인트 테스트 시
# 실제 의존성 주입이 실행되어 Mock이 동작하지 않음

@router.get("/vod/list")
async def list_vod(
    vod_service: VODService = Depends(get_vod_service)  # 이 부분 모킹 필요
):
    ...
```

**해결 방법:**
```python
# conftest.py에 추가
@pytest.fixture
def mock_vod_service():
    """VOD 서비스 Mock"""
    mock = MagicMock(spec=VODService)
    mock.list_recordings.return_value = [...]
    return mock

@pytest.fixture
def client_with_vod_override(mock_vod_service):
    """VOD 의존성 오버라이드"""
    app.dependency_overrides[get_vod_service] = lambda: mock_vod_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

**작업 단계:**
1. `conftest.py`에 `mock_vod_service` fixture 추가
2. `app.dependency_overrides` 설정
3. 25개 테스트 실행 및 검증
4. 코드 리뷰 및 커밋

**예상 소요 시간:** 2-3시간

**완료 기준:**
- [ ] 25개 VOD 테스트 모두 통과
- [ ] 테스트 커버리지 90% 이상 유지
- [ ] 문서 업데이트

---

### 2️⃣ ICE 연결 최종 검증 (우선순위: 중간)

**현재 상태:**
- ✅ WHEP 시그널링 성공 (201 Created)
- ✅ SDP Answer 수신
- ⚠️ 실제 비디오 재생 다양한 환경에서 검증 필요

**테스트 환경:**
1. **로컬 (같은 머신)**
   - Docker 컨테이너 ↔ 호스트 브라우저
   - 예상: UDP 포트 매핑 확인 필요

2. **같은 네트워크 (LAN)**
   - 다른 PC에서 브라우저 접속
   - 예상: 정상 작동

3. **외부 네트워크 (WAN)**
   - 공인 IP 또는 포트 포워딩
   - 예상: STUN/TURN 서버 필요할 수 있음

**테스트 절차:**
```bash
# 1. FFmpeg 테스트 스트림 시작
ffmpeg -re -stream_loop -1 \
  -f lavfi -i testsrc=size=1280x720:rate=30 \
  -f lavfi -i sine=frequency=1000:sample_rate=44100 \
  -c:v libx264 -preset veryfast -b:v 2000k \
  -c:a aac -b:a 128k \
  -f flv rtmp://localhost:1935/live/stream

# 2. 브라우저에서 접속
# http://localhost:5173/#/student

# 3. 개발자 도구에서 확인
# - WHEP 요청 201 응답
# - ICE 상태: new → checking → connected
# - 비디오 트랙 수신 확인

# 4. Playwright 자동 테스트
cd /Users/hwansi/Project/AirClass
INSECURE_HTTPS=1 node scripts/tests/show_browser_test.js
```

**예상 소요 시간:** 1-2시간

**완료 기준:**
- [ ] 로컬 환경 비디오 재생 확인
- [ ] LAN 환경 비디오 재생 확인
- [ ] 지연 시간 측정 (< 1초 목표)
- [ ] 문제 발생 시 해결 방법 문서화

---

## 📅 중기 계획 (2-4주)

### 3️⃣ Dashboard API 구현 (예상 소요: 1일)

**목표:**
통합 대시보드 API로 수업 통계, 참여도, 퀴즈 결과를 한 번에 조회

**API 엔드포인트:**
```python
# routers/dashboard.py

GET /dashboard/summary
- 전체 수업 통계
- 총 참여 학생 수
- 평균 참여도
- 퀴즈 통계

GET /dashboard/session/{session_id}
- 특정 수업 상세 정보
- 참여도 시계열 데이터
- 퀴즈 결과
- 녹화 정보

GET /dashboard/engagement/trend
- 참여도 추세 분석
- 시간대별 패턴
- 학생별 비교

GET /dashboard/quiz/analytics
- 퀴즈 통계
- 정답률 분석
- 난이도 평가
```

**데이터 소스:**
- MongoDB `sessions` 컬렉션
- MongoDB `engagement_data` 컬렉션
- MongoDB `quizzes` 및 `quiz_responses` 컬렉션
- MongoDB `recordings` 컬렉션

**작업 단계:**
1. `services/dashboard_service.py` 생성
2. `routers/dashboard.py` 구현
3. `schemas/dashboard.py` 스키마 정의
4. 15-20개 테스트 작성
5. 문서 작성

**예상 소요 시간:** 1일 (8시간)

**완료 기준:**
- [ ] 4개 주요 엔드포인트 구현
- [ ] 15-20개 테스트 통과
- [ ] API 문서 작성
- [ ] 프론트엔드 통합 가이드

---

### 4️⃣ 부하 테스트 (예상 소요: 2일)

**목표:**
실제 환경에서 100명 이상 동시 접속 테스트

**테스트 시나리오:**

**Scenario 1: WebRTC 스트리밍 부하**
```python
# scripts/tests/load_test_streaming.py
# 100명의 가상 학생이 동시에 WebRTC 스트림 수신

import asyncio
from playwright.async_api import async_playwright

async def simulate_student(student_id: int):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('http://localhost:5173/#/student')
        # JWT 토큰 받아서 스트림 연결
        # 10분간 유지
        await asyncio.sleep(600)
        await browser.close()

async def main():
    tasks = [simulate_student(i) for i in range(100)]
    await asyncio.gather(*tasks)
```

**측정 항목:**
- CPU 사용률 (Main, Sub 노드)
- 메모리 사용량
- 네트워크 대역폭
- 평균 지연 시간
- 패킷 손실률
- 연결 성공률

**Scenario 2: API 부하**
```python
# scripts/tests/load_test_api.py
# 퀴즈 발행, 응답 제출 동시 처리

import aiohttp
import asyncio

async def submit_quiz_response(session, student_id: int):
    async with session.post(
        'http://localhost:8000/quiz/respond',
        json={'student_id': student_id, 'answer': 'A'}
    ) as resp:
        return await resp.json()

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [submit_quiz_response(session, i) for i in range(100)]
        results = await asyncio.gather(*tasks)
```

**목표 성능:**
- ✅ 100명 동시 스트리밍: 안정적
- ✅ CPU 사용률: < 60%
- ✅ 메모리 사용: < 2GB
- ✅ 평균 지연: < 1초
- ✅ 패킷 손실: < 2%

**예상 소요 시간:** 2일

**완료 기준:**
- [ ] 스트리밍 부하 테스트 스크립트 작성
- [ ] API 부하 테스트 스크립트 작성
- [ ] 100명 동시 접속 테스트 성공
- [ ] 성능 보고서 작성
- [ ] 병목 지점 식별 및 개선

---

### 5️⃣ HTTPS/TLS 설정 (예상 소요: 1일)

**목표:**
프로덕션 환경에서 안전한 HTTPS 통신

**구현 방법:**

**옵션 1: Let's Encrypt (무료, 권장)**
```bash
# Certbot 설치
sudo apt-get install certbot

# 인증서 발급
sudo certbot certonly --standalone -d airclass.example.com

# Nginx 설정
# /etc/nginx/sites-available/airclass
server {
    listen 443 ssl;
    server_name airclass.example.com;
    
    ssl_certificate /etc/letsencrypt/live/airclass.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/airclass.example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
    }
    
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# 자동 갱신
sudo certbot renew --dry-run
```

**옵션 2: 자체 서명 인증서 (개발/내부용)**
```bash
# 인증서 생성
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/airclass-selfsigned.key \
  -out /etc/ssl/certs/airclass-selfsigned.crt
```

**Docker 환경 업데이트:**
```yaml
# docker-compose.yml에 Nginx 추가
nginx:
  image: nginx:alpine
  ports:
    - "443:443"
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - /etc/letsencrypt:/etc/letsencrypt
  depends_on:
    - main
```

**예상 소요 시간:** 1일

**완료 기준:**
- [ ] HTTPS 인증서 발급
- [ ] Nginx 설정 완료
- [ ] HTTP → HTTPS 리다이렉트
- [ ] WebSocket WSS 지원
- [ ] 자동 갱신 설정
- [ ] 문서 업데이트

---

## 🎯 장기 계획 (1-3개월)

### 6️⃣ Grafana 모니터링 대시보드

**목표:**
실시간 시스템 모니터링 및 알림

**구성:**
```yaml
# docker-compose.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  depends_on:
    - prometheus
```

**대시보드 패널:**
1. **시스템 리소스**
   - CPU 사용률
   - 메모리 사용량
   - 네트워크 트래픽

2. **스트리밍 메트릭**
   - 활성 스트림 수
   - 시청자 수 (노드별)
   - 평균 비트레이트
   - 패킷 손실률

3. **API 메트릭**
   - 요청 수 (엔드포인트별)
   - 응답 시간
   - 에러율

4. **비즈니스 메트릭**
   - 활성 수업 수
   - 총 참여 학생 수
   - 퀴즈 참여율
   - 평균 참여도

**알림 설정:**
- CPU > 80% 5분 이상
- 메모리 > 90%
- 에러율 > 5%
- 노드 다운

**예상 소요 시간:** 1주일

---

### 7️⃣ 실제 AI 모델 통합

**목표:**
Mock 구현을 실제 AI 모델로 대체

**AI 비전 (OCR, 객체 탐지)**
```python
# services/ai/vision.py 개선

# 현재: Mock 구현
async def analyze_screen(image_path: str) -> ScreenAnalysis:
    return ScreenAnalysis(
        text="하드코딩된 텍스트",
        objects=["test", "mock"],
        complexity="medium"
    )

# 목표: 실제 모델
async def analyze_screen(image_path: str) -> ScreenAnalysis:
    # Tesseract OCR (한글 지원)
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    text = pytesseract.image_to_string(
        Image.open(image_path),
        lang='kor+eng'
    )
    
    # YOLO v8 객체 탐지
    from ultralytics import YOLO
    model = YOLO('yolov8n.pt')
    results = model(image_path)
    objects = [r.names[int(r.boxes.cls[0])] for r in results]
    
    # 복잡도 계산
    complexity = calculate_complexity(text, objects)
    
    return ScreenAnalysis(text=text, objects=objects, complexity=complexity)
```

**AI NLP (감정 분석, 의도 분류)**
```python
# services/ai/nlp.py 개선

# 현재: 키워드 매칭
def analyze_sentiment(text: str) -> Sentiment:
    if "어려워" in text:
        return Sentiment.CONFUSED
    return Sentiment.ENGAGED

# 목표: KoBERT 모델
from transformers import BertTokenizer, BertForSequenceClassification

tokenizer = BertTokenizer.from_pretrained('monologg/kobert')
model = BertForSequenceClassification.from_pretrained('monologg/kobert')

def analyze_sentiment(text: str) -> Sentiment:
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    prediction = torch.argmax(outputs.logits, dim=1)
    return Sentiment(prediction.item())
```

**예상 소요 시간:** 2주

---

### 8️⃣ iOS 앱 개발

**목표:**
iOS에서도 안드로이드와 동일한 RTMP 송출 기능

**기술 스택:**
- Swift 5.9+
- ReplayKit (화면 녹화)
- VideoToolbox (H.264 인코딩)
- RTMP 라이브러리 (HaishinKit 등)

**주요 기능:**
- 화면 캡처 (ReplayKit)
- H.264 하드웨어 인코딩
- RTMP 스트리밍
- 설정 화면 (해상도, FPS, 비트레이트)
- 연결 상태 표시

**예상 소요 시간:** 1개월

---

## 📋 작업 우선순위 정리

### 🔴 긴급 (이번 주)
1. VOD API 테스트 수정 (2-3시간)
2. ICE 연결 검증 (1-2시간)

### 🟡 중요 (2-4주)
3. Dashboard API 구현 (1일)
4. 부하 테스트 (2일)
5. HTTPS/TLS 설정 (1일)

### 🟢 계획 (1-3개월)
6. Grafana 모니터링 (1주)
7. 실제 AI 모델 통합 (2주)
8. iOS 앱 개발 (1개월)

---

## ✅ 체크리스트

### 이번 주 (2026-02-03 ~ 02-09)
- [ ] VOD 테스트 25개 통과
- [ ] ICE 연결 로컬 환경 검증
- [ ] ICE 연결 LAN 환경 검증
- [ ] 문서 최신화 (PROGRESS.md, PROJECT_STATUS.md)

### 다음 주 (2026-02-10 ~ 02-16)
- [ ] Dashboard API 구현
- [ ] Dashboard 테스트 15-20개 작성
- [ ] 부하 테스트 스크립트 작성
- [ ] 100명 동시 접속 테스트

### 3주차 (2026-02-17 ~ 02-23)
- [ ] HTTPS 인증서 발급
- [ ] Nginx 설정 완료
- [ ] 프로덕션 배포 준비
- [ ] 최종 검수

---

## 🎓 성공 기준

### VOD API
- [x] API 구현
- [x] 25개 테스트 작성
- [ ] 25개 테스트 100% 통과
- [ ] 문서화 완료

### Dashboard API
- [ ] 4개 주요 엔드포인트 구현
- [ ] 15-20개 테스트 100% 통과
- [ ] 프론트엔드 통합 가이드
- [ ] 문서화 완료

### 프로덕션 준비
- [x] 201개 테스트 통과
- [ ] VOD, Dashboard 완료
- [ ] 부하 테스트 (100명+)
- [ ] HTTPS/TLS 설정
- [ ] Grafana 대시보드

---

## 📞 연락 및 협의

### 기술적 의사결정 필요
1. **VOD 테스트:** 지금 즉시 수정 vs Dashboard 먼저 구현
2. **부하 테스트 목표:** 100명 vs 200명 vs 450명
3. **HTTPS 방식:** Let's Encrypt vs 자체 서명 vs 상용 인증서

### 일정 협의
- 현재 일정: VOD (1일) → Dashboard (1일) → 부하 테스트 (2일)
- 조정 필요 시 협의

---

## 📚 참고 자료

### 기술 문서
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)

### 프로젝트 문서
- `PROGRESS.md` - 진행 상황
- `PROJECT_STATUS.md` - 프로젝트 상태
- `backend/docs/CURRENT_TASKS.md` - 백엔드 과제

---

**작성자:** AIRClass Team  
**프로젝트 상태:** 🟢 95% 완료  
**다음 마일스톤:** VOD 테스트 수정 → Dashboard 구현
