from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    NEEDS_REVIEW = "Needs Review"
    BLOCKED = "Blocked"


class RebuildabilityLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NOT_REBUILDABLE = "Not Rebuildable"
    UNKNOWN = "Unknown"


class ActionMode(str, Enum):
    ADVISORY = "Advisory"
    QUARANTINE = "Quarantine"
    BLOCKED = "Blocked"


class SystemMetrics(BaseModel):
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    available_disk_bytes: int
    total_disk_bytes: int
    timestamp: datetime = Field(default_factory=utc_now)


class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    status: str = "unknown"
    command_preview: str = ""


class ScanItem(BaseModel):
    path: str
    item_type: str
    size_bytes: int
    risk_level: RiskLevel
    reason: str
    recommended_action: str
    project_root: str | None = None
    project_type: str = "Unknown"
    rebuildability: RebuildabilityLevel = RebuildabilityLevel.UNKNOWN
    recovery_recipe: str = "Review manually before removing."
    evidence: list[str] = Field(default_factory=list)


class MaintenanceAction(BaseModel):
    action_id: str
    action_mode: ActionMode
    path: str | None = None
    reason: str
    size_bytes: int = 0
    risk_level: RiskLevel
    approved: bool = False
    project_root: str | None = None
    project_type: str = "Unknown"
    rebuildability: RebuildabilityLevel = RebuildabilityLevel.UNKNOWN
    recovery_recipe: str = "Review manually before removing."
    evidence: list[str] = Field(default_factory=list)
    last_opened_at: datetime | None = None
    days_since_opened: int | None = None
    priority_score: int = 0
    priority_reason: str = ""
    automation_eligible: bool = False
    automation_reason: str = ""
    inbox_bucket: str = "review"


class MaintenancePlan(BaseModel):
    diagnosis_summary: str
    performance_recommendations: list[MaintenanceAction] = Field(default_factory=list)
    cleanup_actions: list[MaintenanceAction] = Field(default_factory=list)
    blocked_actions: list[MaintenanceAction] = Field(default_factory=list)
    estimated_recoverable_bytes: int = 0


class QuarantineRecord(BaseModel):
    id: int
    original_path: str
    quarantine_path: str
    size_bytes: int
    reason: str
    timestamp: datetime
    restored: bool = False
    permanently_deleted: bool = False


class AuditEvent(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class Observation(BaseModel):
    metrics: SystemMetrics
    top_memory_processes: list[ProcessInfo] = Field(default_factory=list)
    top_cpu_processes: list[ProcessInfo] = Field(default_factory=list)
    pressure_summary: dict[str, Any] = Field(default_factory=dict)
    idle_heavy_apps: list[ProcessInfo] = Field(default_factory=list)
    scan_items: list[ScanItem] = Field(default_factory=list)
