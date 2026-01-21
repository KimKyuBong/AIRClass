# Android Screen Capture App

Kotlin으로 작성된 안드로이드 화면 캡쳐 애플리케이션

## 기능

- 백그라운드에서 실시간 화면 캡쳐
- MediaProjection API 사용
- Foreground Service로 안정적인 백그라운드 실행
- 설정 가능한 캡쳐 간격
- FastAPI 서버로 자동 업로드

## 요구사항

- Android 8.0 (API 26) 이상
- Android Studio Hedgehog (2023.1.1) 이상
- Kotlin 1.9.20
- Gradle 8.2

## 빌드 방법

1. Android Studio에서 프로젝트 열기
2. Gradle 동기화 대기
3. 디바이스/에뮬레이터 연결
4. Run 버튼 클릭

## 권한

이 앱은 다음 권한을 요청합니다:

- `INTERNET` - 서버로 이미지 전송
- `FOREGROUND_SERVICE` - 백그라운드 서비스 실행
- `FOREGROUND_SERVICE_MEDIA_PROJECTION` - 화면 캡쳐
- `POST_NOTIFICATIONS` - 알림 표시 (Android 13+)
- `WAKE_LOCK` - 백그라운드 실행 유지

## 사용 방법

1. 앱 실행
2. 서버 URL 입력 (예: http://192.168.1.100:8000)
3. 캡쳐 간격 설정 (밀리초, 최소 100ms)
4. "시작" 버튼 클릭
5. 화면 캡쳐 권한 허용
6. 백그라운드에서 자동으로 캡쳐 및 전송

## 주요 컴포넌트

### MainActivity
- 사용자 인터페이스
- 권한 요청 처리
- 서비스 시작/중지

### ScreenCaptureService
- 백그라운드 화면 캡쳐
- 주기적 스크린샷 촬영
- 이미지 압축 및 전송

### ApiClient
- Retrofit 기반 HTTP 클라이언트
- 멀티파트 파일 업로드
- 에러 처리

## 주의사항

- 화면 캡쳐는 민감한 권한이므로 매 실행마다 사용자 동의가 필요합니다
- 배터리 소모가 클 수 있으니 캡쳐 간격을 적절히 조정하세요
- 네트워크 상태가 불안정하면 업로드가 실패할 수 있습니다
- 서버 URL은 반드시 `http://` 또는 `https://`로 시작해야 합니다
