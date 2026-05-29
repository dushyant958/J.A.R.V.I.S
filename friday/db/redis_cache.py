"""
Redis cache layer — hot in-memory cache sitting in front of Supabase.
Falls back gracefully if Redis is unavailable.
"""

import asyncio
import functools
import hashlib
import json
import logging
from typing import Any, Callable

logger = logging.getLogger("jarvis.cache")

_client = None


async def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        import redis.asyncio as aioredis
        from friday.config import config

        if not config.REDIS_HOST or not config.REDIS_PASSWORD:
            logger.warning("Redis not configured — caching disabled")
            return None

        _client = aioredis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            username=config.REDIS_USERNAME,
            password=config.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        await _client.ping()
        logger.info("Redis connected: %s:%s", config.REDIS_HOST, config.REDIS_PORT)
        return _client
    except ImportError:
        logger.warning("redis package not installed — run: uv add redis")
        return None
    except Exception as e:
        logger.warning("Redis unavailable: %s — falling back to no cache", e)
        _client = None
        return None


class RedisCache:
    """
    Async Redis wrapper. All methods are no-ops when Redis is unavailable.
    Default TTL values:
      - News / search results: 300s (5 min)
      - Weather: 1800s (30 min)
      - Preferences: 86400s (24 h)
    """

    def __init__(self, client):
        self._r = client

    @property
    def available(self) -> bool:
        return self._r is not None

    async def get(self, key: str) -> Any | None:
        if not self._r:
            return None
        try:
            val = await self._r.get(f"jarvis:{key}")
            return json.loads(val) if val else None
        except Exception as e:
            logger.debug("Cache get error: %s", e)
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if not self._r:
            return
        try:
            await self._r.setex(f"jarvis:{key}", ttl, json.dumps(value))
        except Exception as e:
            logger.debug("Cache set error: %s", e)

    async def delete(self, key: str) -> None:
        if not self._r:
            return
        try:
            await self._r.delete(f"jarvis:{key}")
        except Exception as e:
            logger.debug("Cache delete error: %s", e)

    async def flush_prefix(self, prefix: str) -> int:
        """Delete all keys matching jarvis:{prefix}*. Returns number of keys deleted."""
        if not self._r:
            return 0
        try:
            keys = await self._r.keys(f"jarvis:{prefix}*")
            if keys:
                return await self._r.delete(*keys)
            return 0
        except Exception as e:
            logger.debug("Cache flush error: %s", e)
            return 0

    async def exists(self, key: str) -> bool:
        if not self._r:
            return False
        try:
            return bool(await self._r.exists(f"jarvis:{key}"))
        except Exception:
            return False

    async def get_status(self) -> dict:
        if not self._r:
            return {"connected": False}
        try:
            info = await self._r.info("memory")
            return {
                "connected": True,
                "used_memory_human": info.get("used_memory_human"),
                "maxmemory_human": info.get("maxmemory_human"),
            }
        except Exception:
            return {"connected": False}


# ── Singleton ─────────────────────────────────────────────────────────────────

_cache_instance: RedisCache | None = None


async def get_cache() -> RedisCache:
    global _cache_instance
    if _cache_instance is None:
        r = await _get_client()
        _cache_instance = RedisCache(r)
    return _cache_instance


# ── Decorator for caching tool results ───────────────────────────────────────

def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator that caches the return value of an async function in Redis.
    Cache key = prefix + SHA256 of all arguments.
    Falls back to calling the function directly if Redis is unavailable.

    Usage:
        @cached(ttl=300, key_prefix="news")
        async def get_world_news() -> str:
            ...
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            cache = await get_cache()
            raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
            digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
            cache_key = f"{key_prefix or fn.__name__}:{digest}"

            cached_val = await cache.get(cache_key)
            if cached_val is not None:
                logger.debug("Cache HIT: %s", cache_key)
                return cached_val

            logger.debug("Cache MISS: %s", cache_key)
            result = await fn(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
