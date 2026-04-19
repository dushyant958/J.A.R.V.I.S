"""
System tools — time, environment info, shell commands, etc.
"""

import datetime
import platform
import os


def register(mcp):

    @mcp.tool()
    def get_current_time() -> str:
        """Return the current date and time with timezone (IST)."""
        tz_name = os.getenv("JARVIS_USER_TIMEZONE", "Asia/Kolkata")
        try:
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now(ZoneInfo(tz_name))
        except Exception:
            now = datetime.datetime.now()
        return now.strftime("%A, %d %B %Y, %I:%M %p %Z")

    @mcp.tool()
    def get_system_info() -> str:
        """Return basic information about the host system."""
        return (
            f"{platform.system()} {platform.machine()}, "
            f"Python {platform.python_version()}"
        )
