from __future__ import annotations

from core.models import ActionMode, MaintenanceAction, ProcessLink, RebuildabilityLevel, RiskLevel, ScanItem
from core.workspace_intelligence import build_cleanup_scenarios, profile_workspace, validate_approved_actions
from mcp_server.safety_rules import path_identity


def test_profile_workspace_summarizes_candidates(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    item = ScanItem(
        path=str(tmp_path / "node_modules"),
        item_type="developer_junk",
        size_bytes=1024,
        risk_level=RiskLevel.MEDIUM,
        reason="Node dependencies",
        recommended_action="Quarantine after review",
        project_root=str(tmp_path),
        project_type="Node",
        rebuildability=RebuildabilityLevel.HIGH,
        recovery_recipe="Rebuild with: npm install",
        evidence=["package.json"],
    )

    profile = profile_workspace(tmp_path, [item], [])

    assert profile.project_types == ["Node"]
    assert "package.json" in profile.markers
    assert profile.candidate_count == 1
    assert profile.total_candidate_bytes == 1024


def test_scenarios_exclude_active_process_linked_actions(tmp_path):
    active_link = ProcessLink(pid=123, name="python", match_type="cwd", matched_path=str(tmp_path))
    safe = MaintenanceAction(
        action_id="safe",
        action_mode=ActionMode.QUARANTINE,
        path=str(tmp_path / "__pycache__"),
        reason="Generated cache",
        size_bytes=500,
        risk_level=RiskLevel.LOW,
        rebuildability=RebuildabilityLevel.HIGH,
        confidence=95,
    )
    active = safe.model_copy(
        update={
            "action_id": "active",
            "path": str(tmp_path / "node_modules"),
            "risk_level": RiskLevel.MEDIUM,
            "linked_processes": [active_link],
        }
    )

    scenarios = build_cleanup_scenarios([safe, active])
    approved = validate_approved_actions([safe, active], ["safe", "active"])

    assert all("active" not in scenario.action_ids for scenario in scenarios)
    assert approved.approved_action_ids == ["safe"]
    assert approved.blocked_action_ids == ["active"]


def test_validate_approved_actions_blocks_changed_identity(tmp_path):
    target = tmp_path / "project" / "__pycache__"
    target.mkdir(parents=True)
    identity = path_identity(target)
    action = MaintenanceAction(
        action_id="cache",
        action_mode=ActionMode.QUARANTINE,
        path=str(target),
        reason="Generated cache",
        size_bytes=500,
        risk_level=RiskLevel.LOW,
        rebuildability=RebuildabilityLevel.HIGH,
        **identity,
    )

    changed = tmp_path / "project" / "__pycache___old"
    target.rename(changed)
    target.mkdir()
    approved = validate_approved_actions([action], ["cache"])

    assert approved.approved_action_ids == []
    assert approved.blocked_action_ids == ["cache"]
    assert "identity changed" in " ".join(approved.reasons)
