from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.models import ActionMode, MaintenanceAction, MaintenancePlan, ProcessInfo, RiskLevel, SystemMetrics
from core.scheduler_config import SchedulerConfig, load_scheduler_config, save_scheduler_config
from core.scheduler import install_cron
from core.weekly_report import build_weekly_report_markdown, write_weekly_report
from demo.create_demo_workspace import create_demo_workspace


def test_scheduler_config_round_trip(tmp_path, monkeypatch):
    config_path = tmp_path / "scheduler.json"
    monkeypatch.setattr("core.scheduler_config.SCHEDULER_CONFIG_PATH", config_path)
    config = SchedulerConfig(enabled=True, folders=["/tmp/projects"], weekday=0, hour=9, minute=30)
    save_scheduler_config(config, config_path)
    loaded = load_scheduler_config(config_path)
    assert loaded.enabled is True
    assert loaded.folders == ["/tmp/projects"]
    assert loaded.weekday == 0


def test_scheduler_config_accepts_five_gb_threshold(tmp_path):
    config = SchedulerConfig(folders=[str(tmp_path)], min_size_mb=5000)
    assert config.min_size_mb == 5000


def test_cron_install_quotes_paths_with_spaces(monkeypatch, tmp_path):
    written: dict[str, str] = {}
    script_path = tmp_path / "Project With Spaces" / "weekly scan.py"
    script_path.parent.mkdir()
    script_path.write_text("print('scan')", encoding="utf-8")

    monkeypatch.setattr("core.scheduler.WEEKLY_SCAN_SCRIPT", script_path)
    monkeypatch.setattr("core.scheduler._read_crontab", lambda: "")
    monkeypatch.setattr("core.scheduler._write_crontab", lambda content: written.update(content=content))

    install_cron(
        SchedulerConfig(
            folders=[str(tmp_path)],
            python_executable="/tmp/Python With Spaces/bin/python",
        )
    )

    assert "'/tmp/Python With Spaces/bin/python'" in written["content"]
    assert "'{}'".format(script_path.resolve()) in written["content"]


def test_weekly_report_is_human_readable(tmp_path, monkeypatch):
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr("core.weekly_report.REPORTS_DIR", reports_dir)
    demo_root = create_demo_workspace(reset=True)
    metrics = SystemMetrics(cpu_percent=40, ram_percent=70, disk_percent=80, available_disk_bytes=10_000_000, total_disk_bytes=100_000_000)
    plan = MaintenancePlan(
        diagnosis_summary="Your workspace contains old developer dependencies.",
        performance_recommendations=[
            MaintenanceAction(
                action_id="advice-1",
                action_mode=ActionMode.ADVISORY,
                reason="Consider closing Docker Desktop manually.",
                risk_level=RiskLevel.LOW,
            )
        ],
        cleanup_actions=[
            MaintenanceAction(
                action_id="cleanup-1",
                action_mode=ActionMode.QUARANTINE,
                path=str(demo_root / "python_cache" / "__pycache__"),
                reason="Python cache folder",
                size_bytes=65536,
                risk_level=RiskLevel.LOW,
            )
        ],
        estimated_recoverable_bytes=65536,
    )
    observation = {
        "metrics": metrics,
        "top_memory_processes": [
            ProcessInfo(pid=1, name="Code", cpu_percent=2, memory_mb=900),
        ],
        "top_cpu_processes": [],
        "pressure_summary": {},
        "idle_heavy_apps": [],
        "scan_items": [],
    }

    class ObservationWrapper:
        def __init__(self, data):
            self.metrics = data["metrics"]
            self.top_memory_processes = data["top_memory_processes"]
            self.idle_heavy_apps = data["idle_heavy_apps"]

    folder_results = [{"folder": str(demo_root), "observation": ObservationWrapper(observation), "plan": plan}]
    markdown = build_weekly_report_markdown(folder_results, generated_at=datetime(2026, 6, 25, tzinfo=timezone.utc))
    assert "# OSPilot Weekly Report" in markdown
    assert "Read-only scheduled scan" in markdown
    assert "Docker Desktop" in markdown
    assert "python_cache" in markdown

    paths = write_weekly_report(folder_results, generated_at=datetime(2026, 6, 25, tzinfo=timezone.utc))
    assert paths["markdown"].exists()
    assert paths["html"].exists()
    assert "OSPilot Weekly Report" in paths["html"].read_text(encoding="utf-8")
