"""Desktop control tools."""

import asyncio
import os
import platform
import subprocess
import time


def _run_sync(fn, *args, **kwargs):
    return asyncio.get_running_loop().run_in_executor(None, lambda: fn(*args, **kwargs))


def _get_pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        return pyautogui
    except ImportError:
        raise RuntimeError("pyautogui not installed — run: uv add pyautogui")


_EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

APP_MAP = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": _EDGE_PATH,
    "microsoft edge": _EDGE_PATH,
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

    @mcp.tool()
    async def open_application(app_name: str) -> str:
        """Open an application by name, e.g. 'Chrome', 'Spotify', 'Notepad'."""
        name_lower = app_name.lower().strip()
        executable = APP_MAP.get(name_lower, name_lower)
        try:
            if platform.system() == "Windows":
                if executable.startswith("ms-"):
                    subprocess.Popen(["start", "", executable], shell=True)
                elif os.path.isfile(executable):
                    subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    result = subprocess.run(
                        executable, shell=True,
                        capture_output=True, text=True, timeout=3
                    )
                    if result.returncode != 0 and result.stderr:
                        return f"Could not open {app_name}: {result.stderr.strip()}"
            else:
                subprocess.Popen([executable], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {app_name}."
        except subprocess.TimeoutExpired:
            return f"Opening {app_name}."
        except Exception as e:
            return f"Could not open {app_name}: {e}"

    @mcp.tool()
    async def close_application(app_name: str) -> str:
        """Close a running application by name."""
        name_lower = app_name.lower().strip()
        executable = APP_MAP.get(name_lower, name_lower)
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
        """List currently running processes on the PC."""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True
                )
                lines = result.stdout.strip().split("\n")[:20]
                processes = [line.strip('"').split('","')[0] for line in lines if line]
                return "Running: " + ", ".join(processes[:20])
            else:
                result = subprocess.run(["ps", "-e", "-o", "comm="], capture_output=True, text=True)
                procs = list(set(result.stdout.strip().split("\n")))[:20]
                return "Running: " + ", ".join(procs)
        except Exception as e:
            return f"Could not list processes: {e}"

    @mcp.tool()
    async def type_text(text: str, interval: float = 0.03) -> str:
        """Type text at the current cursor position (supports Unicode)."""
        try:
            proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode("utf-8"))
            pag = _get_pyautogui()
            await asyncio.to_thread(pag.hotkey, "ctrl", "v")
            return f"Typed: {text}"
        except Exception as e:
            return f"Could not type text: {e}"

    @mcp.tool()
    async def press_key(key: str) -> str:
        """Press a key or combo, e.g. 'enter', 'ctrl+c', 'alt+tab', 'win'."""
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
            proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode("utf-8"))
            return "Copied to clipboard."
        except Exception as e:
            return f"Could not copy to clipboard: {e}"

    @mcp.tool()
    async def click_at(x: int, y: int, button: str = "left") -> str:
        """Click at screen coordinates (x, y). button: 'left', 'right', 'middle'."""
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
        """Scroll mouse wheel. direction: 'up' or 'down', amount: 1-10."""
        try:
            pag = _get_pyautogui()
            clicks = amount if direction.lower() == "up" else -amount
            await asyncio.to_thread(pag.scroll, clicks)
            return f"Scrolled {direction} by {amount}."
        except Exception as e:
            return f"Could not scroll: {e}"

    @mcp.tool()
    async def move_mouse(x: int, y: int) -> str:
        """Move mouse cursor to (x, y) without clicking."""
        try:
            pag = _get_pyautogui()
            await asyncio.to_thread(pag.moveTo, x, y, duration=0.2)
            return f"Moved mouse to ({x}, {y})."
        except Exception as e:
            return f"Could not move mouse: {e}"

    @mcp.tool()
    async def take_screenshot() -> str:
        """Take a screenshot and save to temp file. Returns the file path."""
        try:
            pag = _get_pyautogui()
            import tempfile
            path = os.path.join(tempfile.gettempdir(), "jarvis_screen.png")
            await asyncio.to_thread(lambda: pag.screenshot(path))
            size = pag.size()
            return f"Screenshot saved to {path}. Screen: {size.width}x{size.height}."
        except Exception as e:
            return f"Could not take screenshot: {e}"

    @mcp.tool()
    async def get_screen_size() -> str:
        """Get the current screen resolution."""
        try:
            pag = _get_pyautogui()
            size = pag.size()
            return f"Screen: {size.width}x{size.height}."
        except Exception as e:
            return f"Could not get screen size: {e}"

    @mcp.tool()
    async def get_active_window() -> str:
        """Get the title of the currently focused window."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return f"Active window: '{win.title}'" if win else "No active window."
        except ImportError:
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
        """List all open windows on the desktop."""
        try:
            import pygetwindow as gw
            windows = [w.title for w in gw.getAllWindows() if w.title.strip()]
            return "Open windows: " + ", ".join(windows[:20]) if windows else "No windows found."
        except ImportError:
            return "Install pygetwindow: uv add pygetwindow"
        except Exception as e:
            return f"Could not list windows: {e}"

    @mcp.tool()
    async def focus_window(window_title: str) -> str:
        """Bring a window to focus by partial title match."""
        try:
            import pygetwindow as gw
            matches = [w for w in gw.getAllWindows()
                       if window_title.lower() in w.title.lower() and w.title.strip()]
            if not matches:
                return f"No window matching '{window_title}'."
            await asyncio.to_thread(matches[0].activate)
            return f"Focused: '{matches[0].title}'."
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
                return "No active window."
            else:
                matches = [w for w in gw.getAllWindows()
                           if window_title.lower() in w.title.lower()]
                if matches:
                    await asyncio.to_thread(matches[0].minimize)
                    return f"Minimized {window_title}."
                return f"No window matching '{window_title}'."
        except Exception as e:
            return f"Could not minimize: {e}"

    @mcp.tool()
    async def run_shell_command(command: str) -> str:
        """Run a shell command and return its output."""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            return (result.stdout or result.stderr or "(no output)")[:2000]
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds."
        except Exception as e:
            return f"Command failed: {e}"

    @mcp.tool()
    async def set_volume(level: int) -> str:
        """Set system volume 0-100."""
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
        """Open a URL in a browser. browser: 'default', 'chrome', 'firefox', 'edge'."""
        import webbrowser
        try:
            if browser == "default" or browser not in ("chrome", "firefox", "edge"):
                webbrowser.open(url)
            else:
                exe_map = {"chrome": "chrome", "firefox": "firefox", "edge": _EDGE_PATH}
                subprocess.Popen([exe_map[browser], url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opened {url} in {browser}."
        except Exception as e:
            return f"Could not open URL: {e}"
