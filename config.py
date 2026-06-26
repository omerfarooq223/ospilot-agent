from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until requirements are installed
    def load_dotenv() -> bool:
        return False


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("OSPILOT_DATA_DIR", BASE_DIR / ".ospilot_data")).expanduser()
QUARANTINE_DIR = DATA_DIR / "quarantine"
REPORTS_DIR = DATA_DIR / "reports"
SCHEDULER_CONFIG_PATH = DATA_DIR / "scheduler.json"
WEEKLY_SCAN_SCRIPT = BASE_DIR / "scripts" / "weekly_scan.py"
LAUNCH_AGENT_LABEL = "com.ospilot.weekly-scan"
DB_PATH = DATA_DIR / "ospilot.sqlite3"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def fallback_mode_enabled() -> bool:
    return not bool(GROQ_API_KEY)
