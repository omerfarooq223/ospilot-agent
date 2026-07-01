from __future__ import annotations

import os
import time
from pathlib import Path

from agents.maintenance_planner_agent import create_plan
from core.models import Observation, SystemMetrics
from core.scanner import scan_selected_folder


def _observation(items) -> Observation:
    return Observation(
        metrics=SystemMetrics(cpu_percent=5, ram_percent=10, disk_percent=20, available_disk_bytes=1000, total_disk_bytes=2000),
        scan_items=items,
    )


def test_old_lockfile_node_modules_is_autopilot_eligible(tmp_path: Path) -> None:
    project = tmp_path / "old_app"
    node_modules = project / "node_modules"
    node_modules.mkdir(parents=True)
    (project / "package.json").write_text("{}")
    (project / "package-lock.json").write_text("{}")
    (node_modules / "lib.js").write_text("demo")

    old_timestamp = time.time() - (31 * 24 * 60 * 60)
    os.utime(project, (old_timestamp, old_timestamp))
    os.utime(node_modules, (old_timestamp, old_timestamp))

    items = scan_selected_folder(tmp_path)
    plan = create_plan(_observation(items), "test")
    action = next(item for item in plan.cleanup_actions if item.path == str(node_modules))

    assert action.automation_eligible
    assert action.inbox_bucket == "stale_safe"
    assert action.days_since_opened is not None
    assert action.days_since_opened >= 30
    assert "package-lock.json" in action.evidence


def test_recent_node_modules_stays_active_space(tmp_path: Path) -> None:
    project = tmp_path / "fresh_app"
    node_modules = project / "node_modules"
    node_modules.mkdir(parents=True)
    (project / "package.json").write_text("{}")
    (project / "package-lock.json").write_text("{}")
    (node_modules / "lib.js").write_text("demo")

    items = scan_selected_folder(tmp_path)
    plan = create_plan(_observation(items), "test")
    action = next(item for item in plan.cleanup_actions if item.path == str(node_modules))

    assert not action.automation_eligible
    assert action.inbox_bucket == "active_space"
