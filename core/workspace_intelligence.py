from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import psutil

from core.models import (
    ActionMode,
    CleanupScenario,
    MaintenanceAction,
    PlanValidationResult,
    ProcessLink,
    RebuildabilityLevel,
    RiskLevel,
    ScanItem,
    SimulationResult,
    WorkspaceProfile,
)
from core.feedback_store import restore_penalty
from mcp_server.safety_rules import action_identity_mismatch_reason, classify_file_risk, is_protected_path, normalize_path


WORKSPACE_MARKERS = {
    # JavaScript / TypeScript
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    # Python
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "environment.yml",
    "environment.yaml",
    "setup.py",
    # Rust
    "Cargo.toml",
    "Cargo.lock",
    # Java / Kotlin
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    # Go
    "go.mod",
    # Ruby
    "Gemfile",
    # PHP
    "composer.json",
}


def _days_since_path_activity(path: str | Path | None) -> int | None:
    if not path:
        return None
    try:
        stat = Path(path).stat()
    except OSError:
        return None
    last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - last_modified).days)


def confidence_for_item(item: ScanItem | MaintenanceAction) -> int:
    score = 20
    if item.size_bytes >= 1024 * 1024 * 1024:
        score += 20
    elif item.size_bytes >= 100 * 1024 * 1024:
        score += 12
    elif item.size_bytes >= 30 * 1024 * 1024:
        score += 8

    if item.rebuildability == RebuildabilityLevel.HIGH:
        score += 35
    elif item.rebuildability == RebuildabilityLevel.MEDIUM:
        score += 24
    elif item.rebuildability == RebuildabilityLevel.NOT_REBUILDABLE:
        score -= 30

    if item.evidence:
        score += min(15, len(item.evidence) * 5)
    if item.risk_level == RiskLevel.LOW:
        score += 15
    elif item.risk_level == RiskLevel.MEDIUM:
        score += 8
    elif item.risk_level in {RiskLevel.NEEDS_REVIEW, RiskLevel.HIGH, RiskLevel.BLOCKED}:
        score -= 20
    if getattr(item, "linked_processes", []):
        score -= 35

    # Feature 5 — User feedback learning: lower confidence if the user has
    # previously restored items with the same artifact name / project type.
    artifact_name = getattr(item, "path", None)
    if artifact_name:
        from pathlib import Path as _Path
        artifact_name = _Path(artifact_name).name
    else:
        artifact_name = ""
    project_type = getattr(item, "project_type", "Unknown") or "Unknown"
    penalty = restore_penalty(artifact_name, project_type)
    score -= penalty

    return max(0, min(100, score))


def link_processes_to_root(root_path: str | Path) -> list[ProcessLink]:
    root = Path(normalize_path(root_path))
    if is_protected_path(root) or not root.exists():
        return []

    links: list[ProcessLink] = []
    seen: set[tuple[int, str, str]] = set()
    try:
        iterator = psutil.process_iter(["pid", "name", "cmdline", "cwd"])
        for proc in iterator:
            try:
                info = proc.info
                command = " ".join(info.get("cmdline") or [])
                candidates: list[tuple[str, str]] = []
                cwd = info.get("cwd")
                if cwd:
                    candidates.append(("cwd", cwd))
                for token in info.get("cmdline") or []:
                    if root.name and root.name in token:
                        candidates.append(("cmdline", token))
                try:
                    for open_file in proc.open_files()[:10]:
                        candidates.append(("open_file", open_file.path))
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, PermissionError):
                    pass

                for match_type, raw_path in candidates:
                    try:
                        candidate = Path(raw_path).expanduser().resolve()
                    except OSError:
                        continue
                    if candidate == root or root in candidate.parents:
                        key = (int(info.get("pid") or 0), match_type, str(candidate))
                        if key in seen:
                            continue
                        seen.add(key)
                        links.append(
                            ProcessLink(
                                pid=int(info.get("pid") or 0),
                                name=info.get("name") or "unknown",
                                match_type=match_type,
                                matched_path=str(candidate),
                                command_preview=command[:160],
                            )
                        )
                        break
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, PermissionError):
                continue
    except PermissionError:
        return []
    return links


