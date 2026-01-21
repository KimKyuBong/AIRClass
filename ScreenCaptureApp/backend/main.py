"""
WebRTC Screen Streaming Server
MediaMTX를 사용한 실시간 화면 스트리밍 백엔드
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import subprocess
import os
import signal
import atexit
import json
import threading
import time

app = FastAPI(title="WebRTC Screen Streaming Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path("static_streaming")
mediamtx_process = None


def start_mediamtx():
    """MediaMTX RTMP/WebRTC 서버 시작"""
    global mediamtx_process

    if mediamtx_process is None:
        print("🚀 Starting MediaMTX server...")
        mediamtx_process = subprocess.Popen(
            ["./mediamtx"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(f"✅ MediaMTX started (PID: {mediamtx_process.pid})")
        print("📡 RTMP: rtmp://localhost:1935/live/stream")
        print("🌐 WebRTC: http://localhost:8889/live/stream/whep")


def stop_mediamtx():
    """MediaMTX 서버 중지"""
    global mediamtx_process

    if mediamtx_process:
        print("🛑 Stopping MediaMTX...")
        mediamtx_process.terminate()
        mediamtx_process.wait()
        mediamtx_process = None
        print("✅ MediaMTX stopped")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 MediaMTX 실행"""
    start_mediamtx()


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 MediaMTX 중지"""
    stop_mediamtx()


# 프로세스 종료 시 cleanup
atexit.register(stop_mediamtx)


@app.get("/")
async def root():
    """서버 상태 확인"""
    return {
        "status": "running",
        "service": "WebRTC Screen Streaming Server",
        "mediamtx_running": mediamtx_process is not None,
        "rtmp_url": "rtmp://localhost:1935/live/stream",
        "webrtc_viewer": "http://localhost:8000/viewer",
    }


@app.get("/viewer", response_class=HTMLResponse)
async def viewer():
    """WebRTC 뷰어 페이지"""
    html_path = STATIC_DIR / "webrtc_viewer.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(content="<h1>Viewer not found</h1>")


@app.get("/teacher", response_class=HTMLResponse)
async def teacher():
    """교사용 화면"""
    html_path = STATIC_DIR / "teacher.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(content="<h1>Teacher view not found</h1>")


@app.get("/student", response_class=HTMLResponse)
async def student():
    """학생용 화면"""
    html_path = STATIC_DIR / "student.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(content="<h1>Student view not found</h1>")


@app.get("/test", response_class=HTMLResponse)
async def test_viewer():
    """간단한 테스트 뷰어"""
    html_path = STATIC_DIR / "test_viewer.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(content="<h1>Test viewer not found</h1>")


# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static_streaming"), name="static")


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🎥 WebRTC Screen Streaming Server")
    print("=" * 60)
    print("📺 Viewer: http://localhost:8000/viewer")
    print("👨‍🏫 Teacher: http://localhost:8000/teacher")
    print("👨‍🎓 Student: http://localhost:8000/student")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # MediaMTX 프로세스 관리 때문에 reload 비활성화
        log_level="info",
    )
