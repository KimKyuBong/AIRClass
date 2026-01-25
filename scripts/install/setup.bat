@echo off
chcp 65001 >nul
echo ========================================
echo   AIRClass 초기 설정 마법사
echo ========================================
echo.

REM 기존 .env 파일이 있으면 백업
if exist ".env" (
    echo 기존 설정 파일을 발견했습니다.
    echo 백업 파일을 생성합니다: .env.backup
    copy /Y .env .env.backup >nul
    echo.
)

echo 1. 서버 IP 주소를 입력하세요
echo    (학생들이 접속할 컴퓨터의 IP 주소)
echo.
echo    확인 방법:
echo    - Windows: 명령 프롬프트에서 'ipconfig' 입력
echo    - 'IPv4 주소' 항목을 확인 (예: 192.168.0.100)
echo.
set /p SERVER_IP=서버 IP 주소: 

if "%SERVER_IP%"=="" (
    echo [경고] IP 주소를 입력하지 않았습니다. localhost를 사용합니다.
    set SERVER_IP=localhost
)

echo.
echo 2. 클래스 비밀번호를 입력하세요
echo    (다른 선생님의 서버와 구분하기 위한 암호)
echo    예: math2025, room303, myclass 등
echo.
set /p CLUSTER_SECRET=클래스 비밀번호: 

if "%CLUSTER_SECRET%"=="" (
    echo [경고] 비밀번호를 입력하지 않았습니다. 기본값을 사용합니다.
    set CLUSTER_SECRET=airclass2025
)

echo.
echo 3. JWT 암호화 키를 생성합니다...
echo    (자동 생성됩니다)
echo.

REM JWT_SECRET_KEY 랜덤 생성 (PowerShell 사용)
for /f "delims=" %%i in ('powershell -Command "[guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()"') do set JWT_SECRET_KEY=%%i

echo ========================================
echo   설정 내용 확인
echo ========================================
echo.
echo 서버 IP 주소:      %SERVER_IP%
echo 클래스 비밀번호:   %CLUSTER_SECRET%
echo JWT 암호화 키:     %JWT_SECRET_KEY%
echo.
echo ========================================
echo.

set /p CONFIRM=이 설정으로 진행하시겠습니까? (Y/N): 

if /i not "%CONFIRM%"=="Y" (
    echo 설정을 취소했습니다.
    echo setup.bat를 다시 실행해주세요.
    pause
    exit /b 1
)

echo.
echo .env 파일 생성 중...

(
echo # AIRClass 서버 설정 파일
echo # 생성일: %date% %time%
echo.
echo # 서버 IP 주소 (학생들이 접속할 주소^)
echo SERVER_IP=%SERVER_IP%
echo.
echo # 프론트엔드 백엔드 URL
echo VITE_BACKEND_URL=http://%SERVER_IP%:8000
echo.
echo # CORS 설정 (* = 모든 도메인 허용^)
echo CORS_ORIGINS=*
echo.
echo # JWT 보안 키 (자동 생성^)
echo JWT_SECRET_KEY=%JWT_SECRET_KEY%
echo.
echo # Main 노드 WebRTC 사용 여부 (false = Sub 노드로 부하분산^)
echo USE_MAIN_WEBRTC=false
echo.
echo # 클러스터 보안: Main과 Sub 노드가 서로를 인증하는 비밀번호
echo # 다른 선생님의 서버와 구분하기 위해 사용됩니다
echo CLUSTER_SECRET=%CLUSTER_SECRET%
) > .env

echo.
echo ========================================
echo   설정이 완료되었습니다!
echo ========================================
echo.
echo 다음 단계:
echo   1. start.bat를 실행하여 서버를 시작하세요
echo   2. 브라우저에서 http://%SERVER_IP%:5173/teacher 접속
echo   3. 학생들에게 http://%SERVER_IP%:5173/student 주소 공유
echo.
echo 설정 변경: setup.bat 다시 실행
echo 서버 시작: start.bat 실행
echo.
pause
