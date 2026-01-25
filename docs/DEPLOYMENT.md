# 🚀 AIRClass 배포 가이드

이 문서는 AIRClass를 새로운 환경에 배포하는 방법을 설명합니다.

## 📋 사전 요구사항

### 하드웨어
- **CPU**: 4코어 이상 (Intel/AMD/Apple Silicon)
- **RAM**: 8GB 이상 (학생 150명당 2GB 권장)
- **네트워크**: 유선 또는 5GHz Wi-Fi (학생당 500kbps 권장)
- **저장공간**: 10GB 이상 여유 공간

### 소프트웨어
- **Docker Desktop** (Windows/macOS) 또는 **Docker + Docker Compose** (Linux)
- **Git** (선택사항, 소스 다운로드용)
- **브라우저**: Chrome, Edge, Firefox, Safari (최신 버전)

### 네트워크
- 학생들과 같은 네트워크에 연결되어 있어야 함
- 방화벽에서 다음 포트 허용:
  - `5173` (웹 인터페이스)
  - `8000` (API)
  - `1935` (RTMP - Android 앱용)
  - `8889-8892` (WebRTC HTTP)
  - `8189-8192/udp` (WebRTC UDP)

---

## 🔧 빠른 배포 (권장)

### 1. 소스 다운로드
```bash
# Git으로 클론
git clone https://github.com/your-repo/AirClass.git
cd AirClass

# 또는 ZIP 다운로드 후 압축 해제
```

### 2. Docker 확인
```bash
# Docker가 실행 중인지 확인
docker --version
docker-compose --version

# Docker Desktop이 실행 중이어야 합니다
```

### 3. 자동 설정 실행
```bash
# macOS/Linux
./setup.sh

# Windows
setup.bat
```

**설정 마법사가 실행됩니다:**
1. 서버 IP 자동 감지 및 선택
2. 클래스 비밀번호 입력
3. JWT 암호화 키 자동 생성
4. `.env` 파일 자동 생성

### 4. 서버 시작
```bash
# macOS/Linux
./start.sh

# Windows
start.bat
```

**서버가 시작됩니다:**
- Frontend: `http://서버IP:5173`
- Backend API: `http://서버IP:8000`
- MediaMTX: `http://서버IP:8889`

### 5. 접속 확인
```bash
# 브라우저에서 접속
http://서버IP:5173/teacher    # 교사용
http://서버IP:5173/student    # 학생용
```

---

## 🎯 수동 배포

자동 스크립트를 사용할 수 없는 경우:

### 1. 환경 설정 파일 생성
```bash
# .env.example을 .env로 복사
cp .env.example .env

# 에디터로 열기
nano .env
```

### 2. 필수 설정 수정
```bash
# 서버 IP (필수!)
SERVER_IP=10.100.0.102  # 실제 IP로 변경

# 프론트엔드 URL (SERVER_IP와 일치)
VITE_BACKEND_URL=http://10.100.0.102:8000

# JWT 보안 키 생성 (필수!)
# macOS/Linux:
openssl rand -hex 32

# Windows PowerShell:
[System.Convert]::ToBase64String((1..32 | ForEach-Object {Get-Random -Max 256}))

# 생성된 키를 .env에 입력
JWT_SECRET_KEY=생성된_랜덤_키

# 클래스 비밀번호 (선택, 기본값 사용 가능)
CLUSTER_SECRET=myclass2025
```

### 3. Docker 컨테이너 시작
```bash
# 모든 서비스 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 상태 확인
docker-compose ps
```

---

## 🔍 배포 후 확인사항

### 헬스 체크
```bash
# API 서버 확인
curl http://localhost:8000/health

# 예상 응답:
{
  "status": "healthy",
  "mode": "main",
  "stream_active": false
}
```

### 컨테이너 상태 확인
```bash
docker-compose ps

# 모든 컨테이너가 "Up" 또는 "Up (healthy)" 상태여야 함
```

