"""
Desktop control tools — full PC control via voice.
Lets JARVIS open apps, type text, click, take screenshots, manage windows.
"""

import asyncio
import os
import platform
import subprocess
import time


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run_sync(fn, *args, **kwargs):
    """Run a blocking call (pyautogui etc.) in a thread so we don't block the event loop."""
    return asyncio.get_running_loop().run_in_executor(None, lambda: fn(*args, **kwargs))


def _get_pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
        pyautogui.PAUSE = 0.05
        return pyautogui
    except ImportError:
        raise RuntimeError("pyautogui not installed — run: uv add pyautogui")


# ── Windows app name → executable mapping ────────────────────────────────────
APP_MAP = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpnt",
    "spotify": "spotify",
    "discord": "discord",
    "vs code": "code",
    "visual studio code": "code",
    "task manager": "taskmgr",
    "control panel": "control",
    "settings": "ms-settings:",
    "terminal": "wt",
    "windows terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    "paint": "mspaint",
    "vlc": "vlc",
    "zoom": "zoom",
    "teams": "teams",
    "microsoft teams": "teams",
    "slack": "slack",
    "whatsapp": "WhatsApp",
}


def register(mcp):

    # ── Application Control ───────────────────────────────────────────────────

    @mcp.tool()
    async def open_application(app_name: str) -> str:
        """
        Open any application by name on the PC.
        Examples: 'Google Chrome', 'Spotify', 'Notepad', 'VS Code', 'Calculator'.
        """
        name_lower = app_name.lower().strip()
        executable = APP_MAP.get(name_lower, name_lower)

        try:
            if platform.system() == "Windows":
                if executable.startswith("ms-"):
                    subprocess.Popen(["start", "", executable], shell=True)
                else:
                    subprocess.Popen(
                        executable, shell=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
            else:
                subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {app_name}."
        except Exception as e:
            return f"Could not open {app_name}: {e}"

    @mcp.tool()
    async def close_application(app_name: str) -> str:
        """
        Close / kill a running application by name.
        Example: close Chrome, close Notepad.
        """
        name_lower = app_name.lower().strip()
        executable = APP_MAP.get(name_lower, name_lower)
        # Strip .exe if already there, then re-add
        exe_name = executable.replace(".exe", "") + ".exe"
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", exe_name],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    return f"Closed {app_name}."
                return f"Could not close {app_name} — is it running?"
            else:
                subprocess.run(["pkill", "-f", executable])
                return f"Closed {app_name}."
        except Exception as e:
            return f"Error closing {app_name}: {e}"

    @mcp.tool()
    async def get_running_processes() -> str:
        """
        List currently running applications/processes on the PC.
        Use when the user asks what's running or open.
        """
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True
                )
                lines = result.stdout.strip().split("\n")[:20]
                processes = []
                for line in lines:
                    parts = line.strip('"').split('","')
                    if parts:
                        processes.append(parts[0])
                return "Running processes: " + ", ".join(processes[:20])
            else:
                result = subprocess.run(["ps", "-e", "-o", "comm="], capture_output=True, text=True)
                procs = list(set(result.stdout.strip().split("\n")))[:20]
                return "Running: " + ", ".join(procs)
        except Exception as e:
            return f"Could not list processes: {e}"

    # ── Keyboard & Typing ─────────────────────────────────────────────────────

    @mcp.tool()
    async def type_text(text: str, interval: float = 0.03) -> str:
        """
        Type text as if from a keyboard at the current cursor position.
        Use after clicking on a text field/search bar.
        Interval controls typing speed in seconds between keystrokes.
        """
        try:
            pag = _get_pyautogui()
            # Use write() for Unicode support; typewrite() only handles ASCII
            await asyncio.to_thread(pag.write, text, interval=interval)
            return f"Typed: {text}"
        except Exception as e:
            return f"Could not type text: {e}"

    @mcp.tool()
    async def press_key(key: str) -> str:
        """
        Press a keyboard key or key combination.
        Examples: 'enter', 'escape', 'ctrl+c', 'ctrl+v', 'alt+tab', 'win', 'f5', 'backspace'.
        Use '+' to combine keys, e.g. 'ctrl+shift+t' to reopen a tab.
        """
        try:
            pag = _get_pyautogui()
            keys = [k.strip() for k in key.lower().split("+")]
            if len(keys) == 1:
                await asyncio.to_thread(pag.press, keys[0])
            else:
                await asyncio.to_thread(pag.hotkey, *keys)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Could not press key {key}: {e}"

    @mcp.tool()
    async def copy_to_clipboard(text: str) -> str:
        """Copy text to the system clipboard."""
        try:
            proc = subprocess.Popen(
                ["clip"], stdin=subprocess.PIPE
            )
            proc.communicate(input=text.encode("utf-8"))
            return "Copied to clipboard."
        except Exception as e:
            return f"Could not copy to clipboard: {e}"

    # ── Mouse Control ─────────────────────────────────────────────────────────

    @mcp.tool()
    async def click_at(x: int, y: int, button: str = "left") -> str:
        """
        Click the mouse at screen coordinates (x, y).
        button can be 'left', 'right', or 'middle'.
        Get coordinates from take_screenshot first to identify where to click.
        """
        try:
            pag = _get_pyautogui()
            await asyncio.to_thread(pag.click, x, y, button=button)
            return f"Clicked {button} at ({x}, {y})."
        except Exception as e:
            return f"Could not click at ({x}, {y}): {e}"

    @mcp.tool()
    async def double_click_at(x: int, y: int) -> str:
        """Double-click at screen coordinates (x, y)."""
        try:
            pag = _get_pyautogui()
            await asyncio.to_thread(pag.doubleClick, x, y)
            return f"Double-clicked at ({x}, {y})."
        except Exception as e:
            return f"Could not double-click: {e}"

    @mcp.tool()
    async def scroll(direction: str, amount: int = 3) -> str:
        """
        Scroll the mouse wheel up or down.
        direction: 'up' or 'down'. amount: number of scroll clicks (1-10).
        """
        try:
            pag = _get_pyautogui()
            clicks = amount if direction.lower() == "up" else -amount
            await asyncio.to_thread(pag.scroll, clicks)
            return f"Scrolled {direction} by {amount}."
        except Exception as e:
            return f"Could not scroll: {e}"

    @mcp.tool()
    async def move_mouse(x: int, y: int) -> str:
        """Move the mouse cursor to (x, y) without clicking."""
        try:
            pag = _get_pyautogui()
            await asyncio.to_thread(pag.moveTo, x, y, duration=0.2)
            return f"Moved mouse to ({x}, {y})."
        except Exception as e:
            return f"Could not move mouse: {e}"

    # ── Screen / Vision ───────────────────────────────────────────────────────

    @mcp.tool()
    async def take_screenshot(region: str = "full") -> str:
        """
        Take a screenshot of the entire screen and save it to a temp file.
        Returns the file path so JARVIS can reference what's on screen.
        region: 'full' for the whole screen.
        Use this to see what's currently on the screen before clicking.
        """
        try:
            pag = _get_pyautogui()
            import tempfile, os
            path = os.path.join(tempfile.gettempdir(), "jarvis_screen.png")
            await asyncio.to_thread(lambda: pag.screenshot(path))
            size = pag.size()
            return f"Screenshot saved to {path}. Screen size: {size.width}x{size.height}."
        except Exception as e:
            return f"Could not take screenshot: {e}"

    @mcp.tool()
    async def get_screen_size() -> str:
        """Get the current screen resolution/size."""
        try:
            pag = _get_pyautogui()
            size = pag.size()
            return f"Screen size: {size.width}x{size.height} pixels."
        except Exception as e:
            return f"Could not get screen size: {e}"

    # ── Window Management ─────────────────────────────────────────────────────

    @mcp.tool()
    async def get_active_window() -> str:
        """Get the title of the currently focused/active window."""
        try:
            pag = _get_pyautogui()
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                return f"Active window: '{win.title}'"
            return "No active window detected."
        except ImportError:
            # Fallback using Windows API
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return f"Active window: '{buf.value}'"
            except Exception as e:
                return f"Could not get active window: {e}"
        except Exception as e:
            return f"Could not get active window: {e}"

    @mcp.tool()
    async def list_open_windows() -> str:
        """List all currently open windows on the desktop."""
        try:
            import pygetwindow as gw
            windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
            return "Open windows: " + ", ".join(windows[:20]) if windows else "No windows found."
        except ImportError:
            return "Install pygetwindow for window listing: uv add pygetwindow"
        except Exception as e:
            return f"Could not list windows: {e}"

    @mcp.tool()
    async def focus_window(window_title: str) -> str:
        """
        Bring a window to focus by its title (partial match is fine).
        Example: 'Chrome', 'Notepad', 'Spotify'.
        """
        try:
            import pygetwindow as gw
            matches = [w for w in gw.getAllWindows()
                       if window_title.lower() in w.title.lower() and w.title.strip()]
            if not matches:
                return f"No window found matching '{window_title}'."
            win = matches[0]
            await asyncio.to_thread(win.activate)
            return f"Focused window: '{win.title}'."
        except ImportError:
            # Fallback: use Alt+Tab heuristic or open app
            return "pygetwindow not installed — run: uv add pygetwindow"
        except Exception as e:
            return f"Could not focus window: {e}"

    @mcp.tool()
    async def minimize_window(window_title: str = "") -> str:
        """Minimize the active window or a window by title."""
        try:
            import pygetwindow as gw
            if not window_title:
                win = gw.getActiveWindow()
                if win:
                    await asyncio.to_thread(win.minimize)
                    return f"Minimized '{win.title}'."
                return "No active window to minimize."
            else:
                matches = [w for w in gw.getAllWindows()
                           if window_title.lower() in w.title.lower()]
                if matches:
                    await asyncio.to_thread(matches[0].minimize)
                    return f"Minimized {window_title}."
                return f"No window found matching '{window_title}'."
        except Exception as e:
            return f"Could not minimize: {e}"

    # ── System Actions ────────────────────────────────────────────────────────

    @mcp.tool()
    async def run_shell_command(command: str) -> str:
        """
        Run a shell command and return its output.
        Use for tasks like creating files, running scripts, checking system info.
        CAUTION: Only run safe, user-requested commands.
        """
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            output = result.stdout or result.stderr or "(no output)"
            return output[:2000]
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Command failed: {e}"

    @mcp.tool()
    async def set_volume(level: int) -> str:
        """
        Set the system volume level (0-100).
        Example: set_volume(50) for 50% volume.
        """
        try:
            if platform.system() == "Windows":
                ps_cmd = f"""
                Add-Type -TypeDefinition @'
                using System.Runtime.InteropServices;
                [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                interface IAudioEndpointVolume {{
                    int f(); int g(); int h(); int i();
                    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
                    int j();
                    int GetMasterVolumeLevelScalar(out float pfLevel);
                }}
                [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                interface IMMDevice {{ int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev); }}
                [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                interface IMMDeviceEnumerator {{ int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint); }}
                [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject {{ }}
'@
                $enumerator = [MMDeviceEnumeratorComObject] -as [IMMDeviceEnumerator]
                $device = $null; [void]$enumerator.GetDefaultAudioEndpoint(0, 1, [ref]$device)
                $id = [System.Guid]::new("5CDF2C82-841E-4546-9722-0CF74078229A")
                $aev = $null; [void]$device.Activate([ref]$id, 23, 0, [ref]$aev)
                [void]$aev.SetMasterVolumeLevelScalar({level / 100.0}, [System.Guid]::Empty)
                """
                await asyncio.to_thread(
                    subprocess.run, ["powershell", "-Command", ps_cmd],
                    capture_output=True, timeout=5
                )
            return f"Volume set to {level}%."
        except Exception as e:
            return f"Could not set volume: {e}"

    @mcp.tool()
    async def lock_screen() -> str:
        """Lock the computer screen."""
        try:
            if platform.system() == "Windows":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Screen locked."
        except Exception as e:
            return f"Could not lock screen: {e}"

    @mcp.tool()
    async def open_url_in_browser(url: str, browser: str = "default") -> str:
        """
        Open a URL directly in a specific browser.
        browser: 'default', 'chrome', 'firefox', 'edge'.
        Use this to navigate to websites, open Google, Gmail, YouTube, etc.
        """
        import webbrowser
        try:
            if browser == "default" or browser not in ("chrome", "firefox", "edge"):
                webbrowser.open(url)
            else:
                # webbrowser.get("chrome") doesn't work on Windows — launch directly
                exe_map = {"chrome": "chrome", "firefox": "firefox", "edge": "msedge"}
                subprocess.Popen([exe_map[browser], url], shell=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opened {url} in {browser} browser."
        except Exception as e:
            return f"Could not open URL: {e}"
