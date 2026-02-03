# 📚 AIRClass 문서 가이드

**최종 업데이트:** 2025-02-02  
**문서 개수:** 25개 (정리 후)

---

## 📖 문서 맵

### 🚀 시작하기 (필수 읽기)

#### 1. **README.md** (루트)
- 프로젝트 개요
- 주요 기능 소개
- 빠른 링크

#### 2. **docs/QUICKSTART.md** ⭐
- 5분 빠른 시작 가이드
- 최소 설정으로 즉시 실행
- 대상: 처음 사용하는 사용자

#### 3. **docs/INSTALL_GUIDE.md**
- 상세 설치 가이드
- MongoDB, Redis, MediaMTX 설정
- 환경 변수 설정
- 대상: 프로덕션 배포 준비

---

### 🏗️ 아키텍처 & 설계

#### 4. **PROJECT_STRUCTURE.md** (루트) ⭐ **NEW**
- 전체 프로젝트 구조 상세 문서
- 파일별 설명 (19개 백엔드 모듈)
- 워크플로우 다이어그램
- 기술 스택 요약

#### 5. **docs/STREAMING_ARCHITECTURE.md**
- WebRTC/RTMP 스트리밍 구조
- MediaMTX 통합
- 지연 시간 최적화

#### 6. **docs/CLUSTER_ARCHITECTURE.md**
- 멀티 노드 클러스터 구조
- Rendezvous Hashing
- 자동 장애 복구 (Failover)
- 노드 헬스체크

#### 7. **docs/SECURITY_IMPLEMENTATION.md**
- 클러스터 인증 (Shared Secret)
- API 키 암호화 (Fernet)
- 보안 모범 사례

---

### 🧪 테스트 & 품질

#### 8. **TEST_ANALYSIS_REPORT.md** (루트) ⭐
- 전체 테스트 분석 (161개 테스트)
- 모듈별 구현 상태 (Mock vs Real)
- 프로덕션 준비도 평가

#### 9. **BUG_FIX_REPORT.md** (루트) ⭐
- 최근 버그 수정 내역 (2025-02-02)
- 수정 전후 비교
- 테스트 통과율 개선

#### 10. **docs/TESTING_GUIDE.md**
- pytest 테스트 실행 방법
- 테스트 작성 가이드
- CI/CD 통합

#### 11. **docs/PERFORMANCE_TESTING_GUIDE.md**
- 성능 테스트 실행
- 부하 테스트 (locust)
- 병목 지점 분석

---

### 🚢 배포 & 운영

#### 12. **docs/DEPLOYMENT.md**
- 프로덕션 배포 가이드
- 서버 요구사항
- Nginx 설정
- HTTPS 설정

#### 13. **docs/PRODUCTION_DEPLOYMENT.md**
- 상세 프로덕션 체크리스트
- 환경 변수 설정
- 모니터링 설정
- 백업 전략

#### 14. **docs/DOCKER_DEPLOYMENT.md**
- Docker Compose 배포
- 컨테이너 설정
- 볼륨 관리

#### 15. **docs/SETUP_GUIDE.md**
- 개발 환경 설정
- 의존성 설치
- 로컬 테스트 서버 실행

---

### 📱 플랫폼별 가이드

#### 16. **android/README.md**
- Android 앱 빌드 가이드
- RTMP 송출 설정
- QR 코드 스캔 기능

#### 17. **frontend/README.md**
- React 프론트엔드 개발
- Vite 빌드 설정
- WebRTC 클라이언트 구현

#### 18. **gui/README.md**
- Tauri 설치 마법사
- 빌드 방법 (Windows/macOS/Linux)

---

### 📊 프로젝트 관리

#### 19. **docs/PROJECT_STATUS.md**
- 현재 프로젝트 상태
- 완료된 기능 목록
- 진행 중인 작업

#### 20. **docs/NEXT_STEPS.md**
- 향후 계획
- 우선순위 작업
- 로드맵

