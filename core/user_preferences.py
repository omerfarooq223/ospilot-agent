from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATA_DIR, ensure_data_dirs


IGNORE_LIST_PATH = DATA_DIR / "ignored_folders.json"
SCAN_HISTORY_PATH = DATA_DIR / "scan_history.json"


def _read_json(path: Path, fallback: Any) -> Any:
    ensure_data_dirs()
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def _write_json(path: Path, data: Any) -> None:
    ensure_data_dirs()
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def list_ignored_folders() -> list[str]:
    values = _read_json(IGNORE_LIST_PATH, [])
    if not isinstance(values, list):
        return []
    return [str(item) for item in values]


def add_ignored_folder(path: str) -> list[str]:
    folders = list_ignored_folders()
    if path not in folders:
        folders.append(path)
        folders.sort(key=str.lower)
        _write_json(IGNORE_LIST_PATH, folders)
    return folders


def remove_ignored_folder(path: str) -> list[str]:
    folders = [item for item in list_ignored_folders() if item != path]
    _write_json(IGNORE_LIST_PATH, folders)
    return folders


def is_ignored(path: str | Path) -> bool:
    target = str(path)
    return any(target == ignored or target.startswith(ignored + "/") for ignored in list_ignored_folders())


def append_scan_history(entry: dict[str, Any]) -> list[dict[str, Any]]:
    history = scan_history(limit=200)
    history.insert(0, {"timestamp": datetime.now(timezone.utc).isoformat(), **entry})
    history = history[:200]
    _write_json(SCAN_HISTORY_PATH, history)
    return history


def scan_history(limit: int = 30) -> list[dict[str, Any]]:
    values = _read_json(SCAN_HISTORY_PATH, [])
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)][:limit]
