from __future__ import annotations

import platform
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from config import DATA_DIR, LAUNCH_AGENT_LABEL, WEEKLY_SCAN_SCRIPT, ensure_data_dirs
from core.scheduler_config import SchedulerConfig, load_scheduler_config, save_scheduler_config, weekday_label


CRON_MARKER = "# ospilot-weekly-scan"


def scheduler_platform() -> str:
    if sys.platform == "darwin":
        return "launchd"
    if sys.platform.startswith("linux"):
        return "cron"
    return "unsupported"


def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"


def _logs_dir() -> Path:
    path = DATA_DIR / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _build_launchd_plist(config: SchedulerConfig) -> str:
    python_executable = config.python_executable or sys.executable
    script_path = str(WEEKLY_SCAN_SCRIPT.resolve())
    stdout_path = _logs_dir() / "weekly-scan.out.log"
    stderr_path = _logs_dir() / "weekly-scan.err.log"
    launchd_weekday = config.weekday
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{escape(LAUNCH_AGENT_LABEL)}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{escape(python_executable)}</string>
    <string>{escape(script_path)}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>{launchd_weekday}</integer>
    <key>Hour</key>
    <integer>{config.hour}</integer>
    <key>Minute</key>
    <integer>{config.minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{escape(str(stdout_path))}</string>
  <key>StandardErrorPath</key>
  <string>{escape(str(stderr_path))}</string>
  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
"""


def _run_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=check)


def is_launchd_installed() -> bool:
    plist_path = launch_agent_path()
    if not plist_path.exists():
        return False
    result = _run_command(["launchctl", "list"], check=False)
    return LAUNCH_AGENT_LABEL in result.stdout


def install_launchd(config: SchedulerConfig) -> None:
    plist_path = launch_agent_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    if plist_path.exists():
        _run_command(["launchctl", "unload", str(plist_path)], check=False)
    plist_path.write_text(_build_launchd_plist(config), encoding="utf-8")
    _run_command(["launchctl", "load", str(plist_path)])


def uninstall_launchd() -> None:
    plist_path = launch_agent_path()
    if plist_path.exists():
        _run_command(["launchctl", "unload", str(plist_path)], check=False)
        plist_path.unlink(missing_ok=True)


def _read_crontab() -> str:
    result = _run_command(["crontab", "-l"], check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def _write_crontab(content: str) -> None:
    proc = subprocess.run(["crontab", "-"], input=content, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "Failed to update crontab.")


def is_cron_installed() -> bool:
    return CRON_MARKER in _read_crontab()


def install_cron(config: SchedulerConfig) -> None:
    python_executable = config.python_executable or sys.executable
    script_path = str(WEEKLY_SCAN_SCRIPT.resolve())
    cron_line = (
        f"{config.minute} {config.hour} * * {config.weekday} "
        f"{shlex.quote(python_executable)} {shlex.quote(script_path)} {CRON_MARKER}"
    )
    existing = _read_crontab()
    lines = [line for line in existing.splitlines() if CRON_MARKER not in line]
    lines.append(cron_line)
    _write_crontab("\n".join(lines).strip() + "\n")


def uninstall_cron() -> None:
    existing = _read_crontab()
    lines = [line for line in existing.splitlines() if CRON_MARKER not in line]
    _write_crontab("\n".join(lines).strip() + ("\n" if lines else ""))


def is_scheduler_installed() -> bool:
    backend = scheduler_platform()
    if backend == "launchd":
        return is_launchd_installed()
    if backend == "cron":
        return is_cron_installed()
    return False


def install_scheduler(config: SchedulerConfig) -> SchedulerConfig:
    ensure_data_dirs()
    backend = scheduler_platform()
    if backend == "unsupported":
        raise RuntimeError(f"Weekly scheduling is not supported on {platform.system()} yet.")
    config.enabled = True
    config.python_executable = config.python_executable or sys.executable
    config.scheduler_backend = backend
    config.installed_at = datetime.now(timezone.utc)
    save_scheduler_config(config)
    if backend == "launchd":
        install_launchd(config)
    else:
        install_cron(config)
    return config


def uninstall_scheduler() -> SchedulerConfig:
    config = load_scheduler_config()
    backend = config.scheduler_backend or scheduler_platform()
    if backend == "launchd":
        uninstall_launchd()
    elif backend == "cron":
        uninstall_cron()
    config.enabled = False
    config.scheduler_backend = "none"
    save_scheduler_config(config)
    return config


def scheduler_status() -> dict[str, object]:
    config = load_scheduler_config()
    backend = scheduler_platform()
    installed = is_scheduler_installed()
    return {
        "enabled": config.enabled,
        "installed": installed,
        "platform": backend,
        "supported": backend != "unsupported",
        "folders": config.folders,
        "weekday": config.weekday,
        "weekday_label": weekday_label(config.weekday),
        "hour": config.hour,
        "minute": config.minute,
        "min_size_mb": config.min_size_mb,
        "installed_at": config.installed_at.isoformat() if config.installed_at else None,
        "schedule_label": f"{weekday_label(config.weekday)} at {config.hour:02d}:{config.minute:02d}",
    }
