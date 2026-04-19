"""
J.A.R.V.I.S – Voice Agent (MCP-powered)
=========================================
Tony Stark-style personal AI for Dushyant.
LLM: Google Gemini 2.5 Flash — primary
     Groq llama-3.3-70b — fallback
STT: Sarvam Saaras v3 (Indian-English optimised)
TTS: Sarvam Bulbul v3 (advait)

Run:
  uv run friday_voice        – LiveKit Cloud mode (auto-injects 'dev')
  uv run friday_voice console – text-only console mode
"""

import os
import logging
from zoneinfo import ZoneInfo
from datetime import datetime

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli, utils as lk_utils
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.llm import mcp, ChatContext
from livekit.agents.llm.mcp import MCPToolset

from livekit.plugins import openai as lk_openai, google as lk_google, sarvam, silero

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

STT_PROVIDER = "sarvam"    # "sarvam" | "whisper"
LLM_PROVIDER = "groq"      # "groq" | "gemini" | "openai"
TTS_PROVIDER = "sarvam"    # "sarvam" | "openai"

AUTO_GREET = True          # False = stay silent until user speaks first

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GEMINI_LLM_MODEL = "gemini-2.0-flash"  # free tier: 15 RPM vs 5 RPM for 2.5-flash
OPENAI_LLM_MODEL = "gpt-4o-mini"

OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "nova"
TTS_SPEED = 1.15

SARVAM_TTS_LANGUAGE = "en-IN"
SARVAM_TTS_SPEAKER = "advait"

MCP_SERVER_PORT = int(os.getenv("MCP_PORT", "8001"))

# Max conversation turns kept in context — keeps token usage bounded
MAX_HISTORY_ITEMS = 10

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

USER_NAME = os.getenv("JARVIS_USER_NAME", "Boss")

SYSTEM_PROMPT = f"""You are J.A.R.V.I.S, the personal AI of {USER_NAME}. You run on his PC with full desktop, browser, and web access. Timezone: IST.

Personality: calm, composed, dry wit. Greet {USER_NAME} by name once per session, then just talk naturally. Two to four sentences max. Never mention tool names.

Speech rules — you are being spoken aloud via TTS:
- No markdown, no lists, no bullet points, no numbered items, no asterisks, no underscores.
- Never read out raw data. Always convert tool results into natural spoken sentences.
- For news: pick the two or three most interesting headlines and say them conversationally.
- For time/date: say it as a human would ("It's half past nine on a Sunday evening").
- For search results: summarise the key fact in one sentence, don't list sources.

Action rules:
- Answer from knowledge first. Only use tools for live data (weather, news, prices, desktop actions).
- Act first, then report. Don't announce what you're about to do.
- Screenshot before clicking. If a tool fails, say so calmly.
- Stay in character always. You are J.A.R.V.I.S, not a chatbot.""".strip()

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv(override=True)
logger = logging.getLogger("jarvis-agent")
logger.setLevel(logging.INFO)

_groq_key = os.getenv("GROQ_API_KEY", "")
_google_key = os.getenv("GOOGLE_API_KEY", "")
logger.info("GROQ_API_KEY   = %s", f"{_groq_key[:8]}..." if _groq_key else "NOT SET")
logger.info("GOOGLE_API_KEY = %s", f"{_google_key[:8]}..." if _google_key else "NOT SET")
logger.info("LLM_PROVIDER   = %s", LLM_PROVIDER)


# ---------------------------------------------------------------------------
# MCP toolset
# ---------------------------------------------------------------------------

def _build_mcp_toolset() -> MCPToolset:
    url = f"http://127.0.0.1:{MCP_SERVER_PORT}/sse"
    logger.info("MCP Server: %s", url)
    server = mcp.MCPServerHTTP(
        url=url,
        transport_type="sse",
        client_session_timeout_seconds=30,
    )
    return MCPToolset(id=lk_utils.shortuuid("mcp_"), mcp_server=server)


# ---------------------------------------------------------------------------
# Build provider instances
# ---------------------------------------------------------------------------

def _build_stt():
    if STT_PROVIDER == "sarvam":
        logger.info("STT -> Sarvam (en-IN)")
        return sarvam.STT(language="en-IN")
    elif STT_PROVIDER == "whisper":
        logger.info("STT -> OpenAI Whisper")
        return lk_openai.STT(model="whisper-1")
    else:
        raise ValueError(f"Unknown STT_PROVIDER: {STT_PROVIDER!r}")


def _build_llm():
    if LLM_PROVIDER == "groq":
        logger.info("LLM -> Groq (%s)", GROQ_MODEL)
        return lk_openai.LLM(
            model=GROQ_MODEL,
            base_url=GROQ_BASE_URL,
            api_key=os.getenv("GROQ_API_KEY"),
        )
    elif LLM_PROVIDER == "gemini":
        logger.info("LLM -> Gemini (%s) with Groq fallback", GEMINI_LLM_MODEL)
        return lk_google.LLM(
            model=GEMINI_LLM_MODEL,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    elif LLM_PROVIDER == "openai":
        logger.info("LLM -> OpenAI (%s)", OPENAI_LLM_MODEL)
        return lk_openai.LLM(model=OPENAI_LLM_MODEL)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")


def _build_tts():
    if TTS_PROVIDER == "sarvam":
        logger.info("TTS -> Sarvam Bulbul v3 (advait)")
        return sarvam.TTS(
            target_language_code="en-IN",
            model="bulbul:v3",
            speaker="advait",
            pace=TTS_SPEED,
        )
    elif TTS_PROVIDER == "openai":
        logger.info("TTS -> OpenAI TTS (%s / %s)", OPENAI_TTS_MODEL, OPENAI_TTS_VOICE)
        return lk_openai.TTS(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            speed=TTS_SPEED,
        )
    else:
        raise ValueError(f"Unknown TTS_PROVIDER: {TTS_PROVIDER!r}")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class JarvisAgent(Agent):
    """J.A.R.V.I.S — full-desktop AI for Dushyant."""

    def __init__(self, stt, llm, tts) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(),
            tools=[_build_mcp_toolset()],
        )

    async def on_enter(self) -> None:
        if not AUTO_GREET:
            return
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        time_str = now.strftime("%I:%M %p")
        await self.session.generate_reply(
            instructions=(
                f"Greet {USER_NAME} in one short sentence. "
                f"Current time is {time_str} IST. Dry wit, stay in character as J.A.R.V.I.S."
            )
        )

    async def llm_node(self, chat_ctx: ChatContext, tools, model_settings):
        truncated = chat_ctx.truncate(max_items=MAX_HISTORY_ITEMS)
        return Agent.default.llm_node(self, truncated, tools, model_settings)


# ---------------------------------------------------------------------------
# LiveKit entry point
# ---------------------------------------------------------------------------

async def entrypoint(ctx: JobContext) -> None:
    logger.info("JARVIS entrypoint called — room: %s", ctx.room.name)

    try:
        stt = _build_stt()
        llm = _build_llm()
        tts = _build_tts()

        session = AgentSession(
            turn_detection="vad",
            min_endpointing_delay=0.3,
        )

        await session.start(
            agent=JarvisAgent(stt=stt, llm=llm, tts=tts),
            room=ctx.room,
        )
        logger.info("JARVIS agent started successfully")
    except Exception:
        logger.exception("JARVIS startup failed")
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


def dev():
    import sys
    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()


if __name__ == "__main__":
    main()
