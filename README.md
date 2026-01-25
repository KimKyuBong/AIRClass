# 🎓 AIRClass - 실시간 스트리밍 온라인 교실

> **교사를 위한 쉽고 강력한 온라인 수업 플랫폼**

AIRClass는 교사들이 쉽게 사용할 수 있는 실시간 화면 공유 플랫폼입니다. 여러 컴퓨터를 자동으로 연결하여 수백 명의 학생이 동시에 수업을 들을 수 있습니다.

---

## ✨ 주요 기능

### 🚀 간단한 설치와 실행
- **원클릭 설치** - 클릭 한 번으로 모든 설정 완료
- **자동 설정 마법사** - 복잡한 설정 불필요
- **즉시 사용 가능** - 5분 안에 수업 시작

### 🖥️ 멀티 컴퓨터 지원
- **메인 노드 1대** - 관리 및 부하 분산
- **서브 노드 N대** - 필요한 만큼 컴퓨터 추가 가능
- **각 노드당 150명** - 컴퓨터 1대 추가 = 학생 150명 추가 수용

### 🎯 스마트 로드밸런싱
- **Rendezvous Hashing** - 학생이 항상 같은 서버에 연결
- **자동 장애 복구** - 컴퓨터 하나가 문제가 생겨도 자동 전환
- **실시간 모니터링** - 각 컴퓨터의 상태를 실시간으로 확인

### 🔒 보안 기능
- **클러스터 인증** - 다른 선생님의 서버와 자동 구분
- **비밀번호 보호** - 간단한 비밀번호로 서버 보호
- **암호화 통신** - 모든 데이터 암호화 전송

### 📱 다양한 플랫폼 지원
- **Android 앱** - 선생님이 안드로이드 기기로 화면 송출 (RTMP)
- **PC 브라우저** - 선생님이 PC 화면을 브라우저에서 직접 공유 (WebRTC) 🆕
- **웹 브라우저** - 학생들이 브라우저로 시청 (앱 설치 불필요)
- **초저지연 (300ms 이하)** - 실시간 수업 가능

---

## 🏁 빠른 시작 (5분 완성!)

### Windows 사용자

1. **Docker Desktop 설치**
   - https://www.docker.com/products/docker-desktop 에서 다운로드
   - 설치 후 실행

2. **AIRClass 다운로드**
   - GitHub에서 ZIP 파일 다운로드 및 압축 해제
   - 또는 Git 설치 후: `git clone https://github.com/your-repo/AirClass.git`

3. **초기 설정**
   ```cmd
   setup.bat
   ```
   - 서버 IP 주소 입력 (cmd에서 `ipconfig` 입력하여 확인)
   - 클래스 비밀번호 입력 (예: myclass2025)

4. **서버 시작**
   ```cmd
   start.bat
   ```

5. **브라우저에서 접속**
   - 선생님: `http://서버IP:5173/teacher`
   - 학생: `http://서버IP:5173/student`

### macOS 사용자

1. **Docker Desktop 설치**
   - https://www.docker.com/products/docker-desktop 에서 다운로드
   - Apple Silicon (M1/M2/M3) 또는 Intel 버전 확인 후 설치

2. **AIRClass 다운로드**
   ```bash
   cd ~
   git clone https://github.com/your-repo/AirClass.git
   cd AirClass
   ```

3. **초기 설정**
   ```bash
   ./setup.sh
   ```
   - 서버 IP 주소 입력 (터미널에서 `ifconfig | grep "inet "` 입력하여 확인)
   - 클래스 비밀번호 입력

4. **서버 시작**
   ```bash
   ./start.sh
   ```

5. **브라우저에서 접속**
   - 선생님: `http://서버IP:5173/teacher`
   - 학생: `http://서버IP:5173/student`

### Linux (Ubuntu) 사용자

1. **Docker 설치**
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   sudo systemctl start docker
   sudo usermod -aG docker $USER
   # 로그아웃 후 다시 로그인
   ```

2. **AIRClass 다운로드**
   ```bash
   cd ~
   git clone https://github.com/your-repo/AirClass.git
   cd AirClass
   ```

3. **초기 설정**
   ```bash
   ./setup.sh
   ```

4. **서버 시작**
   ```bash
   ./start.sh
   ```

📖 **자세한 설치 방법**: [설치 가이드](docs/INSTALL_GUIDE.md)

---

## 🎬 수업 시작하기

### 방법 1: Android 앱으로 화면 송출 (기존)
1. Android 기기에 RTMP 스트리밍 앱 설치 (예: Larix Broadcaster)
2. RTMP URL 입력: `rtmp://서버IP:1935/live/stream`
3. 스트리밍 시작
4. 학생들이 `http://서버IP:5173/student` 접속

