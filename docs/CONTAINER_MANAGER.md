# 크로스 플랫폼 컨테이너 관리 도구

AIRClass의 Docker 컨테이너(main, sub, frontend, mongodb, redis)를 Windows / macOS / Linux에서 동일하게 관리하기 위한 설계와 구현 요약입니다.

## 1. 요구사항 정리

- **백엔드**: 인터페이스 IP는 **한 개 환경변수**로만 주입해 사용.
  - `SERVER_IP`: 서버(인터페이스) IP 하나로 접속 URL·CORS·LiveKit 브라우저 URL 등 모두 사용.
  - `LIVEKIT_PUBLIC_URL`은 docker-compose에서 `ws://${SERVER_IP}:7880` 형태로 자동 설정되므로, `.env`에는 `SERVER_IP`만 두면 됨.

- **매니저 역할**
  - 인터페이스 IP 선택 (또는 입력) → `.env`에 `SERVER_IP` 등 기록
  - `docker compose up -d` / `docker compose down` 실행 (v1: `docker-compose` 호환)
  - 컨테이너 상태 확인, 로그 확인, 빠른 접속 URL 제공

## 2. 현재 구현: GUI (Python + CustomTkinter)

**위치**: `gui/airclass_gui.py`

- **크로스 플랫폼**: Python 3.8+ 이면 Windows/macOS/Linux 동일 실행.
- **주요 기능**
  - 초기 설정 마법사: 서버 IP 자동 감지, 인터페이스 목록에서 선택, `.env` 생성 시 `SERVER_IP`, `VITE_BACKEND_URL`, `CLUSTER_SECRET` 등 설정 (LiveKit URL은 SERVER_IP 기준으로 compose에서 자동)
  - 설정 창: 동일 항목 수정, 인터페이스(IP) 콤보로 선택
  - 서버 시작/중지: `docker compose`(v2) 우선 사용, 없으면 `docker-compose`(v1) 사용
  - Docker/서버 상태 주기적 확인, 클러스터 정보 표시, 로그 영역
  - 빠른 접속: 선생님/학생/관리자 페이지 URL 열기
- **실행 파일 빌드**: `gui/build-windows.bat`, `gui/build-macos.sh` (PyInstaller)로 단일 실행 파일 생성 가능.

이 GUI가 **현재 권장하는 크로스 플랫폼 컨테이너 매니저**입니다.  
백엔드는 이미 환경변수로 인터페이스 IP를 받으므로, 매니저는 `.env`만 올바르게 쓰면 됩니다.

## 3. 대안 구현 방향 (참고)

필요 시 아래와 같이 확장할 수 있습니다.

| 방식 | 장점 | 단점 |
|------|------|------|
| **현재 GUI (Python + CustomTkinter)** | 이미 구현됨, 의존성 적음, Win/Mac/Linux 동일 | 네이티브 look & feel은 제한적 |
| **Electron + Node.js** | 웹 기술로 풍부한 UI, `dockerode`로 Docker API 직접 제어 | 번들 크기·메모리 사용 큼 |
| **Tauri + Rust** | 경량, Docker CLI 또는 Rust Docker 라이브러리 호출 | Rust/프론트 개발 비용 |
| **웹 대시보드** | 브라우저만 있으면 크로스 플랫폼, 원격 관리 용이 | 호스트에서 .env 쓰기·docker 실행 권한 이슈 (에이전트 필요) |

- **로컬 전용**이면: 현재 Python GUI 확장이 가장 단순합니다.
- **원격 서버 여러 대**를 한 화면에서 관리하려면: 호스트마다 에이전트(작은 HTTP 서버 + docker CLI 래퍼)를 두고, 중앙 웹 대시보드에서 API로 제어하는 구성을 검토할 수 있습니다.

## 4. 환경변수 일치 (매니저 ↔ 백엔드)

**같은 IP 하나만 쓰면 됨.** `.env`에는 `SERVER_IP`만 두고, 나머지는 이걸 기준으로 자동 처리합니다.

| 변수 | 설명 | 설정 |
|------|------|------|
| `SERVER_IP` | 서버(인터페이스) IP. 접속 URL·CORS·LiveKit URL 모두 이 주소 기준 | 매니저/설정에서 선택·입력 |
| `LIVEKIT_PUBLIC_URL` | LiveKit WebSocket 외부 URL | docker-compose에서 `ws://${SERVER_IP}:7880` 자동 생성 (별도 설정 불필요) |
| `VITE_BACKEND_URL` | 프론트엔드가 쓰는 백엔드 URL | 매니저에서 `http://{SERVER_IP}:8000` 로 설정 |
| `CLUSTER_SECRET` | 클러스터 인증용 비밀번호 | 사용자 입력 |

설정 변경 후에는 **서버 재시작**(중지 후 시작)이 필요합니다.

## 5. 요약

- **백엔드**: 인터페이스 IP를 `SERVER_IP` 하나로 사용 (LIVEKIT_PUBLIC_URL은 compose에서 자동).
- **크로스 플랫폼 컨테이너 관리**: `gui/airclass_gui.py`가 그 역할을 하며, 인터페이스 선택·`.env` 반영·docker compose up/down·상태 확인을 담당합니다.
- 추가로 원격 다중 호스트 관리가 필요해지면, 에이전트 + 웹 대시보드 구성을 검토하면 됩니다.
