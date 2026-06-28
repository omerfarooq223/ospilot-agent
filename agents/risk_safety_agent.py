from __future__ import annotations

from core.models import MaintenancePlan
from mcp_server.safety_rules import validate_cleanup_plan


def validate_plan(plan: MaintenancePlan) -> MaintenancePlan:
    return validate_cleanup_plan(plan)
