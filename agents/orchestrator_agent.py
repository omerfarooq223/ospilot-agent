from __future__ import annotations

from pathlib import Path

from agents.diagnosis_agent import diagnose
from agents.maintenance_planner_agent import create_plan
from agents.monitor_agent import observe
from agents.report_agent import generate_report
from agents.risk_safety_agent import validate_plan
from core.audit_log import write_audit_log
from core.models import ActionMode, DiagnosisResult, MaintenancePlan, Observation, QuarantineRecord, ScanDelta
from core.scan_history_db import compute_delta
from core.workspace_intelligence import build_cleanup_scenarios, simulate_scenario, validate_approved_actions
from mcp_server.safety_rules import action_path_identity
from mcp_server.tools_quarantine import quarantine_item
from mcp_server.tools_system import get_system_metrics


def build_plan(
    selected_folder: str | Path | None = None,
    min_size_mb: int = 100,
    scan_delta: ScanDelta | None = None,
    previous_snapshot: dict[str, object] | None = None,
) -> tuple[Observation, MaintenancePlan, DiagnosisResult]:
    """Run the full observe → diagnose → plan pipeline.

    Returns ``(observation, plan, diagnosis_result)``.  The caller is responsible
    for persisting the scan snapshot and computing the delta *before* calling this
    so the LLM can incorporate the delta into its summary.
    """
    observation = observe(selected_folder=selected_folder, min_size_mb=min_size_mb)
    if scan_delta is None and previous_snapshot is not None:
        scan_delta = compute_delta(
            current_items=len(observation.scan_items),
            current_bytes=sum(item.size_bytes for item in observation.scan_items),
            current_reclaimable=sum(
                item.size_bytes
                for item in observation.scan_items
                if item.risk_level.value in {"Low", "Medium"}
            ),
            previous=previous_snapshot,
        )
    diagnosis_result = diagnose(observation, scan_delta=scan_delta)
    plan = validate_plan(create_plan(observation, diagnosis_result.summary))
    all_reviewable = [*plan.cleanup_actions, *plan.performance_recommendations]
    scenarios = build_cleanup_scenarios(plan.cleanup_actions, plan.performance_recommendations)
    simulations = [simulate_scenario(scenario, all_reviewable) for scenario in scenarios]
    plan = plan.model_copy(
        update={
            "workspace_profile": observation.workspace_profile,
            "cleanup_scenarios": scenarios,
            "simulation_results": simulations,
            "validation": validate_approved_actions(plan.cleanup_actions, []),
            # Feature 1 & 3 — structured output
            "diagnosis_result": diagnosis_result,
            "scan_delta": scan_delta,
        }
    )
    write_audit_log(
        "plan_created",
        {
            "selected_folder": str(selected_folder) if selected_folder else None,
            "fallback_mode": diagnosis_result.used_fallback,
            "urgency_level": diagnosis_result.urgency_level.value,
            "recommended_scenario": diagnosis_result.recommended_scenario,
            "agent_confidence": diagnosis_result.agent_confidence,
            "cleanup_actions": len(plan.cleanup_actions),
            "blocked_actions": len(plan.blocked_actions),
            "advisory_actions": len(plan.performance_recommendations),
            "scenario_count": len(plan.cleanup_scenarios),
            "active_process_links": len(observation.process_links),
            "has_scan_delta": scan_delta is not None,
        },
    )
    return observation, plan, diagnosis_result


def execute_approved_actions(plan: MaintenancePlan, approved_action_ids: list[str]) -> list[QuarantineRecord]:
    validation = validate_approved_actions(plan.cleanup_actions, approved_action_ids)
    if validation.blocked_action_ids:
        write_audit_log(
            "approval_validation_blocked",
            {"blocked_action_ids": validation.blocked_action_ids, "reasons": validation.reasons},
        )
    approved = set(validation.approved_action_ids)
    quarantined: list[QuarantineRecord] = []
    for action in plan.cleanup_actions:
        if action.action_id not in approved:
            continue
        if action.action_mode != ActionMode.QUARANTINE or not action.path:
            continue
        try:
            record = quarantine_item(
                action.path,
                action.reason,
                expected_identity=action_path_identity(action),
                artifact_name=Path(action.path).name,
                project_type=action.project_type,
            )
        except (FileNotFoundError, ValueError, OSError) as exc:
            write_audit_log(
                "quarantine_blocked_at_execution",
                {"action_id": action.action_id, "path": action.path, "reason": str(exc)},
            )
            continue
        quarantined.append(record)
        write_audit_log(
            "item_quarantined",
            {"action_id": action.action_id, "path": action.path, "size_bytes": record.size_bytes, "reason": action.reason},
        )
    return quarantined


def run_report(before_observation: Observation, plan: MaintenancePlan, quarantined: list[QuarantineRecord]) -> dict[str, object]:
    after_metrics = get_system_metrics()
    report = generate_report(before_observation.metrics, after_metrics, plan, quarantined)
    write_audit_log("report_generated", report)
    return report
