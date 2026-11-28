"""Daily scheduling, two independent ways (use either or both; the engine lock prevents double runs):

1. OS scheduler (recommended): Windows Task Scheduler runs `python -m metalscout run --trigger schedule`
   daily, with "run as soon as possible after a missed start" so a laptop that was off catches up.
   Works with the dashboard closed.
2. In-app heartbeat: while `metalscout serve` is running, a thread wakes every minute and starts the
   daily run once the configured time has passed and no run has started today.
"""
from __future__ import annotations

import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

from .engine import is_running, open_db

TASK_NAME = "MetalScout Daily"


def _at(cfg: dict) -> tuple[int, int]:
    h, m = cfg["schedule"]["daily_at"].split(":")
    return int(h), int(m)


def next_run(cfg: dict) -> datetime | None:
    if not cfg["schedule"]["enabled"]:
        return None
    h, m = _at(cfg)
    now = datetime.now()
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if ran_today(cfg):
        return t + timedelta(days=1)
    return max(t, now)  # not run yet today: at the set time, or now if that has passed


def ran_today(cfg: dict) -> bool:
    db = open_db(cfg)
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    r = db.c.execute("SELECT 1 FROM runs WHERE started>=? AND trigger IN ('schedule','manual') LIMIT 1", (start,)).fetchone()
    return bool(r)


def due(cfg: dict) -> bool:
    if not cfg["schedule"]["enabled"] or is_running(cfg) or ran_today(cfg):
        return False
    h, m = _at(cfg)
    return datetime.now() >= datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)


def spawn_run(cfg: dict, trigger: str, extra: list[str] | None = None) -> subprocess.Popen:
    flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
    return subprocess.Popen([sys.executable, "-m", "metalscout", "--config", cfg["_path"], "run", "--trigger", trigger, *(extra or [])],
                            cwd=cfg["_home"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)


def start_heartbeat(cfg: dict) -> threading.Thread:
    def loop():
        while True:
            try:
                if due(cfg):
                    spawn_run(cfg, "schedule")
            except Exception:  # noqa: S110  # the heartbeat thread must never die
                pass
            time.sleep(60)
    t = threading.Thread(target=loop, daemon=True, name="metalscout-heartbeat")
    t.start()
    return t


def windows_task_script(cfg: dict) -> str:
    h, m = _at(cfg)
    py = sys.executable
    return f"""$action  = New-ScheduledTaskAction -Execute '{py}' -Argument '-m metalscout --config "{cfg["_path"]}" run --trigger schedule' -WorkingDirectory '{cfg["_home"]}'
$trigger = New-ScheduledTaskTrigger -Daily -At {h:02d}:{m:02d}
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 5) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $action -Trigger $trigger -Settings $settings -Description 'MetalScout daily lead run' -Force
"""


def install_windows_task(cfg: dict) -> str:
    script = windows_task_script(cfg)
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], capture_output=True, text=True)  # noqa: S607  # Windows-only, fixed command
    return (r.stdout + r.stderr).strip() or "installed"


def remove_windows_task() -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-Command", f"Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false"],  # noqa: S607  # Windows-only, fixed command
                       capture_output=True, text=True)
    return (r.stdout + r.stderr).strip() or "removed"


def cron_line(cfg: dict) -> str:
    h, m = _at(cfg)
    q = shlex.quote
    return f"{m} {h} * * * cd {q(cfg['_home'])} && {q(sys.executable)} -m metalscout run --trigger schedule >> logs/cron.log 2>&1"