def attach_process_links(items: list[ScanItem], process_links: list[ProcessLink]) -> list[ScanItem]:
    if not process_links:
        return [item.model_copy(update={"dormant_days": _days_since_path_activity(item.project_root or item.path), "confidence": confidence_for_item(item)}) for item in items]

    enriched: list[ScanItem] = []
    for item in items:
        item_path = Path(item.path)
        item_root = Path(item.project_root) if item.project_root else item_path
        matched: list[ProcessLink] = []
        for link in process_links:
            matched_path = Path(link.matched_path)
            try:
                if item_path == matched_path or item_path in matched_path.parents or item_root == matched_path or item_root in matched_path.parents:
                    matched.append(link)
            except RuntimeError:
                continue
        dormant_days = _days_since_path_activity(item.project_root or item.path)
        candidate = item.model_copy(update={"linked_processes": matched, "dormant_days": dormant_days})
        enriched.append(candidate.model_copy(update={"confidence": confidence_for_item(candidate)}))
    return enriched


def profile_workspace(root_path: str | Path, items: list[ScanItem] | None = None, process_links: list[ProcessLink] | None = None) -> WorkspaceProfile:
    root = Path(normalize_path(root_path))
    markers: set[str] = {marker for item in items or [] for marker in item.evidence if marker in WORKSPACE_MARKERS}
    try:
        markers.update(child.name for child in root.iterdir() if child.name in WORKSPACE_MARKERS)
    except OSError:
        pass

    project_types = sorted({item.project_type for item in items or [] if item.project_type != "Unknown"})
    artifact_counts = Counter(Path(item.path).name for item in items or [])
    total_bytes = sum(item.size_bytes for item in items or [])
    active_process_count = len(process_links or [])
    if not project_types and markers:
        if "package.json" in markers:
            project_types.append("Node")
        if {"requirements.txt", "pyproject.toml", "Pipfile", "environment.yml", "environment.yaml", "setup.py"}.intersection(markers):
            project_types.append("Python")
    summary_bits = []
    if project_types:
        summary_bits.append(f"{', '.join(project_types)} workspace")
    if markers:
        summary_bits.append(f"{len(markers)} manifest markers")
    if items:
        summary_bits.append(f"{len(items)} cleanup candidates")
    if active_process_count:
        summary_bits.append(f"{active_process_count} linked live process signals")
    summary = "Detected " + ", ".join(summary_bits) + "." if summary_bits else "No developer-specific cleanup profile found."
    return WorkspaceProfile(
        root=str(root),
        project_types=project_types,
        markers=sorted(markers),
        artifact_counts=dict(artifact_counts),
        total_candidate_bytes=total_bytes,
        candidate_count=len(items or []),
        active_process_count=active_process_count,
        summary=summary,
    )


def _scenario_from_actions(
    scenario_id: str,
    name: str,
    description: str,
    actions: list[MaintenanceAction],
) -> CleanupScenario:
    low = sum(1 for action in actions if action.risk_level == RiskLevel.LOW)
    medium = sum(1 for action in actions if action.risk_level == RiskLevel.MEDIUM)
    review = sum(1 for action in actions if action.risk_level == RiskLevel.NEEDS_REVIEW)
    blocked = sum(1 for action in actions if action.risk_level == RiskLevel.BLOCKED)
    active = sum(1 for action in actions if action.linked_processes)
    confidence = round(sum(action.confidence for action in actions) / len(actions)) if actions else 0
    return CleanupScenario(
        scenario_id=scenario_id,
        name=name,
        description=description,
        action_ids=[action.action_id for action in actions],
        estimated_recoverable_bytes=sum(action.size_bytes for action in actions),
        item_count=len(actions),
        low_risk_count=low,
        medium_risk_count=medium,
        review_count=review,
        blocked_count=blocked,
        active_process_count=active,
        confidence=confidence,
    )


