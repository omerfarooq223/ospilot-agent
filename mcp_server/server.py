from __future__ import annotations

from mcp_server.safety_rules import classify_file_risk, is_protected_path, validate_cleanup_plan
from mcp_server.tools_files import (
    build_cleanup_scenarios,
    detect_project_root,
    detect_project_type,
    estimate_cleanup_space,
    find_developer_junk,
    link_processes_to_root,
    list_roots,
    profile_workspace,
    rebuildability_for,
    scan_cache_folders,
    scan_selected_folder,
    simulate_scenario,
    validate_approved_actions,
)
from mcp_server.tools_quarantine import list_quarantine, quarantine_item, restore_item
from mcp_server.tools_reporting import generate_maintenance_report, write_audit_log
from mcp_server.tools_system import (
    analyze_performance_pressure,
    detect_idle_heavy_apps,
    get_disk_usage,
    get_process_snapshot,
    get_system_metrics,
    get_top_processes,
)


TOOLS = {
    "get_system_metrics": get_system_metrics,
    "get_process_snapshot": get_process_snapshot,
    "get_top_processes": get_top_processes,
    "analyze_performance_pressure": analyze_performance_pressure,
    "detect_idle_heavy_apps": detect_idle_heavy_apps,
    "get_disk_usage": get_disk_usage,
    "list_roots": list_roots,
    "scan_selected_folder": scan_selected_folder,
    "find_developer_junk": find_developer_junk,
    "scan_cache_folders": scan_cache_folders,
    "estimate_cleanup_space": estimate_cleanup_space,
    "profile_workspace": profile_workspace,
    "build_cleanup_scenarios": build_cleanup_scenarios,
    "link_processes_to_root": link_processes_to_root,
    "simulate_scenario": simulate_scenario,
    "validate_approved_actions": validate_approved_actions,
    "detect_project_root": detect_project_root,
    "detect_project_type": detect_project_type,
    "rebuildability_for": rebuildability_for,
    "is_protected_path": is_protected_path,
    "classify_file_risk": classify_file_risk,
    "validate_cleanup_plan": validate_cleanup_plan,
    "quarantine_item": quarantine_item,
    "restore_item": restore_item,
    "list_quarantine": list_quarantine,
    "write_audit_log": write_audit_log,
    "generate_maintenance_report": generate_maintenance_report,
}


def call_tool(name: str, **kwargs):
    if name not in TOOLS:
        raise ValueError(f"Tool is not exposed by OSPilot: {name}")
    return TOOLS[name](**kwargs)
