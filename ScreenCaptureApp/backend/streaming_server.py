"""
실시간 비디오 스트리밍 서버 (HLS)
오디오 + 비디오 동시 스트리밍
"""

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import aiofiles
from pathlib import Path
import logging
import asyncio
import subprocess
import os
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Streaming Server")

# 디렉토리 생성
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

STREAM_DIR = Path("stream")
STREAM_DIR.mkdir(exist_ok=True)

STATIC_DIR = Path("static_streaming")
STATIC_DIR.mkdir(exist_ok=True)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 현재 스트리밍 정보
current_stream = {
    "video_file": None,
    "is_streaming": False,
    "ffmpeg_process": None,
    "start_time": None,
}


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Video Streaming Server",
        "streaming": current_stream["is_streaming"],
    }


@app.post("/upload/video")
async def upload_video(file: UploadFile = File(...)):
    """비디오 파일 업로드"""
    try:
        # 파일 저장
        filename = f"stream_{int(time.time())}.mp4"
        file_path = UPLOAD_DIR / filename

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Video uploaded: {filename} ({len(content)} bytes)")

        return {"success": True, "filename": filename, "size": len(content)}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream/start/{filename}")
async def start_streaming(filename: str):
    """비디오 스트리밍 시작 (HLS)"""
    try:
        video_path = UPLOAD_DIR / filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")

        # 기존 스트리밍 중지
        if current_stream["ffmpeg_process"]:
            current_stream["ffmpeg_process"].terminate()
            current_stream["ffmpeg_process"].wait()

        # HLS 출력 디렉토리 정리
        for f in STREAM_DIR.glob("*"):
            f.unlink()

        # FFmpeg로 HLS 변환
        output_path = STREAM_DIR / "stream.m3u8"

        # FFmpeg 명령어 (DVR 모드 - 과거 세그먼트 모두 유지)
        ffmpeg_cmd = [
            "ffmpeg",
            "-stream_loop",
            "-1",  # 무한 반복
            "-re",  # 실시간 속도
            "-i",
            str(video_path),
            "-c:v",
            "libx264",  # 비디오 코덱
            "-preset",
            "ultrafast",  # 빠른 인코딩
            "-tune",
            "zerolatency",  # 저지연
            "-c:a",
            "aac",  # 오디오 코덱
            "-b:a",
            "128k",  # 오디오 비트레이트
            "-f",
            "hls",  # HLS 포맷
            "-hls_time",
            "2",  # 세그먼트 길이 (초)
            "-hls_list_size",
            "0",  # 0 = 모든 세그먼트 유지 (DVR)
            "-hls_flags",
            "append_list",  # 세그먼트 계속 추가
            "-hls_segment_filename",
            str(STREAM_DIR / "segment%05d.ts"),  # 더 많은 숫자 자리
            str(output_path),
        ]

        # FFmpeg 프로세스 시작
        process = subprocess.Popen(
            ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        current_stream["video_file"] = filename
        current_stream["is_streaming"] = True
        current_stream["ffmpeg_process"] = process
        current_stream["start_time"] = time.time()

        logger.info(f"Streaming started: {filename}")

        return {
            "success": True,
            "filename": filename,
            "stream_url": "/stream/stream.m3u8",
        }

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream/{filename}")
async def get_stream_file(filename: str):
    """HLS 스트림 파일 제공"""
    file_path = STREAM_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stream file not found")

    # m3u8 파일은 text/plain, ts 파일은 video/MP2T
    media_type = (
        "application/vnd.apple.mpegurl" if filename.endswith(".m3u8") else "video/MP2T"
    )

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.get("/stream/stop")
async def stop_streaming():
    """스트리밍 중지"""
    if current_stream["ffmpeg_process"]:
        current_stream["ffmpeg_process"].terminate()
        current_stream["ffmpeg_process"].wait()
        current_stream["ffmpeg_process"] = None

    current_stream["is_streaming"] = False

    return {"success": True, "message": "Streaming stopped"}


@app.get("/viewer", response_class=HTMLResponse)
async def video_viewer():
    """비디오 뷰어 페이지"""
    html_path = STATIC_DIR / "video_viewer.html"
    if html_path.exists():
        async with aiofiles.open(html_path, "r", encoding="utf-8") as f:
            content = await f.read()
        return HTMLResponse(content=content)
    else:
        return HTMLResponse(content="<h1>Video viewer not found</h1>")


# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static_streaming"), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("streaming_server:app", host="0.0.0.0", port=8000, reload=True)
