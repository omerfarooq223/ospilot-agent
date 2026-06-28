from __future__ import annotations

from core.audit_log import audit_summary
from core.models import MaintenancePlan, QuarantineRecord, SystemMetrics
from core.scoring import format_bytes, health_score, pressure_score


def generate_report(
    before_metrics: SystemMetrics,
    after_metrics: SystemMetrics,
    plan: MaintenancePlan,
    quarantined: list[QuarantineRecord],
) -> dict[str, object]:
    recovered = sum(record.size_bytes for record in quarantined)
    all_actions = [*plan.cleanup_actions, *plan.performance_recommendations, *plan.blocked_actions]
    rebuildable_count = sum(1 for action in all_actions if action.rebuildability.value in {"High", "Medium"})
    project_types = sorted({action.project_type for action in all_actions if action.project_type != "Unknown"})
    automation_candidates = [action for action in plan.cleanup_actions if action.automation_eligible]
    automation_bytes = sum(action.size_bytes for action in automation_candidates)
    recovery_recipes = [
        {"path": action.path, "project_type": action.project_type, "recipe": action.recovery_recipe}
        for action in plan.cleanup_actions
        if action.recovery_recipe
    ]
    return {
        "before_health_score": health_score(before_metrics),
        "after_health_score": health_score(after_metrics),
        "before_pressure_score": pressure_score(before_metrics),
        "after_pressure_score": pressure_score(after_metrics),
        "recovered_bytes": recovered,
        "recovered": format_bytes(recovered),
        "quarantined_count": len(quarantined),
        "advisory_count": len(plan.performance_recommendations),
        "cleanup_count": len(plan.cleanup_actions),
        "blocked_count": len(plan.blocked_actions),
        "automation_candidate_count": len(automation_candidates),
        "automation_candidate_space": format_bytes(automation_bytes),
        "automation_candidates": [
            {
                "path": action.path,
                "space": format_bytes(action.size_bytes),
                "reason": action.automation_reason,
            }
            for action in automation_candidates
        ],
        "rebuildable_artifact_count": rebuildable_count,
        "project_types": project_types,
        "workspace_profile": plan.workspace_profile.model_dump() if plan.workspace_profile else None,
        "cleanup_scenarios": [
            {
                "name": scenario.name,
                "estimated_recoverable": format_bytes(scenario.estimated_recoverable_bytes),
                "item_count": scenario.item_count,
                "confidence": scenario.confidence,
            }
            for scenario in plan.cleanup_scenarios
        ],
        "simulation_results": [simulation.model_dump() for simulation in plan.simulation_results],
        "recovery_recipes": recovery_recipes,
        "audit": audit_summary(),
    }
