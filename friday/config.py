"""
Configuration — load environment variables and app-wide settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Server identity ──────────────────────────────────────────────────────
    SERVER_NAME: str = os.getenv("SERVER_NAME", "JARVIS")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── User Profile ─────────────────────────────────────────────────────────
    USER_NAME: str = os.getenv("JARVIS_USER_NAME", "Boss")
    USER_TIMEZONE: str = os.getenv("JARVIS_USER_TIMEZONE", "Asia/Kolkata")

    # ── LLM Providers ────────────────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ── STT / TTS ────────────────────────────────────────────────────────────
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "")

    # ── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")        # service_role — for backend
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")  # anon — for client-side
    # Individual DB params (avoids URL-encoding issues with special chars in password)
    SUPABASE_DB_HOST: str = os.getenv("SUPABASE_DB_HOST", "")
    SUPABASE_DB_PORT: int = int(os.getenv("SUPABASE_DB_PORT", "5432"))
    SUPABASE_DB_NAME: str = os.getenv("SUPABASE_DB_NAME", "postgres")
    SUPABASE_DB_USER: str = os.getenv("SUPABASE_DB_USER", "postgres")
    SUPABASE_DB_PASSWORD: str = os.getenv("SUPABASE_DB_PASSWORD", "")

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_USERNAME: str = os.getenv("REDIS_USERNAME", "default")

    # ── MCP Server ───────────────────────────────────────────────────────────
    MCP_PORT: int = int(os.getenv("MCP_PORT", "8001"))

    # ── Search ───────────────────────────────────────────────────────────────
    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")


config = Config()
