"""
J.A.R.V.I.S — Wake Launcher
=============================
Run this instead of 'uv run friday_voice' for hands-free activation.

Pipeline:
  1. Listens continuously for 2 claps within 1.5 seconds
  2. After claps, listens for the spoken word "JARVIS" (5 s window)
  3. On detection → starts the LiveKit voice agent session

Usage:
  uv run jarvis_wake

Install required deps first:
  uv add sounddevice numpy SpeechRecognition
"""

import logging
import subprocess
import sys
import time
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("jarvis.wake")


def _print_banner():
    print("""
╔══════════════════════════════════════════════════════╗
║          J.A.R.V.I.S  —  Wake Mode Active           ║
║                                                      ║
║   Clap twice  →  Say "JARVIS"  →  I'm online        ║
╚══════════════════════════════════════════════════════╝
""")


# Track agent process so we don't spawn duplicates
_agent_process: subprocess.Popen | None = None
_agent_lock = threading.Lock()


def _is_agent_running() -> bool:
    global _agent_process
    with _agent_lock:
        if _agent_process is None:
            return False
        poll = _agent_process.poll()
        if poll is not None:
            _agent_process = None
            return False
        return True


def _start_agent():
    global _agent_process
    with _agent_lock:
        if _agent_process and _agent_process.poll() is None:
            logger.info("Agent already running — ignoring wake trigger")
            return

        logger.info("🚀 Launching J.A.R.V.I.S voice agent...")
        print("\n[JARVIS] Waking up... standing by.\n")

        try:
            # Run agent_friday.py directly with 'dev' arg for LiveKit
            _agent_process = subprocess.Popen(
                [sys.executable, "agent_friday.py", "dev"],
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except Exception as e:
            logger.error("Failed to start agent: %s", e)


def main():
    _print_banner()

    try:
        from friday.wake import WakeDetector
    except ImportError as e:
        logger.error("Import failed: %s", e)
        logger.error("Make sure you ran: uv sync")
        sys.exit(1)

    detector = WakeDetector(on_wake=_start_agent)

    try:
        detector.start()
        logger.info("Wake detector running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            # Optionally poll agent health here
    except KeyboardInterrupt:
        logger.info("Shutting down wake detector...")
        detector.stop()
        if _agent_process and _agent_process.poll() is None:
            logger.info("Stopping agent process...")
            _agent_process.terminate()
    except Exception as e:
        logger.error("Wake detector crashed: %s", e)
        detector.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
