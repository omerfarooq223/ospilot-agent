# Course Concepts Demonstrated

This project demonstrates the main agent-system concepts used by OS Pilot.

| Concept | Demonstrated in | Evidence |
| --- | --- | --- |
| Agent / multi-agent system | Code | `agents/orchestrator_agent.py` coordinates Monitor, Diagnosis, Maintenance Planner, Risk & Safety, and Report agents. `agents/skills.py` names the agent skills and the pipeline records the skill chain in audit metadata. |
| MCP server / restricted tool layer | Code | `mcp_server/server.py` exposes a narrow allowlist of local tools. The agent can call scan, profile, validation, quarantine, restore, and report tools, but cannot call arbitrary shell commands. |
| Antigravity | Development workflow | The backend and frontend can be launched from Antigravity's terminal using the README commands. |
| Security features | Code | Protected path blocking, symlink blocking, server-side scan sessions, execution-time filesystem identity revalidation, active-process blocks, quarantine instead of deletion, restore support, and audit logs. |
| Deployability | Docs | `README.md` explains local setup. `docs/desktop_app.md` documents the Tauri desktop shell and build path. |
| Agent skills | Code | `agents/skills.py` defines role-specific skills for observation, diagnosis, planning, safety validation, and reporting. |

## ADK Note

OS Pilot uses an explicit Python multi-agent architecture rather than depending on a hosted runtime for local filesystem control. The code separates agent roles, structured state, deterministic tools, and safety gates in an ADK-style layout while keeping all file actions behind the restricted local tool layer. This keeps the app reproducible locally without requiring cloud deployment or secret credentials.

## Security Evidence Checklist

- Server-side scan sessions are required for cleanup execution.
- Browser-submitted cleanup plans are ignored.
- Safe Autopilot chooses candidates from backend policy only.
- Protected OS paths are blocked.
- Symlinks are blocked.
- Path device, inode, and mtime are rechecked at execution time.
- Active project-linked processes block quarantine.
- Approved items move to quarantine rather than permanent deletion.
- Restore events are recorded as feedback for future confidence scoring.
