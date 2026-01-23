@echo off
chcp 65001 >nul

REM 관리자 권한 확인 및 자동 상승
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 관리자 권한이 필요합니다. UAC 창에서 "예"를 클릭해주세요...
    echo.
    
    REM PowerShell로 관리자 권한 요청 및 재실행
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ========================================
echo   AIRClass 완전 자동 설치
echo   (Docker + AIRClass 모두 설치)
echo ========================================
echo.

echo [1/3] Docker 설치 확인 중...
docker --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ Docker가 이미 설치되어 있습니다.
    goto :check_docker_running
)

echo.
echo [Docker 미설치 감지]
echo Docker Desktop을 자동으로 다운로드하고 설치합니다.
echo.
echo 주의: 설치 중 컴퓨터가 재시작될 수 있습니다!
echo.
set /p CONTINUE=계속하시겠습니까? (Y/N): 
if /i not "%CONTINUE%"=="Y" (
    echo 설치를 취소했습니다.
    pause
    exit /b 1
)

echo.
echo [2/3] Docker Desktop 다운로드 중...
echo (약 500MB, 시간이 걸릴 수 있습니다)
echo.

REM 임시 폴더에 다운로드
set TEMP_DIR=%TEMP%\airclass-install
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

REM PowerShell로 Docker Desktop 다운로드
powershell -Command "& {Write-Host 'Docker Desktop 다운로드 중...' -ForegroundColor Yellow; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe' -OutFile '%TEMP_DIR%\DockerDesktopInstaller.exe'}"

if not exist "%TEMP_DIR%\DockerDesktopInstaller.exe" (
    echo [오류] Docker Desktop 다운로드에 실패했습니다.
    echo.
    echo 수동 설치 방법:
    echo 1. https://www.docker.com/products/docker-desktop 접속
    echo 2. "Download for Windows" 클릭
    echo 3. 다운로드한 파일 실행
    echo 4. 설치 후 이 스크립트를 다시 실행하세요.
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Docker Desktop 설치 중...
echo (설치 창이 나타납니다. 안내에 따라 진행하세요)
echo.

REM Docker Desktop 설치 실행
start /wait "" "%TEMP_DIR%\DockerDesktopInstaller.exe" install --quiet --accept-license

if %errorLevel% neq 0 (
    echo [경고] Docker 설치 중 문제가 발생했을 수 있습니다.
    echo 설치 창의 안내를 따라 수동으로 완료해주세요.
    echo.
)

echo.
echo ========================================
echo   Docker 설치가 완료되었습니다!
echo ========================================
echo.
echo 다음 단계:
echo 1. 컴퓨터를 재시작합니다 (Docker 적용을 위해 필요)
echo 2. 재시작 후 Docker Desktop을 실행합니다
echo 3. start.bat를 실행하여 AIRClass를 시작합니다
echo.
echo 지금 재시작하시겠습니까? (Y/N)
set /p REBOOT=선택: 

if /i "%REBOOT%"=="Y" (
    echo 5초 후 재시작합니다...
    timeout /t 5
    shutdown /r /t 0
) else (
    echo.
    echo 나중에 수동으로 재시작해주세요.
    echo 재시작 후 Docker Desktop 실행 → start.bat 실행
    echo.
    pause
)

exit /b 0

:check_docker_running
echo.
echo [2/3] Docker 실행 확인 중...
docker ps >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ Docker가 실행 중입니다.
    goto :install_airclass
)

echo.
echo [Docker 실행 필요]
echo Docker Desktop이 실행되고 있지 않습니다.
echo.
echo Docker Desktop을 시작하는 중...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo Docker Engine이 시작될 때까지 대기 중... (최대 60초)
set /a WAIT_COUNT=0
:wait_docker
timeout /t 5 /nobreak >nul
docker ps >nul 2>&1
if %errorLevel% equ 0 goto :docker_ready

set /a WAIT_COUNT+=1
if %WAIT_COUNT% lss 12 goto :wait_docker

echo.
echo [타임아웃] Docker가 60초 내에 시작되지 않았습니다.
echo.
echo 수동으로 Docker Desktop을 실행한 후
echo start.bat를 실행해주세요.
echo.
pause
exit /b 1

:docker_ready
echo ✓ Docker가 정상적으로 시작되었습니다!

:install_airclass
echo.
echo [3/3] AIRClass 설정 중...
echo.

REM setup.bat 실행
if exist "setup.bat" (
    call setup.bat
    if %errorLevel% neq 0 (
        echo [오류] AIRClass 설정에 실패했습니다.
        pause
        exit /b 1
    )
) else (
    echo [오류] setup.bat 파일을 찾을 수 없습니다.
    echo AIRClass 폴더에서 이 스크립트를 실행해주세요.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   설치가 완료되었습니다!
echo ========================================
echo.
echo 다음 명령어로 서버를 시작하세요:
echo   start.bat
echo.
echo 서버 시작 후 브라우저에서 접속:
for /f "tokens=2 delims==" %%a in ('findstr /r "^SERVER_IP=" .env 2^>nul') do set SERVER_IP=%%a
if "%SERVER_IP%"=="" set SERVER_IP=localhost
echo   - 선생님: http://%SERVER_IP%:5173/teacher
echo   - 학생:   http://%SERVER_IP%:5173/student
echo.
pause
