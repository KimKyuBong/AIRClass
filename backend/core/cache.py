import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Cache:
    async def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        raise NotImplementedError

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self.set(key, json.dumps(value, ensure_ascii=False), ttl_seconds)


class InMemoryTTLCache(Cache):
    def __init__(self, max_items: int = 10_000):
        self._store: dict[str, tuple[float, str]] = {}
        self._max_items = max_items

    async def get(self, key: str) -> Optional[str]:
        now = time.time()
        item = self._store.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= now:
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        if len(self._store) >= self._max_items:
            self._store.pop(next(iter(self._store)), None)
        self._store[key] = (time.time() + ttl_seconds, value)


class RedisCache(Cache):
    def __init__(self, redis_client: Any):
        self._redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        value = await self._redis.get(key)
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8")
        return str(value)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._redis.set(key, value, ex=ttl_seconds)


_cache: Optional[Cache] = None


async def init_cache() -> Cache:
    global _cache

    backend = os.getenv("CACHE_BACKEND", "auto")  # auto|redis|memory
    max_items = int(os.getenv("CACHE_MAX_ITEMS", "10000"))
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")

    if backend == "memory":
        _cache = InMemoryTTLCache(max_items=max_items)
        logger.info("✅ Cache initialized: InMemoryTTLCache")
        return _cache

    if backend in {"auto", "redis"}:
        try:
            import redis.asyncio as redis  # type: ignore

            client = await redis.from_url(redis_url)
            await client.ping()
            _cache = RedisCache(client)
            logger.info("✅ Cache initialized: RedisCache")
            return _cache
        except Exception as e:
            if backend == "redis":
                raise
            logger.warning(f"⚠️ Redis cache unavailable, falling back to memory: {e}")

    _cache = InMemoryTTLCache(max_items=max_items)
    logger.info("✅ Cache initialized: InMemoryTTLCache (fallback)")
    return _cache


def get_cache() -> Optional[Cache]:
    return _cache