#### 21. **docs/CHANGELOG.md**
- 버전별 변경 이력
- 주요 업데이트 내역

---

### 🔧 기술 참고

#### 22. **docs/AUTO_DISCOVERY.md**
- Zeroconf 자동 노드 발견
- mDNS/Bonjour 설정

#### 23. **docs/SECURITY_LEVEL.md**
- 보안 수준 설명
- 위협 모델

#### 24. **docs/ANDROID_APP_STATUS.md**
- Android 앱 현황
- 지원 기능
- 알려진 이슈

#### 25. **docs/README.md**
- docs 디렉토리 인덱스
- 문서 간 링크

---

## 🗂️ 문서 카테고리별 분류

### ⭐ 필수 문서 (6개)
1. README.md (루트)
2. PROJECT_STRUCTURE.md (루트) - **NEW**
3. docs/QUICKSTART.md
4. docs/INSTALL_GUIDE.md
5. TEST_ANALYSIS_REPORT.md (루트)
6. BUG_FIX_REPORT.md (루트)

### 📐 아키텍처 (4개)
- docs/STREAMING_ARCHITECTURE.md
- docs/CLUSTER_ARCHITECTURE.md
- docs/SECURITY_IMPLEMENTATION.md
- docs/AUTO_DISCOVERY.md

### 🧪 테스트 (2개)
- docs/TESTING_GUIDE.md
- docs/PERFORMANCE_TESTING_GUIDE.md

### 🚢 배포 (4개)
- docs/DEPLOYMENT.md
- docs/PRODUCTION_DEPLOYMENT.md
- docs/DOCKER_DEPLOYMENT.md
- docs/SETUP_GUIDE.md

### 📱 플랫폼 (3개)
- android/README.md
- frontend/README.md
- gui/README.md

### 📊 관리 (3개)
- docs/PROJECT_STATUS.md
- docs/NEXT_STEPS.md
- docs/CHANGELOG.md

### 🔧 기타 (3개)
- docs/SECURITY_LEVEL.md
- docs/ANDROID_APP_STATUS.md
- docs/README.md

---

## 🗑️ 삭제된 문서 (18개)

### 중복 문서
- `IMPLEMENTATION_FIXES_NEEDED.md` → BUG_FIX_REPORT.md에 통합
- `backend/TEST_SUMMARY.md` → TEST_ANALYSIS_REPORT.md에 통합
- `backend/TESTING_REPORT.md` → TEST_ANALYSIS_REPORT.md에 통합
- `docs/TESTING_RESULTS.md` → TESTING_GUIDE.md에 통합
- `docs/PERFORMANCE_ANALYSIS.md` → PERFORMANCE_TESTING_GUIDE.md에 통합

### 구버전 문서
- `backend/PHASE2_완료.md` - 구버전 계획서
- `backend/PHASE3_계획.md` - 구버전 계획서
- `docs/COMPLETION_REPORT_KR.md` - 구버전 완료 보고서
- `docs/TEST_REPORT_KR.md` - 구버전 테스트 리포트
- `docs/PRODUCTION_IMPLEMENTATION_SUMMARY.md` - 구버전 요약

### 일회성 작업 기록
- `docs/CLEANUP_SUMMARY.md` - 일회성 정리 작업
- `docs/PROGRESS.md` - 진행 상황 (PROJECT_STATUS.md로 대체)
- `docs/HLS_MIGRATION.md` - 특정 이슈 해결 (완료됨)
- `docs/SCREEN_DISPLAY_FIX.md` - 특정 버그 수정 (완료됨)
- `docs/WEBSOCKET_INTEGRATION.md` - 통합 완료
- `docs/DEV_SERVER.md` - SETUP_GUIDE.md에 통합

### 기타 중복
- `docs/PRODUCTION_TOOLS.md` - DEPLOYMENT.md에 통합
- `docs/README_WebRTC.md` - STREAMING_ARCHITECTURE.md에 통합

