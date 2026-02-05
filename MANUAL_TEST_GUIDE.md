# AirClass LiveKit 수동 테스트 가이드

## 사전 준비

### 1. 서비스 시작
```bash
cd /Users/hwansi/Project/AirClass
docker-compose up -d
```

### 2. 서비스 상태 확인
```bash
# 모든 컨테이너 실행 확인
docker-compose ps

# 예상 출력:
# - airclass-main-node: Up (port 8000, 7880)
# - airclass-sub-1: Up (port 8001, 7890)
# - airclass-frontend: Up (port 5173)
# - mongodb: Up
# - redis: Up
```

### 3. API 헬스 체크
```bash
curl http://localhost:8000/health
# 출력: {"status":"healthy"}

curl http://localhost:8000/api/livekit/rooms
# 출력: {"rooms":[],"count":0}
```

---

## 테스트 시나리오

### 시나리오 1: Teacher 화면 공유 → Student 수신

#### Step 1: Teacher 페이지 접속
1. 브라우저 열기: http://localhost:5173/#/teacher
2. 방 이름 입력: `test-room-001`
3. "🖥️ PC 화면" 버튼 클릭
4. 화면 선택 팝업에서 공유할 화면 선택
5. **확인 사항:**
   - ✅ 로컬 비디오 프리뷰가 표시됨
   - ✅ "연결됨" 상태 표시
   - ✅ 콘솔에 에러 없음 (F12 개발자 도구)

#### Step 2: Student 페이지 접속 (새 탭)
1. 새 탭 열기: http://localhost:5173/#/student
2. 같은 방 이름 입력: `test-room-001`
3. "수업 참여" 버튼 클릭
4. **확인 사항:**
   - ✅ Teacher 화면이 표시됨
   - ✅ 영상이 부드럽게 재생됨
   - ✅ 지연 시간 < 1초

#### Step 3: 다중 Student 테스트
1. 2~3개의 추가 탭에서 Student 페이지 접속
2. 모두 같은 방 이름 입력
3. **확인 사항:**
   - ✅ 모든 Student가 동일한 영상 수신
   - ✅ 성능 저하 없음

---

### 시나리오 2: 네트워크 안정성 테스트

#### Step 1: 연결 끊김 시뮬레이션
1. Teacher/Student 연결 후
2. 개발자 도구 (F12) → Network 탭
3. "Offline" 체크박스 활성화
4. 5초 대기
5. "Offline" 체크박스 비활성화
6. **확인 사항:**
   - ✅ 자동 재연결됨
   - ✅ 영상 재생 재개됨

#### Step 2: 방 나가기/재입장
1. Student "나가기" 버튼 클릭
2. 다시 "수업 참여" 클릭
3. **확인 사항:**
   - ✅ 즉시 재연결됨
   - ✅ 영상 정상 수신

---

### 시나리오 3: 클러스터 부하 분산 테스트

#### Step 1: 여러 방 동시 생성
1. 5개의 브라우저 탭에서 Teacher 접속
2. 각각 다른 방 이름 사용:
   - `room-1`, `room-2`, `room-3`, `room-4`, `room-5`
3. 모두 화면 공유 시작

#### Step 2: 클러스터 상태 확인
```bash
curl http://localhost:8000/cluster/nodes | jq
```

**예상 출력:**
```json
{
  "total_nodes": 1,
  "healthy_nodes": 1,
  "total_capacity": 150,
  "utilization": 0.033  // 5/150
}
```

#### Step 3: LiveKit 방 목록 확인
```bash
curl http://localhost:8000/api/livekit/rooms | jq
```

**예상 출력:**
```json
{
  "rooms": [
    {"name": "room-1", "num_participants": 1, ...},
    {"name": "room-2", "num_participants": 1, ...},
    ...
  ],
  "count": 5
}
```

---

## 문제 해결

### 문제 1: "연결 실패" 에러

**원인:** LiveKit 서버가 시작되지 않음

**해결:**
```bash
docker logs airclass-main-node | grep -i livekit
# LiveKit 서버 프로세스 확인
docker exec airclass-main-node ps aux | grep livekit
```

### 문제 2: 영상이 표시되지 않음

**원인:** WebRTC 연결 실패 (방화벽/NAT)

**해결:**
1. 브라우저 콘솔 (F12) 확인
2. ICE connection state 확인:
   ```javascript
   // 콘솔에서 실행
   window.room.engine.client.pc.iceConnectionState
   // 출력: "connected" 또는 "failed"
   ```
3. TURN 서버 설정 필요 (다음 섹션 참조)

### 문제 3: 지연 시간이 길다 (> 3초)

**원인:** 네트워크 대역폭 부족 또는 CPU 과부하

**해결:**
1. 비디오 해상도 낮추기 (Frontend 코드 수정)
2. 서버 리소스 확인:
   ```bash
   docker stats airclass-main-node
   ```

---

## 성능 벤치마크

### 목표 지표
- **지연 시간:** < 1초 (LAN 환경)
- **동시 접속:** 150명 (Sub 노드당)
- **CPU 사용률:** < 50% (유휴 시)
- **메모리 사용:** < 2GB (Main 노드)

### 측정 방법
```bash
# 1. 지연 시간 측정 (브라우저 콘솔)
const start = Date.now();
window.room.on('trackSubscribed', () => {
  console.log('Latency:', Date.now() - start, 'ms');
});

# 2. 리소스 사용률
docker stats --no-stream airclass-main-node

# 3. 동시 접속 테스트 (부하 테스트 도구 필요)
# 추후 k6 또는 Artillery 사용
```

---

## 다음 단계

### ✅ 완료 후 체크리스트
- [ ] Teacher → Student 영상 송수신 확인
- [ ] 다중 Student 동시 접속 확인
- [ ] 네트워크 끊김 후 재연결 확인
- [ ] 클러스터 부하 분산 확인
- [ ] 성능 지표 측정

### 🔴 발견된 문제
- 문제 1: [설명]
- 문제 2: [설명]

### 📝 개선 사항
- 개선 1: [설명]
- 개선 2: [설명]

---

## 참고 자료

- LiveKit 문서: https://docs.livekit.io/
- WebRTC 디버깅: chrome://webrtc-internals/
- AirClass 아키텍처: [ARCHITECTURE.md](./ARCHITECTURE.md)
