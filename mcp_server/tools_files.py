from __future__ import annotations

from core.models import ScanItem
from core.scanner import (
    detect_project_root,
    detect_project_type,
    estimate_cleanup_space,
    find_developer_junk,
    rebuildability_for,
    scan_cache_folders,
    scan_selected_folder,
)
from core.workspace_intelligence import (
    build_cleanup_scenarios,
    link_processes_to_root,
    list_roots,
    profile_workspace,
    simulate_scenario,
    validate_approved_actions,
)


__all__ = [
    "scan_selected_folder",
    "find_developer_junk",
    "scan_cache_folders",
    "estimate_cleanup_space",
    "detect_project_root",
    "detect_project_type",
    "rebuildability_for",
    "list_roots",
    "profile_workspace",
    "build_cleanup_scenarios",
    "link_processes_to_root",
    "simulate_scenario",
    "validate_approved_actions",
    "ScanItem",
]
