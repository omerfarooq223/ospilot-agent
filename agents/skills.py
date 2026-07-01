from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentSkill:
    """Submission-facing skill metadata for each agent role in the pipeline."""

    skill_id: str
    agent: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    safety_boundary: str


AGENT_SKILLS: tuple[AgentSkill, ...] = (
    AgentSkill(
        skill_id="observe_system_and_workspace",
        agent="Monitor Agent",
        purpose="Collect local CPU, RAM, disk, process, and selected-folder scan signals.",
        inputs=("selected folder", "large-file threshold"),
        outputs=("Observation", "workspace profile", "process links"),
        safety_boundary="Read-only observation; no file movement or process changes.",
    ),
    AgentSkill(
        skill_id="diagnose_pressure_and_recovery",
        agent="Diagnosis Agent",
        purpose="Turn redacted aggregate scan data into structured diagnosis fields.",
        inputs=("Observation", "scan delta"),
        outputs=("summary", "top risks", "recommended scenario", "urgency", "confidence"),
        safety_boundary="May explain and recommend, but cannot execute filesystem actions.",
    ),
    AgentSkill(
        skill_id="plan_reversible_cleanup",
        agent="Maintenance Planner Agent",
        purpose="Create advisory actions, cleanup candidates, rebuildability evidence, and recovery recipes.",
        inputs=("Observation", "diagnosis summary"),
        outputs=("MaintenancePlan", "cleanup actions", "advisory actions"),
        safety_boundary="Plans are dry-run proposals until the user approves action ids.",
    ),
    AgentSkill(
        skill_id="validate_safety",
        agent="Risk & Safety Agent",
        purpose="Apply deterministic path, symlink, active-process, and risk rules before execution.",
        inputs=("MaintenancePlan",),
        outputs=("validated plan", "blocked actions"),
        safety_boundary="Hard-coded rules override LLM output and user-submitted client data.",
    ),
    AgentSkill(
        skill_id="report_and_learn",
        agent="Report Agent",
        purpose="Summarize before/after state, audit activity, quarantine results, and restore feedback.",
        inputs=("metrics", "plan", "quarantine records"),
        outputs=("report", "audit summary", "recovery recipes"),
        safety_boundary="Reporting is read-only; restore feedback only changes future confidence scoring.",
    ),
)


AGENT_SKILL_CHAIN: tuple[str, ...] = tuple(skill.skill_id for skill in AGENT_SKILLS)