### 로그 확인
```bash
# 모든 로그
docker-compose logs

# 특정 서비스만
docker-compose logs main
docker-compose logs frontend

# 실시간 로그
docker-compose logs -f
```

---

## 🛠️ 문제 해결

### 서버가 시작되지 않음
```bash
# Docker 데몬 확인
docker ps

# 포트 충돌 확인
lsof -i :5173
lsof -i :8000
lsof -i :8889

# 기존 컨테이너 정리
docker-compose down
docker system prune -a --volumes  # 주의: 모든 데이터 삭제
```

### 학생들이 접속할 수 없음
1. **서버 IP 확인**
   ```bash
   # macOS
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # Linux
   hostname -I
   
   # Windows
   ipconfig
   ```

2. **방화벽 확인**
   - 포트 5173, 8000, 8889-8892, 8189-8192/udp 허용

3. **같은 네트워크인지 확인**
   - 학생과 서버가 같은 Wi-Fi/LAN에 연결되어 있어야 함

### PC 화면 공유가 작동하지 않음

**문제**: "화면 공유 시작" 버튼을 눌렀지만 스트림이 시작되지 않음

**해결책**:
1. **서버 IP로 접속 확인**
   - ❌ `http://localhost:5173/teacher`
   - ✅ `http://10.100.0.102:5173/teacher` (실제 IP 사용)
   
2. **브라우저 콘솔 확인**
   - F12 → Console 탭
   - ICE connection 에러 확인

3. **UDP 포트 확인**
   ```bash
   # UDP 포트가 열려있는지 확인
   docker-compose logs main | grep "webrtc"
   ```

4. **MediaMTX 설정 확인**
   ```bash
   # ICE candidate에 올바른 IP가 설정되었는지 확인
   docker exec airclass-main-node cat mediamtx-main.yml | grep webrtcAdditionalHosts
   
   # 예상 출력:
   # webrtcAdditionalHosts: ['10.100.0.102']
   ```

---

## 🔄 업데이트

### 최신 버전으로 업데이트
```bash
# Git으로 최신 코드 받기
git pull origin main

# 컨테이너 재빌드 및 재시작
docker-compose down
docker-compose up -d --build
```

### 설정 변경 후 재시작
```bash
# .env 파일 수정 후
docker-compose down
docker-compose up -d
```

---

## 🚨 비상 복구

### 모든 것을 초기화하고 다시 시작
```bash
# 1. 모든 컨테이너 중지 및 삭제
docker-compose down -v

# 2. 설정 파일 백업 (선택)
cp .env .env.backup

# 3. 다시 설정
./setup.sh

# 4. 재시작
./start.sh
```

### 데이터 백업
```bash
# .env 파일 백업 (중요!)
cp .env backup/.env.$(date +%Y%m%d)

# Docker 볼륨 백업 (선택)
docker run --rm -v airclass_data:/data -v $(pwd):/backup alpine tar czf /backup/airclass-data-backup.tar.gz /data
```

---

## 📞 지원

문제가 계속되면:
1. [GitHub Issues](https://github.com/your-repo/AirClass/issues)에 문의
2. [설치 가이드](docs/INSTALL_GUIDE.md) 참고
3. [CHANGELOG.md](CHANGELOG.md)에서 알려진 문제 확인

---

## ✅ 체크리스트

배포 전 확인:
- [ ] Docker Desktop이 실행 중
- [ ] 서버 IP를 올바르게 설정 (`localhost`가 아님!)
- [ ] 방화벽 포트 허용
- [ ] 학생과 같은 네트워크
- [ ] `.env` 파일에 실제 값 입력
- [ ] `JWT_SECRET_KEY` 랜덤 생성

배포 후 확인:
- [ ] `docker-compose ps` 모두 healthy
- [ ] `curl http://localhost:8000/health` 응답 OK
- [ ] 교사 페이지 접속 가능
- [ ] 학생 페이지 접속 가능
- [ ] PC 화면 공유 테스트 성공

---

**Made with ❤️ for Teachers**
