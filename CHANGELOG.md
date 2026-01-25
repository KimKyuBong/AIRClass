# Changelog

All notable changes to AIRClass will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.0] - 2026-01-24

### Added
- **PC 브라우저 화면 공유 기능** 🎉
  - 교사가 PC 화면을 브라우저에서 직접 공유 가능 (Android 앱 없이)
  - WebRTC (WHIP) 프로토콜 사용으로 초저지연 (200-300ms)
  - 크롬, 엣지, 파이어폭스, 사파리 지원
  - 전체 화면, 특정 윈도우, 특정 탭 공유 선택 가능

- **자동 IP 감지 기능**
  - `setup.sh` 실행 시 서버의 모든 네트워크 IP를 자동 감지
  - 여러 개의 네트워크 인터페이스가 있을 경우 선택 가능
  - 수동 입력도 여전히 가능

- **동적 WebRTC ICE Candidate 설정**
  - Docker 컨테이너 시작 시 `SERVER_IP` 환경 변수 기반으로 자동 설정
  - 하드코딩된 IP 주소 제거로 배포 환경 변경 시 재설정 불필요

### Changed
- **Vite 프록시 설정 개선**
  - `/live` 경로에 WHIP/WHEP 프록시 추가
  - `changeOrigin: true`로 설정하여 Docker 네트워크 호환성 향상
  - 개발용 상세 로그 제거 (에러 로그만 유지)

- **Teacher 페이지 UI/UX 개선**
  - "화면 공유 시작/중지" 버튼 추가
  - 브로드캐스트 상태 표시
  - 에러 메시지 개선 (더 상세한 디버깅 정보)

### Fixed
- **WebRTC P2P 연결 실패 문제 해결**
  - MediaMTX `webrtcAdditionalHosts`에 서버 IP 동적 추가
  - `localhost` 접속 시 발생하는 ICE candidate 문제 문서화
  - UDP 포트 접근성 문제 해결

- **Vite 프록시 타임아웃 문제 해결**
  - WHIP 요청이 MediaMTX에 제대로 전달되지 않던 문제 수정
  - `changeOrigin` 설정으로 Host 헤더 문제 해결

### Documentation
- **README.md 업데이트**
  - PC 브라우저 화면 공유 방법 추가
  - 시스템 구조 다이어그램 업데이트
  - "왜 서버 IP로 접속해야 하나요?" FAQ 추가

- **setup.sh 주석 개선**
  - 자동 IP 감지 로직 설명 추가
  - 사용자 친화적인 안내 메시지 개선

### Technical Details
- **Backend (`main.py`)**
  - `generate_stream_token()` 함수에 `action` 파라미터 추가 (`"read"` / `"publish"`)
  - `/api/token` 엔드포인트에서 `action=publish` 쿼리 파라미터 지원
  - `mediamtx_auth()` 훅에서 WebRTC publish 요청 인증 처리
  - 교사만 publish 권한 부여 (403 에러로 권한 확인)

- **Frontend (`Teacher.svelte`)**
  - `startBroadcast()` 함수 구현: `getDisplayMedia()` API 사용
  - `stopBroadcast()` 함수 구현: 트랙 정리 및 viewer 모드 복귀
  - WHIP 프로토콜로 SDP offer/answer 교환
  - ICE connection 상태 모니터링 및 에러 처리

- **MediaMTX Configuration**
  - `readBufferCount: 65536` (4096→65536) - 큰 SDP 패킷 처리
  - `webrtcIPsFromInterfaces: yes` - 자동 IP 감지 활성화
  - `webrtcAdditionalHosts` - Docker entrypoint에서 동적 설정

- **Docker (`docker-entrypoint.sh`)**
  - Main/Sub 노드 모두 `SERVER_IP` 기반으로 ICE candidate 설정
  - `sed` 명령으로 MediaMTX YAML 파일 동적 수정

### Known Issues
- 브라우저에서 `localhost`로 접속하면 WebRTC 연결 실패 (서버 IP 사용 필요)
- Safari에서 화면 공유 시 일부 제약사항 존재 (macOS 13+ 권장)

### Breaking Changes
- 없음 (하위 호환성 유지)

---

## [2.4.0] - 이전 버전
- Main-Sub 클러스터 아키텍처
- Rendezvous Hashing 로드밸런싱
- HMAC 클러스터 인증
- 원클릭 설치 스크립트

---

## Links
- [GitHub Repository](https://github.com/your-repo/AirClass)
- [Installation Guide](docs/INSTALL_GUIDE.md)
- [Report Issues](https://github.com/your-repo/AirClass/issues)
