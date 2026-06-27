from __future__ import annotations

import os
import tempfile
from pathlib import Path

from core.models import ActionMode, MaintenanceAction, MaintenancePlan, RiskLevel, ScanItem


PROTECTED_PREFIXES = [
    "/System",
    "/Library",
    "/bin",
    "/sbin",
    "/usr",
    "/Applications",
    "/private",
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]

ALLOWED_PRIVATE_PREFIXES = [
    "/private/tmp",
    "/private/var/folders",
    tempfile.gettempdir(),
]

REVIEW_NAMES = {".git", ".ssh", ".gnupg", ".aws", ".config"}
LOW_RISK_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ipynb_checkpoints"}
MEDIUM_RISK_NAMES = {"node_modules", ".venv", "venv", "dist", "build", ".next", ".cache"}


def normalize_path(path: str | Path) -> str:
    raw = str(path).strip()
    if not raw:
        return raw
    try:
        return str(Path(raw).expanduser().resolve())
    except OSError:
        return str(Path(raw).expanduser().absolute())


def path_identity(path: str | Path) -> dict[str, int | bool | None]:
    """Return a non-following filesystem identity for the reviewed path."""
    try:
        stat = Path(path).expanduser().lstat()
    except OSError:
        return {
            "path_device": None,
            "path_inode": None,
            "path_mtime_ns": None,
            "path_is_symlink": False,
        }
    return {
        "path_device": int(stat.st_dev),
        "path_inode": int(stat.st_ino),
        "path_mtime_ns": int(stat.st_mtime_ns),
        "path_is_symlink": Path(path).expanduser().is_symlink(),
    }


def action_path_identity(action: MaintenanceAction) -> dict[str, int | bool | None]:
    return {
        "path_device": action.path_device,
        "path_inode": action.path_inode,
        "path_mtime_ns": action.path_mtime_ns,
        "path_is_symlink": action.path_is_symlink,
    }


def action_identity_mismatch_reason(action: MaintenanceAction) -> str | None:
    if not action.path:
        return "Action has no filesystem path."
    current = path_identity(action.path)
    if action.path_is_symlink or current["path_is_symlink"]:
        return "Path is or became a symlink, so quarantine is blocked."

    expected_values = [action.path_device, action.path_inode, action.path_mtime_ns]
    if all(value is None for value in expected_values):
        return None
    if current["path_device"] is None or current["path_inode"] is None:
        return "Path no longer exists."
    if current["path_device"] != action.path_device or current["path_inode"] != action.path_inode:
        return "Path identity changed since the scan."
    if action.path_mtime_ns is not None and current["path_mtime_ns"] != action.path_mtime_ns:
        return "Path was modified after the scan."
    return None


def is_protected_path(path: str | Path) -> bool:
    normalized = normalize_path(path)
    drive_norm = normalized.replace("/", "\\")
    for allowed in ALLOWED_PRIVATE_PREFIXES:
        allowed_norm = normalize_path(allowed)
        if normalized == allowed_norm or normalized.startswith(allowed_norm + os.sep):
            return False
    for prefix in PROTECTED_PREFIXES:
        if normalized == prefix or normalized.startswith(prefix + os.sep):
            return True
        if drive_norm == prefix or drive_norm.startswith(prefix + "\\"):
            return True
    root = Path(normalized)
    return root.parent == root


def classify_file_risk(path: str | Path) -> RiskLevel:
    try:
        if Path(path).expanduser().is_symlink():
            return RiskLevel.BLOCKED
    except OSError:
        pass
    normalized = normalize_path(path)
    if is_protected_path(normalized):
        return RiskLevel.BLOCKED
    name = Path(normalized).name
    if name in LOW_RISK_NAMES:
        return RiskLevel.LOW
    if name in MEDIUM_RISK_NAMES:
        return RiskLevel.MEDIUM
    if name in REVIEW_NAMES or name.startswith("."):
        return RiskLevel.NEEDS_REVIEW
    return RiskLevel.NEEDS_REVIEW


