"""
J.A.R.V.I.S — Process Launcher
================================
Starts both the MCP server and voice agent as background processes.
Keeps them alive — if either crashes, restarts it automatically.

Run directly:   python launcher.py
As a service:   registered via Task Scheduler (see setup_autostart.py)
Stop:           Ctrl+C  OR  kill the launcher PID
"""

import logging
import os
import subprocess
import sys
import time
import signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LAUNCHER] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "jarvis.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("launcher")

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
PYTHON    = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
RESTART_DELAY = 5   # seconds before restarting a crashed process

PROCESSES = {
    "mcp_server":   [PYTHON, "server.py"],
    "voice_agent":  [PYTHON, "agent_friday.py", "dev"],
}

_procs: dict[str, subprocess.Popen] = {}
_running = True


def _start(name: str) -> subprocess.Popen:
    cmd = PROCESSES[name]
    log_path = os.path.join(BASE_DIR, f"{name}.log")
    log_file = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=log_file,
        stderr=log_file,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    logger.info("Started %s (PID %d) → log: %s", name, proc.pid, log_path)
    return proc


def _stop_all():
    global _running
    _running = False
    logger.info("Shutting down JARVIS processes...")
    for name, proc in _procs.items():
        if proc and proc.poll() is None:
            proc.terminate()
            logger.info("Terminated %s (PID %d)", name, proc.pid)
    time.sleep(2)
    for name, proc in _procs.items():
        if proc and proc.poll() is None:
            proc.kill()
            logger.info("Killed %s (PID %d)", name, proc.pid)


def _handle_signal(sig, frame):
    logger.info("Signal %d received — shutting down", sig)
    _stop_all()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("=" * 50)
    logger.info("J.A.R.V.I.S Launcher starting")
    logger.info("Base dir: %s", BASE_DIR)
    logger.info("=" * 50)

    # Start MCP server first, give it 3s to bind the port
    _procs["mcp_server"] = _start("mcp_server")
    logger.info("Waiting 3s for MCP server to bind port 8000...")
    time.sleep(3)

    # Start voice agent
    _procs["voice_agent"] = _start("voice_agent")

    # Watch loop — restart crashed processes
    while _running:
        for name, proc in list(_procs.items()):
            ret = proc.poll()
            if ret is not None:
                logger.warning("%s exited with code %d — restarting in %ds", name, ret, RESTART_DELAY)
                time.sleep(RESTART_DELAY)
                if _running:
                    _procs[name] = _start(name)
        time.sleep(2)


if __name__ == "__main__":
    main()
