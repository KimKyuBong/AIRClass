#!/bin/bash

echo "🚀 Screen Capture Backend Starting..."
echo ""

# 가상환경이 없으면 생성
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 가상환경 활성화
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# 의존성 설치
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# 디렉토리 생성
mkdir -p static uploads

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting server..."
echo "   Web Viewer: http://localhost:8000/viewer"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# 서버 실행
python main.py
