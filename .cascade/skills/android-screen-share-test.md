# Android Screen Share Test Skill

안드로이드 앱에서 화면 공유 스트리밍을 자동으로 테스트하는 스킬입니다.

## 사전 요구사항

1. Android 에뮬레이터 또는 실제 기기가 연결되어 있어야 함
2. ADB가 설치되어 있어야 함 (보통 `~/Library/Android/sdk/platform-tools/adb`)
3. 서버가 실행 중이어야 함 (Docker Compose)

## 실행 단계

### 1. 서버 IP 확인
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}'
```

### 2. APK 빌드
```bash
cd android && ./gradlew assembleDebug
```

### 3. APK 설치
```bash
~/Library/Android/sdk/platform-tools/adb install -r android/app/build/outputs/apk/debug/app-debug.apk
```

### 4. 앱 실행
```bash
~/Library/Android/sdk/platform-tools/adb shell am start -n com.example.screencapture/.WelcomeActivity
```

### 5. 개발자 모드 버튼 클릭 (자동)

먼저 UI 계층 구조를 덤프하여 버튼 좌표 확인:
```bash
~/Library/Android/sdk/platform-tools/adb shell uiautomator dump /sdcard/ui.xml
~/Library/Android/sdk/platform-tools/adb shell cat /sdcard/ui.xml | grep -i "개발자"
```

버튼 중앙 좌표로 클릭:
```bash
# 예: bounds="[64,761][2496,877]" -> 중앙 (1280, 819)
~/Library/Android/sdk/platform-tools/adb shell input tap 1280 819
```

### 6. 권한 승인 (화면 캡처)

2초 대기 후 UI 덤프:
```bash
sleep 2
~/Library/Android/sdk/platform-tools/adb shell uiautomator dump /sdcard/ui2.xml
~/Library/Android/sdk/platform-tools/adb shell cat /sdcard/ui2.xml | grep -iE "(start|allow)"
```

"Start" 버튼 클릭:
```bash
# 예: bounds="[1488,1032][1796,1176]" -> 중앙 (1642, 1104)
~/Library/Android/sdk/platform-tools/adb shell input tap 1642 1104
```

### 7. 앱 선택 (미디어 프로젝션)

스크롤하여 "Screen Capture" 앱 찾기:
```bash
~/Library/Android/sdk/platform-tools/adb shell input swipe 1280 1400 1280 800 300
sleep 1
~/Library/Android/sdk/platform-tools/adb shell uiautomator dump /sdcard/ui3.xml
~/Library/Android/sdk/platform-tools/adb shell cat /sdcard/ui3.xml | grep -i "screen"
```

"Screen Capture" 앱 클릭:
```bash
# 예: bounds="[1280,1259][1592,1523]" -> 중앙 (1436, 1391)
~/Library/Android/sdk/platform-tools/adb shell input tap 1436 1391
```

### 8. 로그 확인

스트리밍 시작 확인:
```bash
~/Library/Android/sdk/platform-tools/adb logcat -d | grep -E "(ScreenCapture|RTMP|Connection|LiveKit)" | tail -50
```

성공 메시지 예시:
- `✅ 토큰 발급 성공!`
- `✅ LiveKit 연결 성공!`
- `Room State: CONNECTED`
- `✅ 화면 공유 활성화 성공!`
- `🎉 스트리밍 시작 완료!`

### 9. 브라우저에서 확인

학생 페이지 열기:
```bash
open "http://<SERVER_IP>:5173/student"
```

## 자동화된 테스트 기능

WelcomeActivity의 "개발자 모드" 버튼은 다음을 자동으로 수행합니다:
1. 서버 IP를 현재 머신 IP로 설정
2. 비밀번호를 "test"로 설정
3. MainActivity로 이동하면서 `auto_start=true` 플래그 전달
4. MainActivity에서 0.5초 후 자동으로 시작 버튼 클릭

## 문제 해결

### 연결 실패
- 서버 IP가 올바른지 확인: `.env` 파일의 `SERVER_IP`
- 방화벽 설정 확인
- Docker 컨테이너 상태 확인: `docker ps`

### 권한 거부
- 앱 설정에서 권한 수동 부여
- 에뮬레이터 재시작

### 화면이 곧 꺼짐
- 로그 확인: `adb logcat -d | grep -E "Disconnected|error"`
- 서버 로그 확인: `docker logs airclass-main-node --tail 50`
- LiveKit 연결 상태 확인

## 참고

- 화면 해상도에 따라 버튼 좌표가 다를 수 있음
- `adb shell wm size`로 화면 크기 확인
- UI 계층 구조는 `uiautomator dump`로 확인
