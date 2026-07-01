from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api import main
from api.main import app, clean_path_input
from core.models import ActionMode, DiagnosisResult, MaintenanceAction, MaintenancePlan, Observation, RiskLevel, SystemMetrics
from core.scan_history_db import get_last_snapshot, save_scan_snapshot


def _observation() -> Observation:
    return Observation(
        metrics=SystemMetrics(
            cpu_percent=5,
            ram_percent=10,
            disk_percent=20,
            available_disk_bytes=1000,
            total_disk_bytes=2000,
        )
    )


def test_clean_path_input_accepts_user_friendly_paste() -> None:
    assert clean_path_input('"~/Downloads",') == "~/Downloads"
    assert clean_path_input("'~/Documents/projects';") == "~/Documents/projects"
    assert clean_path_input("file:///Users/demo/My%20Project") == "/Users/demo/My Project"


def test_quarantine_uses_server_side_scan_plan(monkeypatch, tmp_path: Path) -> None:
    main.SCAN_SESSIONS.clear()
    safe_path = tmp_path / "safe" / "__pycache__"
    malicious_path = tmp_path / "important"
    safe_path.mkdir(parents=True)
    malicious_path.mkdir()

    safe_plan = MaintenancePlan(
        diagnosis_summary="safe",
        cleanup_actions=[
            MaintenanceAction(
                action_id="safe-action",
                action_mode=ActionMode.QUARANTINE,
                path=str(safe_path),
                reason="cache",
                risk_level=RiskLevel.LOW,
            )
        ],
    )
    malicious_plan = MaintenancePlan(
        diagnosis_summary="malicious",
        cleanup_actions=[
            MaintenanceAction(
                action_id="safe-action",
                action_mode=ActionMode.QUARANTINE,
                path=str(malicious_path),
                reason="not from scan",
                risk_level=RiskLevel.LOW,
            )
        ],
    )
    captured: dict[str, MaintenancePlan] = {}

    def fake_build_plan(folder, min_size_mb=30, scan_delta=None, previous_snapshot=None):
        return _observation(), safe_plan, DiagnosisResult(summary="safe", used_fallback=True)

    def fake_execute_approved_actions(plan, approved_action_ids):
        captured["plan"] = plan
        return []

    monkeypatch.setattr(main, "build_plan", fake_build_plan)
    monkeypatch.setattr(main, "execute_approved_actions", fake_execute_approved_actions)
    monkeypatch.setattr(main, "run_report", lambda observation, plan, quarantined: {})

    client = TestClient(app)
    scan_response = client.post("/api/scan", json={"folder": str(tmp_path), "min_size_mb": 30})
    assert scan_response.status_code == 200
    session_id = scan_response.json()["session_id"]

    quarantine_response = client.post(
        "/api/quarantine",
        json={
            "session_id": session_id,
            "observation": _observation().model_dump(mode="json"),
            "plan": malicious_plan.model_dump(mode="json"),
            "approved_action_ids": ["safe-action"],
        },
    )

    assert quarantine_response.status_code == 200
    assert captured["plan"].cleanup_actions[0].path == str(safe_path)


def test_autopilot_quarantine_uses_only_server_policy_candidates(monkeypatch, tmp_path: Path) -> None:
    main.SCAN_SESSIONS.clear()
    auto_path = tmp_path / "old_app" / "node_modules"
    manual_path = tmp_path / "fresh_app" / "node_modules"
    auto_path.mkdir(parents=True)
    manual_path.mkdir(parents=True)
    plan = MaintenancePlan(
        diagnosis_summary="safe autopilot",
        cleanup_actions=[
            MaintenanceAction(
                action_id="auto-action",
                action_mode=ActionMode.QUARANTINE,
                path=str(auto_path),
                reason="stale lockfile-backed dependency folder",
                risk_level=RiskLevel.MEDIUM,
                automation_eligible=True,
            ),
            MaintenanceAction(
                action_id="manual-action",
                action_mode=ActionMode.QUARANTINE,
                path=str(manual_path),
                reason="recent dependency folder",
                risk_level=RiskLevel.MEDIUM,
                automation_eligible=False,
            ),
        ],
    )
    main.SCAN_SESSIONS["session-1"] = {
        "created_at": main.datetime.now(main.timezone.utc),
        "folder": str(tmp_path),
        "observation": _observation(),
        "plan": plan,
    }
    captured: dict[str, list[str]] = {}

    def fake_execute_approved_actions(server_plan, approved_action_ids):
        captured["ids"] = approved_action_ids
        return []

    monkeypatch.setattr(main, "execute_approved_actions", fake_execute_approved_actions)
    monkeypatch.setattr(main, "run_report", lambda observation, server_plan, quarantined: {})

    response = TestClient(app).post("/api/autopilot/quarantine", json={"session_id": "session-1"})

    assert response.status_code == 200
    assert response.json()["approved_action_ids"] == ["auto-action"]
    assert captured["ids"] == ["auto-action"]