def scan_item_to_action(item: ScanItem, index: int) -> MaintenanceAction:
    risk = classify_file_risk(item.path)
    if item.path_is_symlink:
        risk = RiskLevel.BLOCKED
    if risk == RiskLevel.BLOCKED or item.risk_level in {RiskLevel.BLOCKED, RiskLevel.HIGH, RiskLevel.NEEDS_REVIEW}:
        mode = ActionMode.BLOCKED if risk == RiskLevel.BLOCKED else ActionMode.ADVISORY
        return MaintenanceAction(
            action_id=f"item-{index}",
            action_mode=mode,
            path=item.path,
            reason=item.reason,
            size_bytes=item.size_bytes,
            risk_level=RiskLevel.BLOCKED if risk == RiskLevel.BLOCKED else item.risk_level,
            project_root=item.project_root,
            project_type=item.project_type,
            rebuildability=item.rebuildability,
            recovery_recipe=item.recovery_recipe,
            evidence=item.evidence,
            dormant_days=item.dormant_days,
            confidence=item.confidence,
            linked_processes=item.linked_processes,
            path_device=item.path_device,
            path_inode=item.path_inode,
            path_mtime_ns=item.path_mtime_ns,
            path_is_symlink=item.path_is_symlink,
        )
    return MaintenanceAction(
        action_id=f"item-{index}",
        action_mode=ActionMode.QUARANTINE,
        path=item.path,
        reason=item.reason,
        size_bytes=item.size_bytes,
        risk_level=item.risk_level,
        project_root=item.project_root,
        project_type=item.project_type,
        rebuildability=item.rebuildability,
        recovery_recipe=item.recovery_recipe,
        evidence=item.evidence,
        dormant_days=item.dormant_days,
        confidence=item.confidence,
        linked_processes=item.linked_processes,
        path_device=item.path_device,
        path_inode=item.path_inode,
        path_mtime_ns=item.path_mtime_ns,
        path_is_symlink=item.path_is_symlink,
    )


def validate_cleanup_plan(plan: MaintenancePlan) -> MaintenancePlan:
    safe_cleanup: list[MaintenanceAction] = []
    blocked: list[MaintenanceAction] = list(plan.blocked_actions)

    for action in plan.cleanup_actions:
        if not action.path:
            blocked.append(action.model_copy(update={"action_mode": ActionMode.BLOCKED, "risk_level": RiskLevel.BLOCKED}))
            continue
        risk = classify_file_risk(action.path)
        identity_reason = action_identity_mismatch_reason(action)
        if identity_reason:
            blocked.append(
                action.model_copy(
                    update={
                        "action_mode": ActionMode.BLOCKED,
                        "risk_level": RiskLevel.BLOCKED,
                        "reason": f"{action.reason} {identity_reason}",
                    }
                )
            )
            continue
        if action.linked_processes:
            blocked.append(
                action.model_copy(
                    update={
                        "action_mode": ActionMode.BLOCKED,
                        "risk_level": RiskLevel.BLOCKED,
                        "reason": f"{action.reason} A running process is linked to this path, so quarantine is blocked until it is closed.",
                    }
                )
            )
            continue
        if risk == RiskLevel.BLOCKED or action.risk_level in {RiskLevel.BLOCKED, RiskLevel.HIGH, RiskLevel.NEEDS_REVIEW}:
            blocked.append(action.model_copy(update={"action_mode": ActionMode.BLOCKED, "risk_level": RiskLevel.BLOCKED}))
            continue
        safe_cleanup.append(action.model_copy(update={"action_mode": ActionMode.QUARANTINE, "risk_level": risk}))

    return plan.model_copy(
        update={
            "cleanup_actions": safe_cleanup,
            "blocked_actions": blocked,
            "estimated_recoverable_bytes": sum(action.size_bytes for action in safe_cleanup),
        }
    )
