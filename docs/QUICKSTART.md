# AIRClass 빠른 시작 ⚡

Docker로 1분 만에 배포하는 가이드

---

## 🚀 1분 배포 (테스트용)

```bash
# 1. 다운로드
git clone https://github.com/your-repo/airclass
cd AirClass

# 2. 실행 (단일 서버)
docker-compose -f docker-compose.simple.yml up -d

# 3. 확인
curl http://localhost:8000/health
```

**접속 URL**:
- API: http://localhost:8000
- RTMP: rtmp://localhost:1935/live/stream
- HLS: http://localhost:8888/live/stream/index.m3u8

---

## 🏢 프로덕션 배포 (자동 확장)

```bash
# 1. 환경변수 설정
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" > .env

# 2. 클러스터 시작 (Master 1 + Slave 3)
docker-compose up -d

# 3. 상태 확인
curl http://localhost:8000/cluster/nodes | jq
```

**수용 인원**: 450명 (Slave 3대 × 150명)

---

## 📈 확장하기

### 500명으로 확장
```bash
docker-compose up -d --scale slave=5
```

### 1000명으로 확장
```bash
docker-compose up -d --scale slave=10
```

**자동으로 트래픽 분산!** 🎯

---

## 🔍 주요 명령어

```bash
# 상태 확인
docker-compose ps

# 로그 보기
docker-compose logs -f

# 재시작
docker-compose restart

# 중지
docker-compose down
```

---

## 📱 Android 앱 설정

```kotlin
// 1. Master에게 최적 서버 요청
val response = httpClient.get("http://192.168.1.100:8000/cluster/best-node")
val node = response.json()

// 2. 스트리밍 시작
startStreaming(node["rtmp_url"])
```

---

## 🌐 학생 접속

```javascript
// 토큰 발급 (자동으로 최적 서버 선택)
const res = await fetch('http://서버IP:8000/api/token?user_type=student&user_id=홍길동', 
  { method: 'POST' });
const data = await res.json();

// HLS 재생
player.src = data.hls_url;
```

---

## 📚 더 알아보기

- [전체 배포 가이드](docs/DOCKER_DEPLOYMENT.md)
- [성능 분석](docs/PERFORMANCE_ANALYSIS.md)
- [테스트 결과](docs/TESTING_RESULTS.md)

---

## 🆘 문제 해결

### "No healthy nodes available"
```bash
docker-compose restart
docker-compose up -d --scale slave=5
```

### 포트 충돌
```bash
sudo lsof -i :8000
sudo lsof -i :1935
# 충돌 프로세스 종료 후 재시작
```

### 로그 확인
```bash
docker-compose logs -f master
docker-compose logs -f slave
```

---

**완성!** 🎉 이제 Android 앱으로 스트리밍 시작하세요!
