-- J.A.R.V.I.S — Supabase Schema
-- Run this once in: Supabase Dashboard → SQL Editor → New Query → Run

-- Conversation history
CREATE TABLE IF NOT EXISTS conversations (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT        NOT NULL,
    role        TEXT        NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id, created_at);

-- User preferences (key-value)
CREATE TABLE IF NOT EXISTS user_preferences (
    key         TEXT PRIMARY KEY,
    value       TEXT        NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Long-term memories (tagged notes JARVIS keeps about Dushyant)
CREATE TABLE IF NOT EXISTS memories (
    id          BIGSERIAL PRIMARY KEY,
    tag         TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_memories_tag ON memories(tag);

-- Tool result cache (DB-level fallback when Redis is cold)
CREATE TABLE IF NOT EXISTS tool_cache (
    cache_key   TEXT PRIMARY KEY,
    result      TEXT        NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tool_cache_expiry ON tool_cache(expires_at);

-- Seed default preferences for Dushyant
INSERT INTO user_preferences (key, value) VALUES
    ('user_name',   '"Dushyant"'),
    ('timezone',    '"Asia/Kolkata"'),
    ('tts_voice',   '"nova"'),
    ('llm_model',   '"llama-3.3-70b-versatile"')
ON CONFLICT (key) DO NOTHING;
