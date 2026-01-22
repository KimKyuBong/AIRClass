@echo off
echo 🚀 Screen Capture Backend Starting...
echo.

REM 가상환경이 없으면 생성
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM 가상환경 활성화
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM 의존성 설치
echo 📥 Installing dependencies...
pip install -q -r requirements.txt

REM 디렉토리 생성
if not exist "static" mkdir static
if not exist "uploads" mkdir uploads

echo.
echo ✅ Setup complete!
echo.
echo 🌐 Starting server...
echo    Web Viewer: http://localhost:8000/viewer
echo    API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM 서버 실행
python main.py

pause