---

## 📖 문서 읽기 순서 (추천)

### 초보자
1. README.md - 프로젝트 이해
2. QUICKSTART.md - 5분 안에 실행해보기
3. PROJECT_STRUCTURE.md - 구조 파악

### 개발자
1. PROJECT_STRUCTURE.md - 전체 구조
2. STREAMING_ARCHITECTURE.md - 스트리밍 이해
3. CLUSTER_ARCHITECTURE.md - 클러스터 이해
4. TESTING_GUIDE.md - 테스트 실행
5. backend/README.md - 백엔드 개발

### 운영자
1. INSTALL_GUIDE.md - 설치
2. DEPLOYMENT.md - 배포
3. PRODUCTION_DEPLOYMENT.md - 프로덕션 체크리스트
4. SECURITY_IMPLEMENTATION.md - 보안 설정

### 테스터
1. TESTING_GUIDE.md - 테스트 실행
2. TEST_ANALYSIS_REPORT.md - 테스트 현황
3. PERFORMANCE_TESTING_GUIDE.md - 성능 테스트

---

## 🔍 빠른 검색

### 특정 주제를 찾을 때

**스트리밍 관련**
- `STREAMING_ARCHITECTURE.md` - WebRTC/RTMP 구조
- `android/README.md` - RTMP 송출

**클러스터 관련**
- `CLUSTER_ARCHITECTURE.md` - 멀티 노드
- `AUTO_DISCOVERY.md` - 자동 발견

**보안 관련**
- `SECURITY_IMPLEMENTATION.md` - 보안 구현
- `SECURITY_LEVEL.md` - 보안 수준

**AI 관련**
- `PROJECT_STRUCTURE.md` - AI 모듈 설명
- `TEST_ANALYSIS_REPORT.md` - Mock 구현 현황

**테스트 관련**
- `TEST_ANALYSIS_REPORT.md` - 전체 분석
- `BUG_FIX_REPORT.md` - 최근 수정
- `TESTING_GUIDE.md` - 실행 방법

**배포 관련**
- `DEPLOYMENT.md` - 일반 배포
- `PRODUCTION_DEPLOYMENT.md` - 프로덕션
- `DOCKER_DEPLOYMENT.md` - Docker

---

## 📝 문서 작성 규칙

### 파일 위치
- **루트:** 프로젝트 전체 개요 (README, PROJECT_STRUCTURE, 테스트 리포트)
- **docs/:** 상세 가이드, 아키텍처, 배포
- **backend/:** 백엔드 개발 가이드
- **frontend/:** 프론트엔드 개발 가이드
- **android/:** 안드로이드 개발 가이드
- **gui/:** GUI 개발 가이드

### 명명 규칙
- 대문자 사용 (예: `README.md`, `DEPLOYMENT.md`)
- 단어 구분: 언더스코어 (예: `PROJECT_STATUS.md`)
- 짧고 명확한 이름

### 업데이트 규칙
- 상단에 "최종 업데이트" 날짜 명시
- 버전 정보 포함 (해당되는 경우)
- 중요 변경사항은 CHANGELOG.md에도 기록

---

## 🎯 다음 작업

### 문서 개선
1. ✅ 중복 문서 삭제 완료 (18개)
2. ✅ PROJECT_STRUCTURE.md 생성 완료
3. ⏳ QUICKSTART.md 업데이트 (최신 상태 반영)
4. ⏳ DEPLOYMENT.md 완성 (Docker 통합)

### 새로 작성할 문서
1. API_REFERENCE.md - REST API 전체 목록
2. TROUBLESHOOTING.md - 일반적인 문제 해결
3. CONTRIBUTING.md - 기여 가이드

---

**정리 전:** 43개 문서  
**정리 후:** 25개 문서 (-18개, -42%)  
**상태:** ✅ 문서 정리 완료
