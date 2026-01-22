# 설치 및 실행 가이드

## 1. 백엔드 서버 설정 및 실행

### 1.1 Python 가상환경 설정

```bash
cd ScreenCaptureApp/backend

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 1.2 서버 실행

```bash
# 개발 모드 (자동 재시작)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 또는
python main.py
```

서버가 정상적으로 실행되면 `http://0.0.0.0:8000`에서 접근 가능합니다.

### 1.3 서버 IP 주소 확인

안드로이드 앱에서 접속할 서버 IP를 확인합니다:

```bash
# macOS/Linux
ifconfig | grep "inet "

# Windows
ipconfig
```

로컬 네트워크 IP (예: 192.168.1.100)를 메모해둡니다.

## 2. 안드로이드 앱 빌드 및 실행

### 2.1 Android Studio 설치

1. [Android Studio](https://developer.android.com/studio) 다운로드 및 설치
2. Android SDK 설치 (API 26 이상)

### 2.2 프로젝트 열기

1. Android Studio 실행
2. `Open` → `ScreenCaptureApp/android` 디렉토리 선택
3. Gradle 동기화 대기 (첫 실행 시 시간이 걸릴 수 있음)

### 2.3 빌드 및 실행

1. 안드로이드 디바이스를 USB로 연결하거나 에뮬레이터 실행
2. 디바이스에서 USB 디버깅 활성화:
   - 설정 → 개발자 옵션 → USB 디버깅 켜기
   - (개발자 옵션이 없다면: 설정 → 휴대전화 정보 → 빌드번호 7회 탭)
3. Android Studio에서 `Run` 버튼 클릭 (Shift+F10)

## 3. 앱 사용 방법

### 3.1 서버 URL 설정

앱 실행 후:
1. "서버 URL" 입력란에 백엔드 서버 주소 입력
   - 예: `http://192.168.1.100:8000`
   - 같은 WiFi 네트워크에 연결되어 있어야 합니다

### 3.2 캡쳐 간격 설정

1. "캡쳐 간격" 입력란에 밀리초 단위로 입력
   - 1000 = 1초마다 캡쳐
   - 최소값: 100ms
   - 권장값: 1000~3000ms (배터리 절약)

### 3.3 화면 캡쳐 시작

1. "시작" 버튼 클릭
2. Android 13+ : 알림 권한 허용
3. 화면 캡쳐 권한 허용 (매 실행마다 필요)
4. 백그라운드에서 자동으로 화면 캡쳐 및 전송 시작

### 3.4 캡쳐 중지

1. 앱을 다시 열고 "중지" 버튼 클릭
2. 또는 알림창에서 앱 종료

## 4. 웹 뷰어로 실시간 모니터링

### 4.1 웹 브라우저로 접속

서버 실행 후 브라우저에서:
```
http://[서버IP]:8000/viewer
```

예시:
- 같은 컴퓨터: `http://localhost:8000/viewer`
- 다른 디바이스: `http://192.168.1.100:8000/viewer`

### 4.2 웹 뷰어 사용법

**실시간 LIVE 모드**
- 안드로이드 앱이 캡쳐를 시작하면 자동으로 화면에 표시
- 우측 상단 "LIVE" 표시등 확인
- 새 스크린샷이 오면 자동으로 업데이트

**과거 화면 다시보기**
1. 타임라인 슬라이더를 드래그하여 원하는 시점으로 이동
2. "이전" / "다음" 버튼으로 한 장씩 이동
3. "재생" 버튼으로 자동 재생 (1초 간격)
4. "LIVE" 버튼으로 최신 화면으로 복귀

**키보드 단축키**
- `←` (왼쪽 화살표): 이전 이미지
- `→` (오른쪽 화살표): 다음 이미지  
- `Space` (스페이스바): 재생/일시정지
- `L`: LIVE 모드 활성화

**통계 정보**
- 총 스크린샷 개수
- 현재 보고 있는 시간
- 연결 상태

### 4.3 서버 상태 확인

```bash
# 브라우저 또는 curl로 확인
curl http://localhost:8000/

# 업로드된 파일 개수 확인
curl http://localhost:8000/uploads/count

# 이미지 목록 조회
curl http://localhost:8000/uploads/list
```

### 4.4 업로드된 이미지 확인

백엔드 서버의 `uploads/` 디렉토리에서 캡쳐된 이미지 확인:

```bash
cd ScreenCaptureApp/backend/uploads
ls -lh
```

## 5. 문제 해결

### 연결 실패

- 서버가 실행 중인지 확인
- 안드로이드와 서버가 같은 WiFi에 연결되어 있는지 확인
- 방화벽에서 8000 포트가 열려있는지 확인
- 서버 URL이 `http://`로 시작하는지 확인 (HTTPS 아님)

### 권한 오류

- 화면 캡쳐 권한은 매번 허용해야 합니다
- Android 13+에서는 알림 권한도 필요합니다

### 앱이 백그라운드에서 중지됨

- 디바이스의 배터리 최적화 설정에서 앱 제외
- 설정 → 배터리 → 배터리 최적화 → 앱 선택 → 최적화 안 함

## 6. 고급 설정

### 서버 포트 변경

`backend/main.py` 파일의 마지막 부분 수정:

```python
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=9000,  # 원하는 포트로 변경
    reload=True
)
```

### 이미지 품질 조정

`android/app/src/main/java/com/example/screencapture/service/ScreenCaptureService.kt`의 
`uploadImage()` 메서드에서:

```kotlin
bitmap.compress(Bitmap.CompressFormat.JPEG, 80, stream)
// 80을 0-100 사이 값으로 조정 (높을수록 고품질, 파일 크기 증가)
```

### 해상도 조정

화면 해상도가 너무 크면 성능 문제가 발생할 수 있습니다.
`ScreenCaptureService.kt`의 `initScreenMetrics()` 메서드 수정:

```kotlin
screenWidth = metrics.widthPixels / 2  // 해상도 절반으로
screenHeight = metrics.heightPixels / 2
```
