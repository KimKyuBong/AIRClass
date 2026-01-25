@echo off
REM AIRClass - Unified CLI Interface for Windows

setlocal enabledelayedexpansion

if "%~1"=="" goto help
if "%~1"=="help" goto help
if "%~1"=="--help" goto help
if "%~1"=="-h" goto help

if "%~1"=="install" goto install
if "%~1"=="start" goto start
if "%~1"=="stop" goto stop
if "%~1"=="restart" goto restart
if "%~1"=="logs" goto logs
if "%~1"=="status" goto status
if "%~1"=="dev" goto dev
if "%~1"=="dev-stop" goto dev_stop
if "%~1"=="test" goto test
if "%~1"=="clean" goto clean

echo ❌ 알 수 없는 명령어: %~1
echo.
goto help

:help
echo AIRClass - 실시간 온라인 교실 플랫폼
echo.
echo 사용법: airclass.bat ^<command^>
echo.
echo 주요 명령어:
echo   install     초기 설치 및 설정
echo   start       서버 시작
echo   stop        서버 중지
echo   restart     서버 재시작
echo   logs        로그 확인
echo   status      서버 상태 확인
echo.
echo 개발 명령어:
echo   dev         개발 모드로 시작
echo   dev-stop    개발 서버 중지
echo   test        테스트 실행
echo   clean       임시 파일 정리
echo.
echo 도움말:
echo   help        이 메시지 출력
echo.
goto end

:install
echo 🚀 AIRClass 설치 시작...
call scripts\install\setup.bat
goto end

:start
echo ▶️  AIRClass 시작...
call scripts\start.bat
goto end

:stop
echo ⏹️  AIRClass 중지...
call scripts\stop.bat
goto end

:restart
echo 🔄 AIRClass 재시작...
call scripts\stop.bat
timeout /t 2 /nobreak >nul
call scripts\start.bat
goto end

:logs
call scripts\logs.bat
goto end

:status
call scripts\dev\status.bat
goto end

:dev
echo 🔧 개발 모드로 시작...
call scripts\dev\start-dev.bat
goto end

:dev_stop
echo 🔧 개발 서버 중지...
call scripts\dev\stop-dev.bat
goto end

:test
echo 🧪 테스트 실행...
cd backend
python -m pytest tests\ -v
cd ..
goto end

:clean
echo 🧹 임시 파일 정리...
if exist backend\__pycache__ rmdir /s /q backend\__pycache__
if exist backend\.pytest_cache rmdir /s /q backend\.pytest_cache
if exist frontend\dist rmdir /s /q frontend\dist
if exist frontend\.svelte-kit rmdir /s /q frontend\.svelte-kit
if exist logs\*.log del /q logs\*.log
for /r %%i in (*.pyc) do del "%%i"
for /d /r %%i in (__pycache__) do @if exist "%%i" rmdir /s /q "%%i"
echo ✅ 정리 완료
goto end

:end
endlocal
