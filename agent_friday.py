"""
J.A.R.V.I.S – Voice Agent (MCP-powered)
=========================================
Tony Stark-style personal AI for Dushyant.
LLM: Groq (llama-3.3-70b-versatile) — primary, ultra-fast inference
     Google Gemini 2.5 Flash — fallback
STT: Sarvam Saaras v3 (Indian-English optimised)
TTS: OpenAI nova

Run:
  uv run friday_voice        – LiveKit Cloud mode (auto-injects 'dev')
  uv run friday_voice console – text-only console mode
"""

import os
import logging

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.llm import mcp

from livekit.plugins import openai as lk_openai, google as lk_google, sarvam, silero

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

STT_PROVIDER = "sarvam"    # "sarvam" | "whisper"
LLM_PROVIDER = "gemini"    # "groq" | "gemini" | "openai"
TTS_PROVIDER = "sarvam"    # "sarvam" | "openai"

# Groq — best balance of speed + quality for voice
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Fallback models
GEMINI_LLM_MODEL = "gemini-2.5-flash"
OPENAI_LLM_MODEL = "gpt-4o-mini"

OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "nova"
TTS_SPEED = 1.15

SARVAM_TTS_LANGUAGE = "en-IN"
SARVAM_TTS_SPEAKER = "rahul"

MCP_SERVER_PORT = int(os.getenv("MCP_PORT", "8001"))

# ---------------------------------------------------------------------------
# System prompt — personalised for Dushyant
# ---------------------------------------------------------------------------

USER_NAME = os.getenv("JARVIS_USER_NAME", "Boss")

SYSTEM_PROMPT = f"""You are J.A.R.V.I.S, the personal AI of {USER_NAME}. You run on his PC with full desktop, browser, and web access. Timezone: IST.

Personality: calm, composed, dry wit. Greet {USER_NAME} by name once per session, then just talk naturally. Two to four sentences max. No markdown, no lists — you are speaking. Never mention tool names.

Rules:
- Answer from knowledge first. Only search the web for live data (weather, news, prices).
- Act first, then report. Don't announce what you're about to do.
- Screenshot before clicking. If a tool fails, say so calmly.
- Stay in character always. You are J.A.R.V.I.S, not a chatbot.""".strip()

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv(override=True)
logger = logging.getLogger("jarvis-agent")
logger.setLevel(logging.INFO)

# Debug: verify which keys are actually loaded
_groq_key = os.getenv("GROQ_API_KEY", "")
_google_key = os.getenv("GOOGLE_API_KEY", "")
print(f"[BOOT] GROQ_API_KEY   = {_groq_key[:8]}...{_groq_key[-4:]}" if _groq_key else "[BOOT] GROQ_API_KEY   = NOT SET")
print(f"[BOOT] GOOGLE_API_KEY = {_google_key[:8]}...{_google_key[-4:]}" if _google_key else "[BOOT] GOOGLE_API_KEY = NOT SET")
print(f"[BOOT] LLM_PROVIDER   = {LLM_PROVIDER}")


# ---------------------------------------------------------------------------
# MCP server URL
# ---------------------------------------------------------------------------

def _mcp_server_url() -> str:
    url = f"http://127.0.0.1:{MCP_SERVER_PORT}/sse"
    logger.info("MCP Server: %s", url)
    return url


# ---------------------------------------------------------------------------
# Build provider instances
# ---------------------------------------------------------------------------

def _build_stt():
    if STT_PROVIDER == "sarvam":
        logger.info("STT → Sarvam (en-IN, defaults)")
        return sarvam.STT(language="en-IN")
    elif STT_PROVIDER == "whisper":
        logger.info("STT → OpenAI Whisper")
        return lk_openai.STT(model="whisper-1")
    else:
        raise ValueError(f"Unknown STT_PROVIDER: {STT_PROVIDER!r}")


def _build_llm():
    if LLM_PROVIDER == "groq":
        logger.info("LLM → Groq (%s)", GROQ_MODEL)
        # Groq uses OpenAI-compatible API — fastest inference available
        return lk_openai.LLM(
            model=GROQ_MODEL,
            base_url=GROQ_BASE_URL,
            api_key=os.getenv("GROQ_API_KEY"),
        )
    elif LLM_PROVIDER == "gemini":
        logger.info("LLM → Google Gemini (%s)", GEMINI_LLM_MODEL)
        return lk_google.LLM(
            model=GEMINI_LLM_MODEL,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    elif LLM_PROVIDER == "openai":
        logger.info("LLM → OpenAI (%s)", OPENAI_LLM_MODEL)
        return lk_openai.LLM(model=OPENAI_LLM_MODEL)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")


def _build_tts():
    if TTS_PROVIDER == "sarvam":
        logger.info("TTS → Sarvam Bulbul v3 (advait)")
        return sarvam.TTS(
            target_language_code="en-IN",
            model="bulbul:v3",
            speaker="advait",
            pace=TTS_SPEED,
        )
    elif TTS_PROVIDER == "openai":
        logger.info("TTS → OpenAI TTS (%s / %s)", OPENAI_TTS_MODEL, OPENAI_TTS_VOICE)
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
    """
    J.A.R.V.I.S — full-desktop AI for Dushyant.
    All tools are served by the FastMCP server over SSE.
    """

    def __init__(self, stt, llm, tts) -> None:
        super().__init__(
            instructions=SYSTEM_PROMPT,
            stt=stt,
            llm=llm,
            tts=tts,
            vad=silero.VAD.load(),
            mcp_servers=[
                mcp.MCPServerHTTP(
                    url=_mcp_server_url(),
                    transport_type="sse",
                    client_session_timeout_seconds=30,
                ),
            ],
        )

    async def on_enter(self) -> None:
        """Greet Dushyant on session start."""
        await self.session.generate_reply(
            instructions=(
                f"Greet {USER_NAME} by name. "
                "If it's late at night, acknowledge it. "
                "Keep it to one sentence. Stay in character as J.A.R.V.I.S."
            )
        )


# ---------------------------------------------------------------------------
# LiveKit entry point
# ---------------------------------------------------------------------------

def _turn_detection() -> str:
    return "vad"


def _endpointing_delay() -> float:
    return 0.3


async def entrypoint(ctx: JobContext) -> None:
    print(f"\n>>> JARVIS ENTRYPOINT CALLED — room: {ctx.room.name}\n", flush=True)

    try:
        print(">>> Building STT...", flush=True)
        stt = _build_stt()
        print(">>> STT OK", flush=True)

        print(">>> Building LLM...", flush=True)
        llm = _build_llm()
        print(">>> LLM OK", flush=True)

        print(">>> Building TTS...", flush=True)
        tts = _build_tts()
        print(">>> TTS OK", flush=True)

        print(">>> Creating session...", flush=True)
        session = AgentSession(
            turn_detection=_turn_detection(),
            min_endpointing_delay=_endpointing_delay(),
        )
        print(">>> Session OK", flush=True)

        print(">>> Starting agent...", flush=True)
        await session.start(
            agent=JarvisAgent(stt=stt, llm=llm, tts=tts),
            room=ctx.room,
        )
        print(">>> Agent started successfully!", flush=True)
    except Exception as e:
        print(f"\n>>> JARVIS STARTUP FAILED: {e}\n", flush=True)
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="jarvis"))


def dev():
    """Wrapper to run the agent in dev mode automatically."""
    import sys
    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()


if __name__ == "__main__":
    main()
