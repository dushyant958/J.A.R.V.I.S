"""
J.A.R.V.I.S — Windows Task Scheduler Setup
============================================
Registers JARVIS to auto-start on login using Windows Task Scheduler.
Run once as a normal user (no admin needed for current-user tasks):

    python setup_autostart.py install    # register auto-start
    python setup_autostart.py remove     # remove auto-start
    python setup_autostart.py status     # check if registered
"""

import os
import subprocess
import sys

TASK_NAME = "JARVIS_Autostart"
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
PYTHON    = os.path.join(BASE_DIR, "venv", "Scripts", "pythonw.exe")  # pythonw = no console window
LAUNCHER  = os.path.join(BASE_DIR, "launcher.py")


def install():
    """Register JARVIS in Task Scheduler to run at login (no console window)."""
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON}</Command>
      <Arguments>"{LAUNCHER}"</Arguments>
      <WorkingDirectory>{BASE_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    xml_path = os.path.join(BASE_DIR, "_task.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(xml)

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", xml_path, "/F"],
        capture_output=True, text=True
    )
    os.remove(xml_path)

    if result.returncode == 0:
        print(f"JARVIS auto-start registered as Task: {TASK_NAME}")
        print("JARVIS will start automatically on next login.")
        print(f"Logs will be written to: {BASE_DIR}\\jarvis.log")
    else:
        print(f"Failed to register task: {result.stderr}")
        sys.exit(1)


def remove():
    """Remove JARVIS from Task Scheduler."""
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"Task '{TASK_NAME}' removed. JARVIS will no longer auto-start.")
    else:
        print(f"Could not remove task (maybe it wasn't registered): {result.stderr}")


def status():
    """Check if JARVIS task is registered."""
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Task '{TASK_NAME}' is NOT registered.")


def start_now():
    """Trigger the task immediately without waiting for login."""
    result = subprocess.run(
        ["schtasks", "/Run", "/TN", TASK_NAME],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("JARVIS started via Task Scheduler.")
    else:
        print(f"Failed to start: {result.stderr}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "install"
    {
        "install": install,
        "remove":  remove,
        "status":  status,
        "start":   start_now,
    }.get(cmd, lambda: print(f"Unknown command: {cmd}. Use: install | remove | status | start"))()
