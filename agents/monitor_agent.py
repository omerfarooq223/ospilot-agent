from __future__ import annotations

from pathlib import Path

from core.models import Observation
from core.workspace_intelligence import attach_process_links, link_processes_to_root, profile_workspace
from mcp_server.tools_files import scan_selected_folder
from mcp_server.tools_system import (
    analyze_performance_pressure,
    detect_idle_heavy_apps,
    get_system_metrics,
    get_top_processes,
)


def observe(selected_folder: str | Path | None = None, min_size_mb: int = 100) -> Observation:
    metrics = get_system_metrics()
    process_links = link_processes_to_root(selected_folder) if selected_folder else []
    scan_items = scan_selected_folder(selected_folder, min_size_mb=min_size_mb) if selected_folder else []
    scan_items = attach_process_links(scan_items, process_links) if selected_folder else scan_items
    workspace_profile = profile_workspace(selected_folder, scan_items, process_links) if selected_folder else None
    return Observation(
        metrics=metrics,
        top_memory_processes=get_top_processes(metric="memory", limit=8),
        top_cpu_processes=get_top_processes(metric="cpu", limit=8),
        pressure_summary=analyze_performance_pressure(),
        idle_heavy_apps=detect_idle_heavy_apps(),
        scan_items=scan_items,
        workspace_profile=workspace_profile,
        process_links=process_links,
    )
