from __future__ import annotations

from core.audit_log import audit_summary, write_audit_log
from core.models import MaintenancePlan
from core.scoring import format_bytes


def generate_maintenance_report(plan: MaintenancePlan | None = None) -> dict[str, object]:
    summary = audit_summary()
    report: dict[str, object] = {"audit": summary}
    if plan:
        report.update(
            {
                "diagnosis": plan.diagnosis_summary,
                "recoverable": format_bytes(plan.estimated_recoverable_bytes),
                "advisory_count": len(plan.performance_recommendations),
                "cleanup_count": len(plan.cleanup_actions),
                "blocked_count": len(plan.blocked_actions),
            }
        )
    return report


__all__ = ["write_audit_log", "generate_maintenance_report"]
