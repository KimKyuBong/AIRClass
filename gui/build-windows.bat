@echo off
chcp 65001 >nul
echo ========================================
echo   AIRClass GUI 실행 파일 빌드
echo   (Windows .exe 생성)
echo ========================================
echo.

cd /d "%~dp0"

REM Python 설치 확인
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 설치해주세요.
    pause
    exit /b 1
)

echo [1/3] 필요한 패키지 설치 중...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [2/3] 실행 파일 빌드 중...
echo (시간이 걸릴 수 있습니다)
echo.

pyinstaller --name="AIRClass" ^
    --onefile ^
    --windowed ^
    --icon=NONE ^
    --add-data="../.env;." ^
    --add-data="../docker-compose.yml;." ^
    --hidden-import=customtkinter ^
    --hidden-import=PIL ^
    --hidden-import=dotenv ^
    airclass_gui.py

if %errorLevel% neq 0 (
    echo [오류] 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [3/3] 빌드 완료!
echo.
echo 생성된 파일:
echo   dist\AIRClass.exe
echo.
echo 사용 방법:
echo   1. dist\AIRClass.exe를 AIRClass 프로젝트 폴더에 복사
echo   2. AIRClass.exe 더블클릭으로 실행
echo.
pause
