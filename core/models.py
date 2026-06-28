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


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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


class DiagnosisResult(BaseModel):
    """Structured output from the Diagnosis Agent."""

    summary: str
    top_risks: list[str] = Field(default_factory=list)
    recommended_scenario: str = "balanced"  # "conservative" | "balanced" | "deep"
    urgency_level: UrgencyLevel = UrgencyLevel.MEDIUM
    agent_confidence: int = 0  # 0-100
    used_fallback: bool = False


class ScanDelta(BaseModel):
    """Difference between the current scan and the previous scan of the same folder."""

    previous_scan_at: datetime | None = None
    days_since_last_scan: int | None = None
    bytes_delta: int = 0        # positive = workspace grew, negative = shrank
    items_delta: int = 0
    reclaimable_delta: int = 0
    summary: str = ""           # human-readable description of the change


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


class ProcessLink(BaseModel):
    pid: int
    name: str
    match_type: str
    matched_path: str
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
    dormant_days: int | None = None
    confidence: int = 0
    linked_processes: list[ProcessLink] = Field(default_factory=list)
    path_device: int | None = None
    path_inode: int | None = None
    path_mtime_ns: int | None = None
    path_is_symlink: bool = False


class WorkspaceProfile(BaseModel):
    root: str
    project_types: list[str] = Field(default_factory=list)
    markers: list[str] = Field(default_factory=list)
    artifact_counts: dict[str, int] = Field(default_factory=dict)
    total_candidate_bytes: int = 0
    candidate_count: int = 0
    active_process_count: int = 0
    summary: str = "No developer workspace profile generated yet."


class CleanupScenario(BaseModel):
    scenario_id: str
    name: str
    description: str
    action_ids: list[str] = Field(default_factory=list)
    estimated_recoverable_bytes: int = 0
    item_count: int = 0
    low_risk_count: int = 0
    medium_risk_count: int = 0
    review_count: int = 0
    blocked_count: int = 0
    active_process_count: int = 0
    confidence: int = 0


class SimulationResult(BaseModel):
    scenario_id: str
    estimated_recoverable_bytes: int
    remaining_candidate_bytes: int
    selected_count: int
    blocked_count: int = 0
    active_process_count: int = 0
    notes: list[str] = Field(default_factory=list)


class PlanValidationResult(BaseModel):
    valid: bool
    approved_action_ids: list[str] = Field(default_factory=list)
    blocked_action_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


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
    dormant_days: int | None = None
    confidence: int = 0
    linked_processes: list[ProcessLink] = Field(default_factory=list)
    path_device: int | None = None
    path_inode: int | None = None
    path_mtime_ns: int | None = None
    path_is_symlink: bool = False


class MaintenancePlan(BaseModel):
    diagnosis_summary: str
    performance_recommendations: list[MaintenanceAction] = Field(default_factory=list)
    cleanup_actions: list[MaintenanceAction] = Field(default_factory=list)
    blocked_actions: list[MaintenanceAction] = Field(default_factory=list)
    estimated_recoverable_bytes: int = 0
    workspace_profile: WorkspaceProfile | None = None
    cleanup_scenarios: list[CleanupScenario] = Field(default_factory=list)
    simulation_results: list[SimulationResult] = Field(default_factory=list)
    validation: PlanValidationResult | None = None
    # Structured agent output (Features 1 & 3)
    diagnosis_result: DiagnosisResult | None = None
    scan_delta: ScanDelta | None = None


class QuarantineRecord(BaseModel):
    id: int
    original_path: str
    quarantine_path: str
    size_bytes: int
    reason: str
    timestamp: datetime
    restored: bool = False
    permanently_deleted: bool = False
    artifact_name: str = ""
    project_type: str = "Unknown"


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
    workspace_profile: WorkspaceProfile | None = None
    process_links: list[ProcessLink] = Field(default_factory=list)
