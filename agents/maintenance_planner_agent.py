from __future__ import annotations

from core.models import ActionMode, MaintenanceAction, MaintenancePlan, Observation, RiskLevel
from core.automation_policy import apply_cleanup_policy
from core.scoring import format_bytes
from mcp_server.safety_rules import scan_item_to_action


def create_plan(observation: Observation, diagnosis_summary: str) -> MaintenancePlan:
    recommendations: list[MaintenanceAction] = []
    for index, proc in enumerate(observation.idle_heavy_apps[:5], start=1):
        recommendations.append(
            MaintenanceAction(
                action_id=f"advice-{index}",
                action_mode=ActionMode.ADVISORY,
                path=None,
                reason=f"Consider closing {proc.name} manually if it is not needed. It is using {proc.memory_mb:.0f} MB RAM.",
                size_bytes=0,
                risk_level=RiskLevel.LOW,
            )
        )

    cleanup_actions: list[MaintenanceAction] = []
    blocked_actions: list[MaintenanceAction] = []
    for index, item in enumerate(observation.scan_items, start=1):
        action = scan_item_to_action(item, index)
        action = action.model_copy(
            update={
                "reason": (
                    f"{item.reason} Rebuildability: {item.rebuildability.value}. "
                    f"Evidence: {', '.join(item.evidence) if item.evidence else 'no manifest found'}. "
                    f"Recovery: {item.recovery_recipe}"
                )
            }
        )
        if action.action_mode == ActionMode.QUARANTINE:
            cleanup_actions.append(apply_cleanup_policy(action))
        elif action.action_mode == ActionMode.ADVISORY:
            recommendations.append(
                action.model_copy(
                    update={
                        "action_id": f"review-{index}",
                        "reason": f"Review manually: {item.reason} ({format_bytes(item.size_bytes)}).",
                    }
                )
            )
        else:
            blocked_actions.append(action)

    return MaintenancePlan(
        diagnosis_summary=diagnosis_summary,
        performance_recommendations=recommendations,
        cleanup_actions=sorted(cleanup_actions, key=lambda item: (item.priority_score, item.size_bytes), reverse=True),
        blocked_actions=blocked_actions,
        estimated_recoverable_bytes=sum(action.size_bytes for action in cleanup_actions),
    )