def build_cleanup_scenarios(
    cleanup_actions: list[MaintenanceAction],
    advisory_actions: list[MaintenanceAction] | None = None,
) -> list[CleanupScenario]:
    available = [action for action in cleanup_actions if action.action_mode == ActionMode.QUARANTINE and not action.linked_processes]
    conservative = [
        action
        for action in available
        if action.risk_level == RiskLevel.LOW
        or (action.automation_eligible and action.rebuildability in {RebuildabilityLevel.HIGH, RebuildabilityLevel.MEDIUM})
    ]
    balanced = [
        action
        for action in available
        if action.risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}
        and action.rebuildability in {RebuildabilityLevel.HIGH, RebuildabilityLevel.MEDIUM}
    ]
    deep = [
        action
        for action in available
        if action.risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}
        and action.rebuildability != RebuildabilityLevel.NOT_REBUILDABLE
    ]

    return [
        _scenario_from_actions("conservative", "Conservative", "Only low-risk or Safe Autopilot-ready rebuildable artifacts.", conservative),
        _scenario_from_actions("balanced", "Balanced", "Adds medium-risk dependencies and generated build outputs with rebuild evidence.", balanced),
        _scenario_from_actions("deep", "Deep Review", "Adds manual-review candidates for a larger simulated recovery, still excluding protected and active items.", deep),
    ]


def simulate_scenario(
    scenario: CleanupScenario,
    all_actions: list[MaintenanceAction],
) -> SimulationResult:
    all_bytes = sum(action.size_bytes for action in all_actions)
    notes: list[str] = []
    if scenario.active_process_count:
        notes.append("Active-process-linked items are excluded from execution.")
    if scenario.blocked_count:
        notes.append("Blocked items remain out of scope.")
    if scenario.review_count:
        notes.append("Manual-review items require explicit selection before quarantine.")
    return SimulationResult(
        scenario_id=scenario.scenario_id,
        estimated_recoverable_bytes=scenario.estimated_recoverable_bytes,
        remaining_candidate_bytes=max(0, all_bytes - scenario.estimated_recoverable_bytes),
        selected_count=scenario.item_count,
        blocked_count=scenario.blocked_count,
        active_process_count=scenario.active_process_count,
        notes=notes,
    )


def _current_process_links_for_action(
    action: MaintenanceAction,
    cache: dict[str, list[ProcessLink]],
) -> list[ProcessLink]:
    if not action.path:
        return []
    root_key = action.project_root or str(Path(action.path).parent)
    if root_key not in cache:
        cache[root_key] = link_processes_to_root(root_key)
    links = cache[root_key]
    if not links:
        return []

    action_path = Path(action.path)
    action_root = Path(action.project_root) if action.project_root else action_path
    matched: list[ProcessLink] = []
    for link in links:
        try:
            matched_path = Path(link.matched_path)
            if (
                action_path == matched_path
                or action_path in matched_path.parents
                or action_root == matched_path
                or action_root in matched_path.parents
            ):
                matched.append(link)
        except RuntimeError:
            continue
    return matched


def validate_approved_actions(plan_actions: list[MaintenanceAction], approved_action_ids: list[str]) -> PlanValidationResult:
    by_id = {action.action_id: action for action in plan_actions}
    approved: list[str] = []
    blocked: list[str] = []
    reasons: list[str] = []
    process_cache: dict[str, list[ProcessLink]] = {}
    for action_id in approved_action_ids:
        action = by_id.get(action_id)
        if not action:
            blocked.append(action_id)
            reasons.append(f"{action_id} was not found in the server-side plan.")
            continue
        if action.action_mode != ActionMode.QUARANTINE or not action.path:
            blocked.append(action_id)
            reasons.append(f"{action_id} is not a quarantine action.")
            continue
        if classify_file_risk(action.path) == RiskLevel.BLOCKED or is_protected_path(action.path):
            blocked.append(action_id)
            reasons.append(f"{action_id} points to a protected path.")
            continue
        identity_reason = action_identity_mismatch_reason(action)
        if identity_reason:
            blocked.append(action_id)
            reasons.append(f"{action_id}: {identity_reason}")
            continue
        if action.linked_processes:
            blocked.append(action_id)
            reasons.append(f"{action_id} is linked to a running process.")
            continue
        current_links = _current_process_links_for_action(action, process_cache)
        if current_links:
            blocked.append(action_id)
            reasons.append(f"{action_id} is currently linked to a running process.")
            continue
        approved.append(action_id)
    return PlanValidationResult(valid=not blocked, approved_action_ids=approved, blocked_action_ids=blocked, reasons=reasons)


def list_roots() -> list[dict[str, str]]:
    home = Path.home().resolve()
    candidates = [home, home / "Desktop", home / "Documents", home / "Downloads"]
    roots = []
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir() and not is_protected_path(candidate):
            roots.append({"name": candidate.name or str(candidate), "uri": candidate.as_uri(), "path": str(candidate)})
    return roots