### 방법 2: PC 브라우저로 화면 공유 🆕
1. 브라우저에서 **서버 IP로 접속**: `http://서버IP:5173/teacher`
   - ⚠️ **주의**: `localhost`가 아닌 **서버 IP**로 접속해야 합니다!
   - 예: `http://10.100.0.102:5173/teacher`
2. **"화면 공유 시작"** 버튼 클릭
3. 공유할 화면/윈도우 선택
4. 학생들이 `http://서버IP:5173/student` 접속

**왜 서버 IP로 접속해야 하나요?**
- WebRTC는 P2P 연결을 위해 네트워크 IP가 필요합니다
- `localhost`로 접속하면 Docker 컨테이너의 UDP 포트에 접근할 수 없습니다
- 같은 네트워크의 학생들과 연결하려면 실제 네트워크 IP가 필요합니다

---

## 📊 사용 예시

### 소규모 수업 (학생 150명)
```
💻 메인 노드 1대 (선생님 PC)
총 용량: 150명
```

### 중규모 수업 (학생 450명)
```
💻 메인 노드 1대 (선생님 PC)
🖥️ 서브 노드 2대 (추가 PC)
총 용량: 450명
```

### 대규모 수업 (학생 1,500명)
```
💻 메인 노드 1대
🖥️ 서브 노드 9대 (학교 내 여러 PC 활용)
총 용량: 1,500명
```

---

## 🎯 시스템 구조

```
┌──────────────────┐  ┌──────────────────────────┐
│ 👩‍🏫 선생님      │  │ 👨‍🏫 선생님 (PC 브라우저)  │
│ (Android 앱)    │  │   화면 공유 (WebRTC) 🆕  │
│ 화면 송출(RTMP) │  └─────────┬────────────────┘
└────────┬─────────┘            │
         │                      │
         └──────────┬───────────┘
                    │
            ┌───────▼────────┐
            │   메인 노드     │ ← 클러스터 비밀번호로 보호
            │  (관리 서버)    │
            │                │
            │  • 부하 분산    │
            │  • 인증 관리    │
            │  • 장애 복구    │
            └───┬──────┬─────┘
                │      │
        ┌───────┴──┐ ┌─┴────────┐
        │ 서브 #1   │ │ 서브 #2   │ ← 같은 비밀번호만 연결
        │ (150명)  │ │ (150명)  │
        └─┬────────┘ └─────┬────┘
          │                │
    ┌─────▼──────┐  ┌──────▼─────┐
    │ 👨‍🎓 학생들  │  │ 👨‍🎓 학생들  │
    │ (웹 브라우저)│  │ (웹 브라우저)│
    └────────────┘  └────────────┘
```

---

## 📚 주요 명령어

### Windows
```cmd
setup.bat      # 초기 설정 (IP 주소, 비밀번호 입력)
start.bat      # 서버 시작
stop.bat       # 서버 중지
logs.bat       # 로그 확인
```

### macOS / Linux
```bash
./setup.sh     # 초기 설정
./start.sh     # 서버 시작
./stop.sh      # 서버 중지
./logs.sh      # 로그 확인
```

---

## 🔧 설정 변경

`.env` 파일을 직접 수정하거나 `setup.bat` (또는 `./setup.sh`)를 다시 실행하세요.

**주요 설정 항목**:
- `SERVER_IP` - 서버 IP 주소 (학생들이 접속할 주소)
- `CLUSTER_SECRET` - 클러스터 비밀번호 (다른 선생님 서버와 구분)
- `JWT_SECRET_KEY` - 보안 암호화 키 (자동 생성)

---

## 🛠️ 고급 기능

### 관리자 대시보드
서버 상태를 실시간으로 확인:
```
http://서버IP:8000/cluster/nodes
```

**확인 가능한 정보**:
- 전체 노드 수 및 상태
- 각 노드별 접속 학생 수
- CPU, 메모리 사용량
- 마지막 통신 시간

### 보안 기능

**클러스터 비밀번호 (CLUSTER_SECRET)**:
- 다른 선생님의 메인 노드에 서브 노드가 실수로 연결되는 것 방지
- 같은 네트워크에 여러 선생님이 있어도 안전하게 구분
- 비밀번호가 다르면 연결 거부 (403 Authentication failed)

**작동 방식**:
```
1. 서브 노드가 메인 노드에 연결 요청
2. HMAC-SHA256으로 암호화된 인증 토큰 전송
3. 메인 노드가 비밀번호 검증
4. 일치하면 연결 허용, 다르면 거부
```

