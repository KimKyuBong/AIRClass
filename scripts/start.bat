@echo off
chcp 65001 >nul
echo ========================================
echo   AIRClass 실시간 스트리밍 시스템
echo ========================================
echo.

REM Docker 설치 확인
docker --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Docker가 설치되어 있지 않습니다.
    echo.
    echo Docker Desktop을 먼저 설치해주세요:
    echo https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

REM Docker 실행 확인
docker ps >nul 2>&1
if errorlevel 1 (
    echo [오류] Docker가 실행되고 있지 않습니다.
    echo.
    echo Docker Desktop을 실행해주세요.
    echo.
    pause
    exit /b 1
)

REM .env 파일 존재 확인
if not exist ".env" (
    echo [경고] .env 파일이 없습니다. 기본 설정으로 생성합니다.
    echo.
    call setup.bat
    if errorlevel 1 (
        echo [오류] 설정 파일 생성에 실패했습니다.
        pause
        exit /b 1
    )
)

echo [1단계] 기존 컨테이너 중지 중...
docker-compose down >nul 2>&1

echo [2단계] 최신 이미지 빌드 중... (최초 실행시 1-2분 소요)
docker-compose build
if errorlevel 1 (
    echo [오류] 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo [3단계] 서버 시작 중...
docker-compose up -d
if errorlevel 1 (
    echo [오류] 서버 시작에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   서버가 성공적으로 시작되었습니다!
echo ========================================
echo.

REM .env에서 SERVER_IP 읽기
for /f "tokens=2 delims==" %%a in ('findstr /r "^SERVER_IP=" .env') do set SERVER_IP=%%a

if "%SERVER_IP%"=="" (
    set SERVER_IP=localhost
)

echo 접속 주소:
echo   - 선생님 페이지: http://%SERVER_IP%:5173/teacher
echo   - 학생 페이지:   http://%SERVER_IP%:5173/student
echo   - 관리자 페이지: http://%SERVER_IP%:8000/cluster/nodes
echo.
echo 서버 중지: stop.bat 실행
echo 로그 보기: logs.bat 실행
echo.

REM 15초 대기 후 상태 확인
echo 서버 초기화 중... (15초 대기)
timeout /t 15 /nobreak >nul

echo.
echo [서버 상태 확인]
docker-compose ps

echo.
echo 선생님 페이지를 브라우저에서 열까요? (Y/N)
set /p OPEN_BROWSER=선택: 

if /i "%OPEN_BROWSER%"=="Y" (
    start http://%SERVER_IP%:5173/teacher
)

echo.
pause
