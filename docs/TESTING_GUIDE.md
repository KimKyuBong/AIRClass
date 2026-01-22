# 테스트 가이드

## 백엔드 서버 테스트

### 1. 서버 실행

```bash
cd ScreenCaptureApp/backend

# 방법 1: 자동 스크립트 (권장)
./start.sh              # macOS/Linux
start.bat               # Windows

# 방법 2: 직접 실행
source venv/bin/activate
python main.py
```

서버가 실행되면 다음 주소에서 접근 가능:
- **웹 뷰어**: http://localhost:8000/viewer
- **API 문서**: http://localhost:8000/docs

### 2. 샘플 이미지 테스트

안드로이드 앱 없이도 테스트 가능합니다!

```bash
cd ScreenCaptureApp/backend
source venv/bin/activate
python test_sample_images.py
```

**실행 결과**:
- 20개의 컬러풀한 샘플 이미지 자동 생성
- 1초 간격으로 서버에 업로드
- 실시간으로 WebSocket을 통해 웹 뷰어에 표시

**설정 변경**:
`test_sample_images.py` 파일에서:
- `num_images`: 생성할 이미지 개수 (기본: 20)
- `interval`: 전송 간격 초 단위 (기본: 1.0)

### 3. 웹 뷰어 사용

브라우저에서 `http://localhost:8000/viewer` 접속

#### 주요 기능

**실시간 LIVE 모드**
- 새 이미지가 업로드되면 자동으로 화면에 표시
- 우측 상단 "LIVE" 표시등이 녹색으로 깜박임

**히스토리 재생**
- 타임라인 슬라이더를 드래그하여 과거 이미지 탐색
- "재생" 버튼: 1초 간격 자동 재생
- "이전/다음" 버튼: 한 장씩 이동
- "LIVE" 버튼: 최신 이미지로 즉시 이동

**키보드 단축키**
- `←` (왼쪽 화살표): 이전 이미지
- `→` (오른쪽 화살표): 다음 이미지
- `Space` (스페이스바): 재생/일시정지
- `L`: LIVE 모드 활성화

**통계 정보**
- 총 스크린샷 개수
- 현재 보고 있는 시간
- 서버 연결 상태

## API 테스트

### REST API 엔드포인트

```bash
# 헬스체크
curl http://localhost:8000/

# 업로드된 이미지 개수 조회
curl http://localhost:8000/uploads/count

# 업로드된 이미지 목록 조회
curl http://localhost:8000/uploads/list

# 이미지 업로드
curl -X POST -F "file=@test.jpg" http://localhost:8000/upload

# 모든 이미지 삭제
curl -X DELETE http://localhost:8000/uploads/clear
```

### WebSocket 테스트

WebSocket 연결: `ws://localhost:8000/ws`

JavaScript 예제:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('Connected');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('New screenshot:', data);
};
```

## 안드로이드 앱 테스트

### 준비사항

1. Android Studio 설치
2. 안드로이드 디바이스 또는 에뮬레이터 준비
3. 같은 WiFi 네트워크에 연결

### 실행 방법

1. **백엔드 서버 IP 확인**
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "
   
   # Windows
   ipconfig
   ```
   예: `192.168.1.100`

2. **Android Studio에서 앱 실행**
   - `android/` 프로젝트 열기
   - Gradle 동기화 완료
   - 디바이스 연결 확인
   - Run 버튼 클릭

3. **앱 설정**
   - 서버 URL: `http://192.168.1.100:8000` (서버 IP로 변경)
   - 캡쳐 간격: `1000` (1초, 밀리초 단위)
   - "시작" 버튼 클릭

4. **권한 허용**
   - 알림 권한 허용 (Android 13+)
   - 화면 캡쳐 권한 허용

5. **실행 확인**
   - 웹 브라우저에서 `http://localhost:8000/viewer` 접속
   - 안드로이드 화면이 실시간으로 표시되는지 확인

## 테스트 시나리오

### 시나리오 1: 실시간 모니터링
1. 백엔드 서버 실행
2. 웹 뷰어 접속 (LIVE 모드 확인)
3. 샘플 이미지 스크립트 실행
4. 웹 뷰어에서 이미지가 실시간으로 추가되는지 확인

### 시나리오 2: 히스토리 재생
1. 샘플 이미지 20개 업로드
2. 웹 뷰어에서 타임라인 슬라이더 조작
3. 재생 버튼으로 자동 재생
4. 키보드 화살표로 이동

### 시나리오 3: 안드로이드 연동
1. 안드로이드 앱에서 캡쳐 시작
2. 웹 뷰어에서 실시간 확인
3. 앱 종료 후 웹에서 히스토리 확인

## 문제 해결

### 서버가 시작되지 않음
```bash
# 포트 충돌 확인
lsof -i:8000

# 기존 프로세스 종료
lsof -ti:8000 | xargs kill -9

# 의존성 재설치
pip install -r requirements.txt
```

### 웹 뷰어가 연결되지 않음
- 서버가 실행 중인지 확인: `curl http://localhost:8000/`
- 브라우저 콘솔에서 에러 확인
- 방화벽 설정 확인

### 안드로이드 앱 연결 실패
- 서버 IP 주소 확인
- 같은 WiFi 네트워크에 연결되어 있는지 확인
- URL에 `http://` 포함 여부 확인
- 방화벽에서 8000 포트 허용

### WebSocket 연결 끊김
- 네트워크 상태 확인
- 브라우저 콘솔에서 에러 로그 확인
- 서버 로그 확인: `tail -f server.log`

## 성능 테스트

### 부하 테스트
```bash
# 100개 이미지 빠르게 업로드
python test_sample_images.py  # num_images=100, interval=0.1
```

### 메모리 사용량 확인
```bash
# 서버 프로세스 모니터링
ps aux | grep python

# 업로드 디렉토리 용량 확인
du -sh uploads/
```

## 로그 확인

```bash
# 서버 로그
tail -f server.log

# 실시간 로그
python main.py  # Ctrl+C로 종료
```
