"""
MediaMTX RTMP/WebRTC Server Management
MediaMTX 프로세스 시작 및 중지 관리
"""

import subprocess
import logging
import atexit
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Global MediaMTX process
_mediamtx_process: Optional[subprocess.Popen] = None


def start_mediamtx() -> None:
    """MediaMTX RTMP/WebRTC 서버 시작"""
    global _mediamtx_process

    if _mediamtx_process is None:
        logger.info("🚀 Starting MediaMTX server...")
        try:
            import os
            backend_dir = os.path.dirname(os.path.dirname(__file__))
            mediamtx_binary = os.path.join(backend_dir, "mediamtx")
            
            # 모드에 따라 적절한 설정 파일 선택
            mode = os.getenv("MODE", "standalone").lower()
            if mode == "main":
                config_file = os.path.join(backend_dir, "mediamtx-main.yml")
            elif mode == "sub":
                config_file = os.path.join(backend_dir, "mediamtx-sub.yml")
            else:  # standalone
                config_file = os.path.join(backend_dir, "mediamtx.yml")
            
            # MediaMTX 로그를 파일로 저장하여 디버깅 가능하도록
            import os as os_module
            log_dir = os_module.path.join(os_module.path.dirname(backend_dir), "logs")
            os_module.makedirs(log_dir, exist_ok=True)
            log_file = os_module.path.join(log_dir, "mediamtx.log")
            with open(log_file, "a") as log:
                log.write(f"\n=== MediaMTX started at {datetime.now()} ===\n")
                log.write(f"Config: {config_file}\n")
                log.write(f"Mode: {mode}\n")
            _mediamtx_process = subprocess.Popen(
                [mediamtx_binary, config_file], 
                stdout=open(log_file, "a"), 
                stderr=subprocess.STDOUT,
                cwd=backend_dir
            )
            logger.info(f"✅ MediaMTX started (PID: {_mediamtx_process.pid}) with config: {os.path.basename(config_file)}")
            logger.info("📡 RTMP: rtmp://localhost:1935/live/stream")
            logger.info("🎬 WebRTC: http://localhost:8889/live/stream/whep")
        except Exception as e:
            logger.error(f"❌ Failed to start MediaMTX: {e}")
            _mediamtx_process = None


def stop_mediamtx() -> None:
    """MediaMTX 서버 중지"""
    global _mediamtx_process

    if _mediamtx_process:
        logger.info("🛑 Stopping MediaMTX...")
        try:
            _mediamtx_process.terminate()
            _mediamtx_process.wait(timeout=5)
            logger.info("✅ MediaMTX stopped successfully")
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ MediaMTX did not stop gracefully, killing process...")
            _mediamtx_process.kill()
            _mediamtx_process.wait()
        finally:
            _mediamtx_process = None


def is_mediamtx_running() -> bool:
    """MediaMTX 서버 실행 중 여부 확인"""
    global _mediamtx_process
    return _mediamtx_process is not None and _mediamtx_process.poll() is None


def get_mediamtx_pid() -> Optional[int]:
    """MediaMTX 프로세스 ID 반환"""
    global _mediamtx_process
    if _mediamtx_process:
        return _mediamtx_process.pid
    return None


# 프로세스 종료 시 자동 cleanup
atexit.register(stop_mediamtx)
