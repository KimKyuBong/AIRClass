"""
LiveKit 서버 프로세스 관리자

FastAPI lifespan에서 LiveKit 서버를 subprocess로 실행/종료
"""

import asyncio
import subprocess
import signal
import sys
from pathlib import Path
from typing import Optional
import logging

from core.livekit_config import LiveKitConfigGenerator

logger = logging.getLogger(__name__)


class LiveKitManager:
    """LiveKit 서버 프로세스 관리자"""

    def __init__(
        self,
        node_id: str,
        mode: str,
        redis_url: str,
        livekit_binary: str = "livekit-server",
        config_path: Optional[Path] = None,
    ):
        """
        Args:
            node_id: 노드 ID
            mode: 클러스터 모드 (main/sub/standalone)
            redis_url: Redis 연결 URL
            livekit_binary: LiveKit 바이너리 경로 (PATH에 있으면 "livekit-server")
            config_path: 설정 파일 경로 (None이면 자동 생성)
        """
        self.node_id = node_id
        self.mode = mode
        self.redis_url = redis_url
        self.livekit_binary = livekit_binary
        self.config_path = config_path
        self.process: Optional[subprocess.Popen] = None
        self.config_generator: Optional[LiveKitConfigGenerator] = None

    async def start(self) -> bool:
        """
        LiveKit 서버 시작

        Returns:
            bool: 시작 성공 여부
        """
        try:
            # 1. 설정 파일 생성
            if self.config_path is None:
                self.config_generator = LiveKitConfigGenerator(
                    node_id=self.node_id,
                    mode=self.mode,
                    redis_url=self.redis_url,
                )
                self.config_path = self.config_generator.save_to_file()

            logger.info(f"LiveKit 서버 시작 중... (노드: {self.node_id}, 모드: {self.mode})")
            logger.info(f"설정 파일: {self.config_path}")

            # 2. LiveKit 프로세스 시작
            self.process = subprocess.Popen(
                [
                    self.livekit_binary,
                    "--config",
                    str(self.config_path),
                    # LiveKit 1.9.x는 --node-id 플래그를 사용하지 않음
                    # 노드 ID는 config 파일에서 설정하거나 자동 생성
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 라인 버퍼링
            )

            # 3. 시작 확인 (비동기)
            await asyncio.sleep(2)  # LiveKit 초기화 대기

            if self.process.poll() is not None:
                # 프로세스가 이미 종료됨
                stdout, stderr = self.process.communicate()
                logger.error(f"LiveKit 서버 시작 실패:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False

            logger.info(f"✅ LiveKit 서버 시작 완료 (PID: {self.process.pid})")

            # 4. 로그 모니터링 태스크 시작
            asyncio.create_task(self._monitor_logs())

            return True

        except FileNotFoundError:
            logger.error(f"LiveKit 바이너리를 찾을 수 없습니다: {self.livekit_binary}")
            logger.error("LiveKit을 설치하거나 LIVEKIT_BINARY 환경변수를 설정하세요.")
            return False
        except Exception as e:
            logger.error(f"LiveKit 서버 시작 중 오류: {e}")
            return False

    async def _monitor_logs(self):
        """LiveKit 로그 모니터링 (비동기)"""
        if not self.process:
            return

        try:
            # stdout 모니터링
            if self.process.stdout:
                async for line in self._async_read_stream(self.process.stdout):
                    logger.debug(f"[LiveKit] {line}")

            # stderr 모니터링
            if self.process.stderr:
                async for line in self._async_read_stream(self.process.stderr):
                    if "error" in line.lower() or "fatal" in line.lower():
                        logger.error(f"[LiveKit ERROR] {line}")
                    else:
                        logger.warning(f"[LiveKit] {line}")
        except Exception as e:
            logger.error(f"로그 모니터링 오류: {e}")

    async def _async_read_stream(self, stream):
        """스트림을 비동기로 읽기"""
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, stream.readline)
            if not line:
                break
            yield line.strip()

    async def stop(self):
        """LiveKit 서버 종료"""
        if not self.process:
            logger.warning("LiveKit 프로세스가 실행되지 않았습니다.")
            return

        try:
            logger.info(f"LiveKit 서버 종료 중... (PID: {self.process.pid})")

            # 1. SIGTERM 전송 (graceful shutdown)
            self.process.send_signal(signal.SIGTERM)

            # 2. 최대 10초 대기
            try:
                await asyncio.wait_for(asyncio.to_thread(self.process.wait), timeout=10.0)
                logger.info("✅ LiveKit 서버 정상 종료")
            except asyncio.TimeoutError:
                # 3. 강제 종료
                logger.warning("LiveKit 서버가 응답하지 않습니다. 강제 종료합니다.")
                self.process.kill()
                await asyncio.to_thread(self.process.wait)
                logger.warning("⚠️ LiveKit 서버 강제 종료됨")

            self.process = None

        except Exception as e:
            logger.error(f"LiveKit 서버 종료 중 오류: {e}")

    def is_running(self) -> bool:
        """LiveKit 서버 실행 상태 확인"""
        if not self.process:
            return False
        return self.process.poll() is None

    async def restart(self) -> bool:
        """LiveKit 서버 재시작"""
        logger.info("LiveKit 서버 재시작 중...")
        await self.stop()
        await asyncio.sleep(1)
        return await self.start()

    def get_websocket_url(self) -> Optional[str]:
        """LiveKit WebSocket URL 반환"""
        if self.config_generator:
            return self.config_generator.get_websocket_url()
        return None

    def get_http_url(self) -> Optional[str]:
        """LiveKit HTTP API URL 반환"""
        if self.config_generator:
            return self.config_generator.get_http_url()
        return None


# 전역 인스턴스
_livekit_manager: Optional[LiveKitManager] = None


def get_livekit_manager() -> Optional[LiveKitManager]:
    """전역 LiveKitManager 인스턴스 반환"""
    return _livekit_manager


async def init_livekit_manager(
    node_id: str,
    mode: str,
    redis_url: str,
    livekit_binary: str = "livekit-server",
) -> LiveKitManager:
    """
    LiveKitManager 초기화 및 시작

    Args:
        node_id: 노드 ID
        mode: 클러스터 모드
        redis_url: Redis URL
        livekit_binary: LiveKit 바이너리 경로

    Returns:
        LiveKitManager: 초기화된 매니저 인스턴스
    """
    global _livekit_manager

    _livekit_manager = LiveKitManager(
        node_id=node_id,
        mode=mode,
        redis_url=redis_url,
        livekit_binary=livekit_binary,
    )

    success = await _livekit_manager.start()
    if not success:
        raise RuntimeError("LiveKit 서버 시작 실패")

    return _livekit_manager


async def shutdown_livekit_manager():
    """LiveKitManager 종료"""
    global _livekit_manager

    if _livekit_manager:
        await _livekit_manager.stop()
        _livekit_manager = None


if __name__ == "__main__":
    # 테스트: LiveKit 서버 시작/종료
    async def test():
        manager = LiveKitManager(
            node_id="test-node",
            mode="standalone",
            redis_url="redis://localhost:6379",
        )

        print("Starting LiveKit server...")
        success = await manager.start()
        print(f"Start result: {success}")

        if success:
            print(f"WebSocket URL: {manager.get_websocket_url()}")
            print(f"HTTP URL: {manager.get_http_url()}")
            print(f"Is running: {manager.is_running()}")

            # 10초 대기
            await asyncio.sleep(10)

            print("Stopping LiveKit server...")
            await manager.stop()
            print(f"Is running: {manager.is_running()}")

    asyncio.run(test())
