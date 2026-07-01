from __future__ import annotations

import pytest

from core.models import ActionMode, MaintenanceAction, MaintenancePlan, RiskLevel
from mcp_server.safety_rules import classify_file_risk, is_protected_path, validate_cleanup_plan


def test_protected_macos_paths_are_blocked() -> None:
    assert is_protected_path("/System")
    assert is_protected_path("/System/Library")
    assert classify_file_risk("/System/Library") == RiskLevel.BLOCKED


def test_validate_cleanup_plan_blocks_protected_paths() -> None:
    plan = MaintenancePlan(
        diagnosis_summary="test",
        cleanup_actions=[
            MaintenanceAction(
                action_id="unsafe",
                action_mode=ActionMode.QUARANTINE,
                path="/System/Library",
                reason="bad idea",
                risk_level=RiskLevel.LOW,
            )
        ],
    )
    validated = validate_cleanup_plan(plan)
    assert validated.cleanup_actions == []
    assert len(validated.blocked_actions) == 1
    assert validated.blocked_actions[0].risk_level == RiskLevel.BLOCKED


def test_symlink_paths_are_blocked(tmp_path) -> None:
    target = tmp_path / "real_node_modules"
    target.mkdir()
    link = tmp_path / "node_modules"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink creation is not available: {exc}")

    plan = MaintenancePlan(
        diagnosis_summary="test",
        cleanup_actions=[
            MaintenanceAction(
                action_id="link",
                action_mode=ActionMode.QUARANTINE,
                path=str(link),
                reason="symlinked dependency folder",
                risk_level=RiskLevel.MEDIUM,
            )
        ],
    )
    validated = validate_cleanup_plan(plan)

    assert classify_file_risk(link) == RiskLevel.BLOCKED
    assert validated.cleanup_actions == []
    assert validated.blocked_actions[0].risk_level == RiskLevel.BLOCKED
