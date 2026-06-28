from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from core.models import ActionMode, MaintenanceAction, RebuildabilityLevel


STALE_DAYS_THRESHOLD = 30
ACTIVE_DAYS_THRESHOLD = 30
GENERATED_NAMES = {
    # Python
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ipynb_checkpoints", ".tox", ".eggs",
    # JavaScript / TypeScript
    ".next", ".turbo", ".nx", ".parcel-cache", ".angular", ".svelte-kit",
    # Generic build outputs
    "dist", "build", ".cache", "coverage", "__snapshots__",
    # Rust
    "target",
    # Java / Kotlin
    ".gradle",
    # Dart / Flutter
    ".dart_tool", ".pub-cache",
}


def _path_activity_time(path: str | Path) -> datetime | None:
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _days_since(moment: datetime | None) -> int | None:
    if moment is None:
        return None
    return max(0, (datetime.now(timezone.utc) - moment).days)


def _has_any_evidence(action: MaintenanceAction, names: set[str]) -> bool:
    return bool(names.intersection(set(action.evidence or [])))


def _size_score(size_bytes: int) -> int:
    mb = size_bytes / (1024 * 1024)
    if mb >= 1024:
        return 40
    if mb >= 500:
        return 30
    if mb >= 100:
        return 20
    if mb >= 30:
        return 10
    return 5


def apply_cleanup_policy(action: MaintenanceAction) -> MaintenanceAction:
    if action.action_mode != ActionMode.QUARANTINE or not action.path:
        return action.model_copy(update={"inbox_bucket": "manual_review"})

    name = Path(action.path).name
    activity = _path_activity_time(action.project_root or action.path)
    days = _days_since(activity)
    stale = days is not None and days >= STALE_DAYS_THRESHOLD
    active = days is not None and days < ACTIVE_DAYS_THRESHOLD
    rebuildable = action.rebuildability in {RebuildabilityLevel.HIGH, RebuildabilityLevel.MEDIUM}

    automation_eligible = False
    automation_reason = ""

    if name == "node_modules" and stale and _has_any_evidence(action, {"package-lock.json", "pnpm-lock.yaml", "yarn.lock"}):
        automation_eligible = True
        automation_reason = (
            f"Autopilot rule matched: stale Node dependencies, lockfile evidence, "
            f"and no recent project activity for {days} days."
        )
    elif name in {".venv", "venv"} and stale and _has_any_evidence(
        action, {"requirements.txt", "pyproject.toml", "Pipfile", "environment.yml", "environment.yaml"}
    ):
        automation_eligible = True
        automation_reason = (
            f"Autopilot rule matched: stale Python environment, manifest evidence, "
            f"and no recent project activity for {days} days."
        )
    elif name in GENERATED_NAMES and stale and rebuildable:
        automation_eligible = True
        automation_reason = (
            f"Autopilot rule matched: stale generated artifact with {action.rebuildability.value} rebuildability "
            f"and no recent project activity for {days} days."
        )

    priority_score = _size_score(action.size_bytes)
    if rebuildable:
        priority_score += 30
    if stale:
        priority_score += 25
    if automation_eligible:
        priority_score += 20
    if active:
        priority_score -= 10
    priority_score = max(0, min(100, priority_score))

    if automation_eligible:
        bucket = "stale_safe"
        priority_reason = "High-confidence stale cleanup candidate."
    elif active:
        bucket = "active_space"
        priority_reason = "Uses space but appears recently active, so review before cleanup."
    elif rebuildable:
        bucket = "priority_cleanup"
        priority_reason = "Rebuildable cleanup candidate ranked by size and evidence."
    else:
        bucket = "manual_review"
        priority_reason = "Needs human review before cleanup."

    return action.model_copy(
        update={
            "last_opened_at": activity,
            "days_since_opened": days,
            "dormant_days": days,
            "priority_score": priority_score,
            "priority_reason": priority_reason,
            "automation_eligible": automation_eligible,
            "automation_reason": automation_reason,
            "inbox_bucket": bucket,
        }
    )