---

## 🔍 문제 해결

### 서버가 시작되지 않아요
1. Docker Desktop이 실행 중인지 확인
2. `docker --version` 명령어로 Docker 설치 확인
3. 포트가 이미 사용 중이면 `stop.bat` (또는 `./stop.sh`) 실행 후 재시도

### 학생들이 접속이 안 돼요
1. 서버 IP 주소가 올바른지 확인 (`ipconfig` 또는 `ifconfig`)
2. 같은 Wi-Fi 네트워크에 연결되어 있는지 확인
3. 방화벽 설정 확인 (포트 5173, 8000, 8889-8892, 8189-8192 허용 필요)

### 서브 노드가 연결되지 않아요
1. 메인 노드가 실행 중인지 확인
2. 클러스터 비밀번호가 메인과 서브가 동일한지 확인
3. 로그 확인: `logs.bat` (또는 `./logs.sh`)
4. 에러 메시지에 "Authentication failed" 있으면 비밀번호 불일치

### 영상이 끊겨요
1. 관리자 대시보드에서 노드 상태 확인
2. 부하가 90% 이상이면 서브 노드 추가
3. 인터넷 연결 상태 확인

📖 **자세한 문제 해결**: [설치 가이드 - 문제 해결](docs/INSTALL_GUIDE.md#문제-해결)

---

## 📁 프로젝트 구조

```
AirClass/
├── start.bat / start.sh        # 서버 시작 스크립트
├── stop.bat / stop.sh          # 서버 중지 스크립트
├── setup.bat / setup.sh        # 초기 설정 마법사
├── logs.bat / logs.sh          # 로그 확인
│
├── .env                        # 설정 파일 (자동 생성)
├── docker-compose.yml          # Docker 구성
│
├── backend/                    # 백엔드 서버
│   ├── main.py                 # FastAPI 서버
│   ├── cluster.py              # 클러스터 관리 및 인증
│   └── mediamtx-main.yml       # 스트리밍 서버 설정
│
├── frontend/                   # 프론트엔드
│   └── src/
│       ├── pages/
│       │   ├── Teacher.svelte  # 선생님 페이지
│       │   └── Student.svelte  # 학생 페이지
│       └── ...
│
└── docs/                       # 문서
    ├── INSTALL_GUIDE.md        # 설치 가이드
    └── ...
```

---

## 🚀 기술 스택

### 백엔드
- **FastAPI** (Python) - REST API 서버
- **MediaMTX** - WebRTC/RTMP 스트리밍 서버
- **Docker** - 컨테이너 기반 배포

### 프론트엔드
- **Svelte** - 경량 UI 프레임워크
- **WebRTC** - 초저지연 스트리밍

### 인프라
- **Rendezvous Hashing** - 스마트 로드 밸런싱
- **HMAC-SHA256** - 클러스터 인증
- **Docker Compose** - 멀티 컨테이너 관리

---

## 📊 성능

### 지연시간
- **WebRTC**: 200-300ms (초저지연)
- **자동 버퍼 관리**: 200ms 이상 지연 시 자동 라이브로 점프

### 확장성
- **노드당 수용 인원**: 150명
- **최대 확장**: 이론상 무제한 (메인 1대당 서브 10대 권장)
- **권장 시스템**:
  - CPU: 4코어 이상
  - RAM: 8GB 이상
  - 네트워크: 유선 연결 또는 5GHz Wi-Fi

---

## 🗺️ 로드맵

- [x] **v1.0** - 기본 스트리밍 기능
- [x] **v2.0** - 멀티 노드 클러스터 (Main-Sub 아키텍처)
- [x] **v2.1** - Rendezvous Hashing 로드밸런싱
- [x] **v2.2** - WebRTC 초저지연 스트리밍
- [x] **v2.3** - HMAC 클러스터 인증
- [x] **v2.4** - 원클릭 설치 스크립트 (Windows/macOS/Linux)
- [ ] **v3.0** - 자동 노드 발견 (mDNS)
- [ ] **v3.1** - Kubernetes 지원
- [ ] **v3.2** - AI 기반 자동 스케일링

---

## 🤝 기여하기

Pull Request는 언제나 환영합니다!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 라이선스

MIT License

---

## 📞 지원

문제가 있거나 도움이 필요하시면:
- 📖 [설치 가이드](docs/INSTALL_GUIDE.md) 확인
- 🐛 [GitHub Issues](https://github.com/your-repo/AirClass/issues)에 문의
- 💬 Discord 커뮤니티 참여

---

**Made with ❤️ for Teachers**

교사들의 온라인 수업을 더욱 쉽고 편리하게!
