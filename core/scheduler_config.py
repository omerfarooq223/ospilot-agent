from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from config import SCHEDULER_CONFIG_PATH, ensure_data_dirs


WEEKDAYS = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]


class SchedulerConfig(BaseModel):
    enabled: bool = False
    folders: list[str] = Field(default_factory=list)
    weekday: int = Field(default=0, ge=0, le=6)
    hour: int = Field(default=9, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    min_size_mb: int = Field(default=30, ge=30, le=5000)
    python_executable: str = Field(default_factory=lambda: sys.executable)
    installed_at: datetime | None = None
    scheduler_backend: str = "none"


def load_scheduler_config(path: Path = SCHEDULER_CONFIG_PATH) -> SchedulerConfig:
    ensure_data_dirs()
    if not path.exists():
        return SchedulerConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return SchedulerConfig.model_validate(data)


def save_scheduler_config(config: SchedulerConfig, path: Path = SCHEDULER_CONFIG_PATH) -> SchedulerConfig:
    ensure_data_dirs()
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
    return config


def weekday_label(weekday: int) -> str:
    return WEEKDAYS[weekday % 7]
