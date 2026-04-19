# J.A.R.V.I.S — Project Context

## What this is
Tony Stark-style personal voice AI for Dushyant. Runs on his Windows 11 PC. Controlled entirely by voice. Full desktop control, web search, news, weather, app launching, shell commands.

## How to run (always two terminals)
```
Terminal 1:  python server.py [--reload]   # FastMCP tool server on :8001
Terminal 2:  uv run friday_voice           # LiveKit voice agent
```
Then connect via LiveKit Playground at https://agents-playground.livekit.io

## Stack
- **LLM**: Groq `llama-3.3-70b-versatile` (primary) — free tier 12k TPM, hits limits after ~5-6 exchanges
- **STT**: Sarvam Saaras v3 (`en-IN`)
- **TTS**: Sarvam Bulbul v3, speaker `advait`, pace 1.15
- **Voice pipeline**: LiveKit Agents 1.5.2+
- **Tools**: FastMCP over SSE on port 8001 (`MCP_PORT` in `.env`)
- **DB**: Supabase (asyncpg) + Redis Cloud

## Key files
| File | Role |
|------|------|
| `agent_friday.py` | LiveKit voice agent — STT/LLM/TTS wiring, system prompt, greeting |
| `server.py` | FastMCP MCP server entry point — registers all tools |
| `friday/tools/web.py` | News (RSS), search (DuckDuckGo), weather (wttr.in), fetch_url, open_url |
| `friday/tools/desktop.py` | Full PC control — open/close apps, click, type, screenshot, volume, shell |
| `friday/tools/system.py` | Time (IST), system info |
| `friday/db/supabase_client.py` | Async Postgres — table: `conversations` |
| `wake.py` | Wake word launcher (clap×2 or "JARVIS" keyword) |
| `dispatch.py` | Explicit LiveKit agent dispatch (not needed for normal use) |
| `test_tools.py` | Manual test suite — run `python test_tools.py all` |

## Config flags (top of agent_friday.py)
```python
LLM_PROVIDER = "groq"    # "groq" | "gemini" | "openai"
STT_PROVIDER = "sarvam"  # "sarvam" | "whisper"
TTS_PROVIDER = "sarvam"  # "sarvam" | "openai"
AUTO_GREET   = True      # False = JARVIS stays silent until user speaks first
MAX_HISTORY_ITEMS = 10   # conversation turns kept in context
```

## Known issues / gotchas
- **Groq 12k TPM limit**: hits after ~5-6 exchanges with tool calls. Real fix = paid Groq Dev tier ($5) or enable Gemini billing.
- **Port 8001 in use**: kill orphaned python.exe with `tasklist` then `taskkill /F /PID <pid>`
- **Timezone on Windows**: requires `tzdata` package — already in pyproject.toml
- **FastMCP port**: `mcp.run(transport='sse')` ignores constructor `port=` arg — server.py calls uvicorn directly to fix this
- **MCPToolset**: uses `livekit.agents.llm.mcp.MCPToolset`, NOT the deprecated `mcp_servers=[]` Agent kwarg
- **TTS reads raw data**: all tool return values must be plain prose — no markdown, no numbered lists, no dict keys with underscores
- **Explicit dispatch kills auto-connect**: do NOT set `agent_name` in WorkerOptions unless you also run `python dispatch.py` manually each session

## .env keys needed
```
LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
GROQ_API_KEY
GOOGLE_API_KEY
SARVAM_API_KEY
JARVIS_USER_NAME=Dushyant
MCP_PORT=8001
```

---

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