def test_autopilot_quarantine_rejects_session_without_candidates(tmp_path: Path) -> None:
    main.SCAN_SESSIONS.clear()
    plan = MaintenancePlan(
        diagnosis_summary="no autopilot",
        cleanup_actions=[
            MaintenanceAction(
                action_id="manual-action",
                action_mode=ActionMode.QUARANTINE,
                path=str(tmp_path / "fresh_app" / "node_modules"),
                reason="recent dependency folder",
                risk_level=RiskLevel.MEDIUM,
                automation_eligible=False,
            )
        ],
    )
    main.SCAN_SESSIONS["session-2"] = {
        "created_at": main.datetime.now(main.timezone.utc),
        "folder": str(tmp_path),
        "observation": _observation(),
        "plan": plan,
    }

    response = TestClient(app).post("/api/autopilot/quarantine", json={"session_id": "session-2"})

    assert response.status_code == 400
    assert "Safe Autopilot policy" in response.json()["detail"]


def test_report_export_escapes_html() -> None:
    response = TestClient(app).post(
        "/api/report/export",
        json={"format": "html", "report": {"unsafe": "<script>alert('x')</script>"}},
    )

    assert response.status_code == 200
    assert "&lt;script&gt;" in response.text
    assert "<script>alert" not in response.text


def test_scan_result_passes_previous_snapshot_to_agent(monkeypatch, tmp_path: Path) -> None:
    previous = {
        "id": 1,
        "folder": str(tmp_path),
        "timestamp": main.datetime.now(main.timezone.utc).isoformat(),
        "total_items": 1,
        "total_bytes": 100,
        "reclaimable_bytes": 50,
        "project_types": [],
        "artifact_summary": {},
    }
    captured: dict[str, object] = {}
    plan = MaintenancePlan(diagnosis_summary="delta-aware")

    def fake_build_plan(folder, min_size_mb=30, scan_delta=None, previous_snapshot=None):
        captured["previous_snapshot"] = previous_snapshot
        return _observation(), plan, DiagnosisResult(summary="delta-aware", used_fallback=True)

    monkeypatch.setattr(main, "get_last_snapshot", lambda folder: previous)
    monkeypatch.setattr(main, "save_scan_snapshot", lambda folder, observation, plan: 2)
    monkeypatch.setattr(main, "build_plan", fake_build_plan)

    response = main.build_scan_result(tmp_path, min_size_mb=30)

    assert response.plan.diagnosis_summary == "delta-aware"
    assert captured["previous_snapshot"] == previous


def test_get_last_snapshot_returns_latest_saved_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "scan.sqlite3"
    folder = str(tmp_path / "workspace")
    observation = _observation()
    plan_one = MaintenancePlan(diagnosis_summary="one", estimated_recoverable_bytes=10)
    plan_two = MaintenancePlan(diagnosis_summary="two", estimated_recoverable_bytes=20)

    save_scan_snapshot(folder, observation, plan_one, db_path=db_path)
    save_scan_snapshot(folder, observation, plan_two, db_path=db_path)
    latest = get_last_snapshot(folder, db_path=db_path)

    assert latest is not None
    assert latest["reclaimable_bytes"] == 20
