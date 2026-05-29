"""
JARVIS Tool Test Suite — run manually to verify each tool works before connecting LiveKit.

Usage:
    python test_tools.py
    python test_tools.py weather
    python test_tools.py desktop
    python test_tools.py all
"""

import asyncio
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()


# ── Helpers ──────────────────────────────────────────────────────────────────

def ok(label, result):
    print(f"  [PASS] {label}")
    print(f"         {str(result)[:200]}")

def fail(label, err):
    print(f"  [FAIL] {label}: {err}")


# ── System tools ─────────────────────────────────────────────────────────────

async def test_system():
    print("\n=== SYSTEM TOOLS ===")
    try:
        import datetime
        from zoneinfo import ZoneInfo
        now = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        result = now.strftime("%A, %d %B %Y, %I:%M %p IST")
        ok("get_current_time (direct)", result)
    except Exception as e:
        fail("get_current_time", e)

    try:
        import platform
        result = {"os": platform.system(), "machine": platform.machine()}
        ok("get_system_info (direct)", result)
    except Exception as e:
        fail("get_system_info", e)


# ── Web tools ─────────────────────────────────────────────────────────────────

async def test_web():
    print("\n=== WEB TOOLS ===")

    try:
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            r = await client.get(
                "https://wttr.in/Pune?format=j1",
                headers={"User-Agent": "JARVIS-Test/1.0"},
            )
            data = r.json()
            c = data["current_condition"][0]
            result = f"{c['weatherDesc'][0]['value']}, {c['temp_C']}C"
            ok("get_weather (Pune)", result)
    except Exception as e:
        fail("get_weather", e)

    try:
        from ddgs import DDGS
        results = list(DDGS().text("what is JARVIS AI", max_results=2))
        ok("search_web", results[0].get("title", "no title") if results else "no results")
    except Exception as e:
        fail("search_web", e)

    try:
        import xml.etree.ElementTree as ET
        import httpx
        async with httpx.AsyncClient(follow_redirects=True, timeout=8) as client:
            r = await client.get(
                "https://feeds.bbci.co.uk/news/world/rss.xml",
                headers={"User-Agent": "JARVIS-Test/1.0"},
            )
            root = ET.fromstring(r.content)
            titles = [item.findtext("title") for item in root.findall(".//item")[:3]]
            ok("get_world_news (BBC RSS)", titles)
    except Exception as e:
        fail("get_world_news", e)


# ── Desktop tools ─────────────────────────────────────────────────────────────

async def test_desktop():
    print("\n=== DESKTOP TOOLS ===")

    try:
        import pyautogui
        size = pyautogui.size()
        ok("screen_size", f"{size.width}x{size.height}")
    except Exception as e:
        fail("pyautogui import / screen_size", e)

    try:
        import tempfile
        import pyautogui
        path = os.path.join(tempfile.gettempdir(), "jarvis_test_screen.png")
        pyautogui.screenshot(path)
        ok("take_screenshot", f"saved to {path}")
    except Exception as e:
        fail("take_screenshot", e)

    try:
        import subprocess
        proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
        proc.communicate(input="JARVIS test clipboard".encode("utf-8"))
        ok("copy_to_clipboard", "text copied — paste somewhere to verify")
    except Exception as e:
        fail("copy_to_clipboard", e)

    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        ok("get_active_window", buf.value or "(empty title)")
    except Exception as e:
        fail("get_active_window", e)

    try:
        import subprocess
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        procs = [line.split('","')[0].strip('"') for line in result.stdout.strip().split("\n")[:5]]
        ok("get_running_processes", procs)
    except Exception as e:
        fail("get_running_processes", e)


# ── MCP server connectivity ───────────────────────────────────────────────────

async def test_mcp_connection():
    print("\n=== MCP SERVER ===")
    import socket
    port = int(os.getenv("MCP_PORT", "8001"))
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=2)
        s.close()
        ok(f"MCP server reachable (port {port})", "TCP connection successful")
    except Exception as e:
        fail(f"MCP server not running on port {port}", e)
        print(f"         Start it first: python server.py")


# ── Runner ────────────────────────────────────────────────────────────────────

async def main():
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "all"

    print("JARVIS Tool Test Suite")
    print("=" * 40)

    if target in ("all", "system"):
        await test_system()
    if target in ("all", "web"):
        await test_web()
    if target in ("all", "desktop"):
        await test_desktop()
    if target in ("all", "mcp"):
        await test_mcp_connection()

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
