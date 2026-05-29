# J.A.R.V.I.S

> *"Just A Rather Very Intelligent System"* — a Tony Stark-inspired, voice-controlled personal AI that runs on your own machine.

J.A.R.V.I.S is a fully local-first voice assistant built around a **LiveKit Agents** voice pipeline and a **FastMCP** tool server. It listens through your microphone, reasons with an LLM, speaks back in a natural voice, and can actually *drive your computer* — open apps, search the web, read the news, click, type, take screenshots, and more.

It is woken up by a wake word (a double clap + the keyword "JARVIS"), talks to you in real time, and remembers things across sessions via a Supabase + Redis backend.

---

## Features

- **Wake-word activation** — double clap followed by saying *"JARVIS"* (`friday/wake/detector.py`)
- **Real-time voice pipeline** — STT → LLM → TTS over LiveKit Agents
- **MCP tool system** — every capability is exposed as an MCP tool, so the LLM can call them dynamically
- **Desktop control** — open applications, click, type, take screenshots, manage windows, run shell commands
- **Web tools** — DuckDuckGo search, URL fetching, world news, weather, open-URL
- **System tools** — current time, system info
- **Persistent memory** — Supabase Postgres for conversations / preferences / memories
- **Caching layer** — Redis Cloud with a `@cached(ttl=...)` decorator for tool responses
- **Auto-start on boot** — `setup_autostart.py` wires JARVIS into Windows startup

---

## Architecture

```
                    ┌────────────────────┐
   Double clap ────►│   Wake Detector    │  (clap × 2 + "JARVIS" keyword)
   + "JARVIS"       └─────────┬──────────┘
                              │ wakes
                              ▼
┌────────────────────────────────────────────────────────┐
│                   LiveKit Voice Agent                  │
│                    (agent_friday.py)                   │
│                                                        │
│   Mic ─► STT (Sarvam Saaras v3)                        │
│            │                                           │
│            ▼                                           │
│          LLM (Groq llama-3.3-70b, Gemini fallback)     │
│            │         ▲                                 │
│            │         │ tool calls / results            │
│            ▼         │                                 │
│          TTS (OpenAI nova) ─► Speaker                  │
└────────────────────────┬───────────────────────────────┘
                         │ SSE
                         ▼
              ┌────────────────────────┐
              │   FastMCP Server       │  (server.py, :8000/sse)
              │                        │
              │   friday/tools/        │
              │    ├─ web.py           │  search_web, fetch_url,
              │    │                   │  get_world_news, weather, open_url
              │    ├─ desktop.py       │  open_app, type_text, click,
              │    │                   │  screenshot, list_windows, run_shell
              │    └─ system.py        │  get_current_time, get_system_info
              └───────────┬────────────┘
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
     ┌──────────────┐          ┌──────────────┐
     │  Supabase    │          │ Redis Cloud  │
     │  (asyncpg)   │          │  (cache)     │
     │              │          │              │
     │ conversations│          │ tool_cache   │
     │ preferences  │          │              │
     │ memories     │          │              │
     └──────────────┘          └──────────────┘
```

---

## Tech stack

| Layer | Choice |
|-------|--------|
| LLM (primary) | Groq `llama-3.3-70b-versatile` |
| LLM (fallback) | Google Gemini 2.5 Flash |
| STT | Sarvam Saaras v3 (Indian-English optimised) |
| TTS | OpenAI `nova` |
| Voice framework | LiveKit Agents ≥ 1.5.1 |
| Tool framework | FastMCP (SSE transport) |
| Database | Supabase Postgres via `asyncpg` |
| Cache | Redis Cloud (`redis[asyncio]`) |
| Desktop control | `pyautogui`, `pygetwindow`, `Pillow` |
| Wake word | `sounddevice` + `SpeechRecognition` + custom clap detector |
| Package manager | `uv` |

---

## Project structure

```
J.A.R.V.I.S/
├── server.py              # uv run friday       → FastMCP server (SSE :8000)
├── agent_friday.py        # uv run friday_voice → LiveKit voice agent
├── wake.py                # uv run jarvis_wake  → wake-word listener
├── launcher.py            # orchestrates server + agent + wake together
├── setup_autostart.py     # installs JARVIS into Windows startup
│
├── pyproject.toml
├── .env.example           # copy → .env and fill in keys
│
├── migrations/
│   └── init.sql           # Supabase schema
│
└── friday/                # MCP server package
    ├── config.py          # env-var loading & settings
    ├── db/
    │   ├── supabase_client.py  # async Postgres client
    │   └── redis_cache.py      # @cached decorator
    ├── wake/
    │   └── detector.py         # ClapDetector + KeywordListener
    └── tools/
        ├── __init__.py    # tool registration
        ├── web.py         # search, news, weather, fetch
        ├── desktop.py     # full PC control
        ├── system.py      # time, system info
        └── utils.py
```

---

## Setup

### 1. Clone

```bash
git clone https://github.com/dushyant958/J.A.R.V.I.S.git
cd J.A.R.V.I.S
```

### 2. Install dependencies

This project uses [`uv`](https://github.com/astral-sh/uv):

```bash
uv sync
```

### 3. Environment variables

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

You will need API keys / credentials for:

- **Groq** — primary LLM
- **Google Gemini** — fallback LLM
- **Sarvam AI** — STT
- **OpenAI** — TTS (`nova` voice)
- **LiveKit** — URL, API key, API secret
- **Supabase** — Postgres connection string
- **Redis Cloud** — host, port, password

### 4. Database

Run the schema migration against your Supabase instance:

```bash
psql "$SUPABASE_URL" -f migrations/init.sql
```

This creates the `conversations`, `tool_cache`, `preferences`, and `memories` tables.

---

## Running

You can run the three processes individually, or use the launcher to spin them all up at once.

### Individually

```bash
# Terminal 1 — MCP tool server
uv run friday

# Terminal 2 — Voice agent (connects to MCP over SSE)
uv run friday_voice

# Terminal 3 — Wake-word listener
uv run jarvis_wake
```

### All at once

```bash
uv run python launcher.py
```

### Auto-start on Windows boot

```bash
uv run python setup_autostart.py
```

---

## How wake-word works

`friday/wake/detector.py` runs a lightweight always-on listener:

1. A **clap detector** watches the mic for two sharp amplitude spikes within a short window.
2. On a double-clap it arms a **keyword listener** that waits a few seconds for the word *"JARVIS"*.
3. If both fire, the LiveKit voice agent is activated and starts a conversation turn.

This keeps CPU and network cost at zero while idle — no LLM or STT calls happen until you explicitly wake it.

---

## Extending — adding a new tool

All capabilities are MCP tools. To add one:

1. Create (or open) a file under `friday/tools/`, e.g. `friday/tools/music.py`.
2. Define a function and decorate it so FastMCP picks it up.
3. Register it in `friday/tools/__init__.py` alongside the existing tools.
4. Use `@cached(ttl=300)` from `friday/db/redis_cache.py` for anything expensive / idempotent.
5. For DB access, call `get_db()` from `friday/db/supabase_client.py`.

The LLM will automatically discover the new tool over SSE — no prompt changes required.

---

## Status

Actively being built. Core voice loop, MCP server, web tools, desktop control, wake word, and database layers are all working.

---

## Contributors

**I am the only contributor to this project.** — Dushyant Atalkar

---

## License

Personal project. All rights reserved.
