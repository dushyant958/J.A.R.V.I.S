"""
Supabase client — persistent storage for conversations, preferences, and memories.

Uses supabase-py v2 REST API over HTTPS — no direct TCP connection needed,
so it works on any network without port 5432 being open.

Tables must be created once via Supabase Dashboard → SQL Editor.
Run the SQL in migrations/init.sql to initialise.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("jarvis.db")

_client = None


async def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        from supabase import acreate_client
        from friday.config import config

        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not set — database disabled")
            return None

        _client = await acreate_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("Supabase REST client connected: %s", config.SUPABASE_URL)
        return _client
    except ImportError:
        logger.warning("supabase package not installed — run: pip install supabase")
        return None
    except Exception as e:
        logger.error("Could not create Supabase client: %s", e)
        return None


class SupabaseClient:
    """
    Async Supabase client wrapping supabase-py v2.
    All methods are safe no-ops when Supabase is unavailable.

    Tables required (run migrations/init.sql in Supabase SQL Editor):
      - conversations
      - user_preferences
      - memories
      - tool_cache
    """

    def __init__(self, client):
        self._sb = client

    @property
    def available(self) -> bool:
        return self._sb is not None

    # ── Conversations ─────────────────────────────────────────────────────────

    async def save_message(self, session_id: str, role: str, content: str) -> None:
        if not self._sb:
            return
        try:
            await self._sb.table("conversations").insert(
                {"session_id": session_id, "role": role, "content": content}
            ).execute()
        except Exception as e:
            logger.error("save_message failed: %s", e)

    async def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        if not self._sb:
            return []
        try:
            result = await (
                self._sb.table("conversations")
                .select("role, content, created_at")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )
            return [{"role": r["role"], "content": r["content"]} for r in (result.data or [])]
        except Exception as e:
            logger.error("get_history failed: %s", e)
            return []

    # ── User Preferences ──────────────────────────────────────────────────────

    async def set_preference(self, key: str, value: Any) -> None:
        if not self._sb:
            return
        try:
            await (
                self._sb.table("user_preferences")
                .upsert({"key": key, "value": json.dumps(value)})
                .execute()
            )
        except Exception as e:
            logger.error("set_preference failed: %s", e)

    async def get_preference(self, key: str, default: Any = None) -> Any:
        if not self._sb:
            return default
        try:
            result = await (
                self._sb.table("user_preferences")
                .select("value")
                .eq("key", key)
                .maybe_single()
                .execute()
            )
            if result.data:
                return json.loads(result.data["value"])
            return default
        except Exception as e:
            logger.error("get_preference failed: %s", e)
            return default

    async def get_all_preferences(self) -> dict:
        if not self._sb:
            return {}
        try:
            result = await self._sb.table("user_preferences").select("key, value").execute()
            return {r["key"]: json.loads(r["value"]) for r in (result.data or [])}
        except Exception as e:
            logger.error("get_all_preferences failed: %s", e)
            return {}

    # ── Memories ──────────────────────────────────────────────────────────────

    async def save_memory(self, tag: str, content: str) -> None:
        if not self._sb:
            return
        try:
            await self._sb.table("memories").insert({"tag": tag, "content": content}).execute()
        except Exception as e:
            logger.error("save_memory failed: %s", e)

    async def get_memories(self, tag: str = None, limit: int = 10) -> list[dict]:
        if not self._sb:
            return []
        try:
            query = self._sb.table("memories").select("tag, content, created_at")
            if tag:
                query = query.eq("tag", tag)
            result = await query.order("created_at", desc=True).limit(limit).execute()
            return [{"tag": r["tag"], "content": r["content"]} for r in (result.data or [])]
        except Exception as e:
            logger.error("get_memories failed: %s", e)
            return []

    # ── Tool cache (DB fallback when Redis misses) ────────────────────────────

    async def cache_set(self, key: str, value: str, ttl_seconds: int = 3600) -> None:
        if not self._sb:
            return
        try:
            from datetime import datetime, timezone, timedelta
            expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
            await (
                self._sb.table("tool_cache")
                .upsert({"cache_key": key, "result": value, "expires_at": expires})
                .execute()
            )
        except Exception as e:
            logger.error("cache_set failed: %s", e)

    async def cache_get(self, key: str) -> str | None:
        if not self._sb:
            return None
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            result = await (
                self._sb.table("tool_cache")
                .select("result")
                .eq("cache_key", key)
                .gt("expires_at", now)
                .maybe_single()
                .execute()
            )
            return result.data["result"] if result.data else None
        except Exception as e:
            logger.error("cache_get failed: %s", e)
            return None


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: SupabaseClient | None = None


async def get_db() -> SupabaseClient:
    global _instance
    if _instance is None:
        client = await _get_client()
        _instance = SupabaseClient(client)
    return _instance
