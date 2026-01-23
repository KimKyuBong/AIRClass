# AIRClass 설치 가이드

## 📋 목차
- [🚀 빠른 설치 (자동)](#-빠른-설치-자동)
- [Windows 설치 가이드](#windows-설치-가이드)
- [macOS 설치 가이드](#macos-설치-가이드)
- [Linux (Ubuntu) 설치 가이드](#linux-ubuntu-설치-가이드)
- [문제 해결](#문제-해결)

---

## 🚀 빠른 설치 (자동)

**Docker 자동 설치 포함! 아무것도 설치할 필요 없습니다.**

### Windows
1. **install.bat 더블클릭** (또는 마우스 우클릭 > "관리자 권한으로 실행")
2. 안내에 따라 진행
3. 완료!

**모든 것이 자동으로 설치됩니다:**
- ✅ Docker Desktop 다운로드 및 설치
- ✅ Docker 자동 실행
- ✅ AIRClass 설정 (IP 주소, 비밀번호 입력만 하면 됨)
- ✅ 서버 준비 완료

### macOS / Linux
```bash
./install.sh
# 또는 macOS 전용
./install-macos.sh
# 또는 Linux 전용
sudo ./install-linux.sh
```

**자동으로 처리:**
- ✅ Docker 자동 설치 (macOS는 Apple Silicon/Intel 자동 감지)
- ✅ 시스템 설정 자동 구성
- ✅ AIRClass 초기 설정
- ✅ 모든 준비 완료

---

## 수동 설치 (고급 사용자용)

자동 설치에 문제가 있거나 직접 설치하고 싶은 경우 아래 가이드를 따라주세요.

## Windows 설치 가이드

### 1단계: Docker Desktop 설치 (선택사항 - install.bat가 자동으로 설치)

1. **Docker Desktop 다운로드**
   - https://www.docker.com/products/docker-desktop 접속
   - "Download for Windows" 클릭
   - 다운로드한 파일(`Docker Desktop Installer.exe`) 실행

2. **설치 진행**
   - "Use WSL 2 instead of Hyper-V" 옵션 **체크** (권장)
   - "Add shortcut to desktop" 옵션 선택 (선택사항)
   - Install 클릭
   - 설치 완료 후 컴퓨터 재시작

3. **Docker Desktop 실행**
   - 바탕화면 또는 시작 메뉴에서 "Docker Desktop" 실행
   - 최초 실행 시 약관 동의 필요
   - Docker Engine이 시작될 때까지 대기 (하단 아이콘이 초록색으로 변경)

### 2단계: AIRClass 다운로드

1. **프로젝트 다운로드**
   ```
   방법 1: Git 사용 (Git 설치되어 있는 경우)
   - 명령 프롬프트(cmd) 실행
   - cd C:\Users\사용자명\Documents
   - git clone https://github.com/your-repo/AirClass.git
   - cd AirClass

   방법 2: ZIP 다운로드 (Git 없는 경우)
   - GitHub에서 "Code" > "Download ZIP" 클릭
   - 다운로드한 ZIP 파일 압축 풀기
   - 명령 프롬프트에서 압축 푼 폴더로 이동
   ```

### 3단계: 서버 설정

1. **명령 프롬프트(cmd)에서 AIRClass 폴더로 이동**
   ```cmd
   cd C:\Users\사용자명\Documents\AirClass
   ```

2. **setup.bat 실행**
   ```cmd
   setup.bat
   ```

3. **설정 입력**
   - **서버 IP 주소**: 
     - 새 명령 프롬프트 열기
     - `ipconfig` 입력
     - "IPv4 주소" 확인 (예: 192.168.0.100)
     - 해당 IP를 setup.bat에 입력
   
   - **클래스 비밀번호**: 
     - 원하는 비밀번호 입력 (예: math2025, room303)
     - 다른 선생님 서버와 구분하기 위한 용도

### 4단계: 서버 시작

1. **start.bat 실행**
   ```cmd
   start.bat
   ```

2. **브라우저에서 접속**
   - 선생님 페이지: `http://서버IP:5173/teacher`
   - 학생 페이지: `http://서버IP:5173/student`

### 일상적인 사용

**서버 시작**: `start.bat` 더블클릭  
**서버 중지**: `stop.bat` 더블클릭  
**로그 확인**: `logs.bat` 더블클릭  
**설정 변경**: `setup.bat` 더블클릭

---

## macOS 설치 가이드

### 1단계: Docker Desktop 설치

1. **Docker Desktop 다운로드**
   - https://www.docker.com/products/docker-desktop 접속
   - "Download for Mac" 클릭
   - **중요**: 본인의 Mac 칩 확인
     - Apple 메뉴 () > "이 Mac에 관하여" 클릭
     - "칩" 항목 확인
     - **Apple Silicon (M1/M2/M3)**: "Mac with Apple chip" 다운로드
     - **Intel**: "Mac with Intel chip" 다운로드

2. **설치 진행**
   - 다운로드한 `.dmg` 파일 열기
   - Docker 아이콘을 Applications 폴더로 드래그
   - Applications에서 Docker 실행
   - 시스템 권한 요청 시 "확인" 클릭
   - Docker Engine이 시작될 때까지 대기

### 2단계: AIRClass 다운로드

1. **터미널 실행** (Finder > 응용 프로그램 > 유틸리티 > 터미널)

2. **프로젝트 다운로드**
   ```bash
   # 홈 디렉토리로 이동
   cd ~
   
   # Git으로 다운로드 (Git 설치되어 있는 경우)
   git clone https://github.com/your-repo/AirClass.git
   cd AirClass
   
   # 또는 ZIP 다운로드 후
   # Downloads 폴더에서 압축 풀기
   cd ~/Downloads/AirClass
   ```

### 3단계: 서버 설정

1. **setup.sh 실행**
   ```bash
   ./setup.sh
   ```

2. **설정 입력**
   - **서버 IP 주소**: 
     - 새 터미널 창 열기
     - `ifconfig | grep "inet "` 입력
     - 192.168 또는 10.으로 시작하는 IP 확인
     - 해당 IP를 setup.sh에 입력
   
   - **클래스 비밀번호**: 
     - 원하는 비밀번호 입력 (예: math2025, room303)

### 4단계: 서버 시작

1. **start.sh 실행**
   ```bash
   ./start.sh
   ```

2. **브라우저에서 접속**
   - 선생님 페이지: `http://서버IP:5173/teacher`
   - 학생 페이지: `http://서버IP:5173/student`

### 일상적인 사용

**서버 시작**: `./start.sh`  
**서버 중지**: `./stop.sh`  
**로그 확인**: `./logs.sh`  
**설정 변경**: `./setup.sh`

---

## Linux (Ubuntu) 설치 가이드

### 1단계: Docker 설치

1. **시스템 업데이트**
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

2. **Docker 설치**
   ```bash
   # Docker 설치
   sudo apt install -y docker.io docker-compose
   
   # Docker 서비스 시작
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # 현재 사용자를 docker 그룹에 추가 (sudo 없이 사용하기 위함)
   sudo usermod -aG docker $USER
   
   # 로그아웃 후 다시 로그인 (그룹 변경 적용)
   ```

3. **설치 확인**
   ```bash
   docker --version
   docker-compose --version
   ```

### 2단계: AIRClass 다운로드

```bash
# 홈 디렉토리로 이동
cd ~

# Git으로 다운로드
git clone https://github.com/your-repo/AirClass.git
cd AirClass
```

### 3단계: 서버 설정

1. **setup.sh 실행**
   ```bash
   ./setup.sh
   ```

2. **설정 입력**
   - **서버 IP 주소**: 
     ```bash
     # 새 터미널에서 IP 확인
     ip addr show | grep "inet "
     # 또는
     hostname -I
     ```
   
   - **클래스 비밀번호**: 원하는 비밀번호 입력

### 4단계: 서버 시작

```bash
./start.sh
```

### 일상적인 사용

**서버 시작**: `./start.sh`  
**서버 중지**: `./stop.sh`  
**로그 확인**: `./logs.sh`  
**설정 변경**: `./setup.sh`

---

## 문제 해결

### Windows

**문제 1: "Docker가 실행되고 있지 않습니다"**
- Docker Desktop을 시작 메뉴에서 실행
- 작업 표시줄에서 Docker 아이콘이 초록색이 될 때까지 대기

**문제 2: "WSL 2 installation is incomplete"**
- https://aka.ms/wsl2kernel 에서 WSL 2 업데이트 다운로드
- 설치 후 컴퓨터 재시작

**문제 3: 포트가 이미 사용 중입니다**
- `stop.bat` 실행 후 다시 시도
- 또는 다른 프로그램이 8000번 포트를 사용 중인지 확인

**문제 4: 학생들이 접속이 안 됩니다**
- 방화벽 설정 확인:
  - Windows 방화벽 > 고급 설정 > 인바운드 규칙
  - 새 규칙: 포트 5173, 8000, 8889-8892, 8189-8192 허용

### macOS

**문제 1: "command not found: ./setup.sh"**
```bash
chmod +x setup.sh start.sh stop.sh logs.sh
```

**문제 2: Docker가 시작되지 않습니다**
- Docker Desktop을 Applications에서 실행
- 메뉴바에서 Docker 아이콘 확인 (고래 모양)

**문제 3: 포트 권한 오류**
```bash
sudo ./start.sh
```

### Linux

**문제 1: "permission denied" 오류**
```bash
# Docker 그룹에 추가되었는지 확인
groups

# docker가 목록에 없으면
sudo usermod -aG docker $USER
# 로그아웃 후 다시 로그인
```

**문제 2: Docker 서비스가 시작되지 않습니다**
```bash
sudo systemctl status docker
sudo systemctl start docker
```

**문제 3: 방화벽 설정 (UFW 사용 시)**
```bash
sudo ufw allow 5173/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8889:8892/tcp
sudo ufw allow 8189:8192/udp
sudo ufw reload
```

---

## 추가 도움말

### 네트워크 설정

**같은 Wi-Fi 네트워크에 있어야 합니다**
- 선생님 컴퓨터와 학생 기기가 같은 Wi-Fi에 연결
- 학교 네트워크의 경우 IT 관리자에게 포트 개방 요청 필요

**IP 주소 고정 (선택사항)**
- 서버 컴퓨터의 IP 주소를 고정하면 매번 설정 변경 불필요
- 공유기 설정에서 DHCP 고정 IP 할당 권장

### 성능 최적화

**권장 시스템 사양**
- CPU: 4코어 이상
- RAM: 8GB 이상
- 네트워크: 유선 연결 권장 (Wi-Fi는 5GHz 대역)

**동시 접속 학생 수**
- 기본 설정: 최대 450명 (Sub 노드 3개 × 150명)
- 더 많은 학생 수용 시 Sub 노드 추가 필요

---

## 문의 및 지원

문제가 해결되지 않으면:
1. `logs.bat` (또는 `./logs.sh`) 실행하여 오류 메시지 확인
2. 관리자 페이지(`http://서버IP:8000/cluster/nodes`)에서 서버 상태 확인
3. GitHub Issues에 로그와 함께 문의
