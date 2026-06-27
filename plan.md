# OS Pilot 2-Week Execution Plan

## Summary

Build a polished MVP of **OS Pilot**, a local-first AI system health agent for the Kaggle AI Agents capstone. The MVP will run on **macOS first**, use **Groq + deterministic fallback**, and assume **3-4 hours/day for 14 days**.

The finished project must include a working JavaScript UI (React + Vite), FastAPI backend, restricted MCP-style local tools, multi-agent orchestration, structured system/performance diagnosis, selected-folder scanning, Home Scan through the user-owned home area, developer junk detection, project type detection, rebuildability scoring, recovery recipes, scan-delta memory, restore feedback learning, Safe Autopilot automation, human approval, quarantine/restore, audit logs, tests, README, docs, Kaggle writeup, and a 5-minute video.

Core demo story:

```text
Observe system health -> detect RAM/process pressure -> scan a selected folder or Home Scan scope -> compare with previous snapshot -> diagnose issues with structured output -> create maintenance plan -> validate safety -> user approves cleanup -> revalidate path identity/live processes -> quarantine files -> generate report -> restore one item -> record feedback
```

## Key Implementation Plan

### Foundation and Architecture

- Create project structure under the workspace:
  - `api/main.py`
  - `frontend/` (React + Vite + Tailwind)
  - `requirements.txt`
  - `.env.example`
  - `README.md`
  - `agents/`
  - `mcp_server/`
  - `core/`
  - `demo/`
  - `tests/`
  - `docs/`
- Use Python, FastAPI, `psutil`, Pydantic, SQLite, `python-dotenv`, and Groq SDK/client.
- Use JavaScript (React + Vite + Tailwind) for the UI — not Streamlit.
- OS Pilot runs on demand by default. Optional weekly scans can be enabled by the user through `launchd` on macOS or `cron` on Linux, and scheduled scans are report-only.
- Use `.env` for `GROQ_API_KEY`; never commit secrets.
- Add deterministic fallback mode for demo/tests when no Groq key is present.
- Treat the MCP server as a restricted local tool layer. It may be implemented as Python tool modules plus a thin server wrapper; no arbitrary shell execution.

### Core Data Models and Interfaces

Define Pydantic models in `core/models.py`:

- `SystemMetrics`
  - CPU percent, RAM percent, disk percent, available disk, timestamp.
- `ProcessInfo`
  - PID, name, CPU percent, memory MB, status, command preview.
- `ScanItem`
  - path, item type, size bytes, risk level, reason, recommended action, project root, project type, rebuildability, recovery recipe, evidence, path identity fields.
- `MaintenanceAction`
  - action id, action mode, path, reason, size bytes, risk level, approved boolean, project root, project type, rebuildability, recovery recipe, evidence, path identity fields.
- `MaintenancePlan`
  - diagnosis summary, structured diagnosis result, scan delta, performance recommendations, cleanup actions, blocked actions, estimated recoverable bytes.
- `QuarantineRecord`
  - id, original path, quarantine path, size bytes, reason, timestamp, restored boolean, artifact name, project type.
- `AuditEvent`
  - event type, payload JSON, timestamp.

Use fixed risk levels:

```text
Low
Medium
High
Needs Review
Blocked
```

Use fixed action modes:

```text
Advisory
Quarantine
Blocked
```

### Restricted Tool Layer

Implement restricted tools in `mcp_server/`:

- System tools:
  - `get_system_metrics()`
  - `get_process_snapshot(limit=20)`
  - `get_top_processes(metric="memory" | "cpu", limit=10)`
  - `analyze_performance_pressure()`
  - `detect_idle_heavy_apps()`
  - `get_disk_usage()`
- File scan tools:
  - `scan_selected_folder(root_path, min_size_mb=100)`
  - `find_developer_junk(root_path)`
  - `scan_cache_folders(root_path)`
  - `estimate_cleanup_space(items)`
  - `detect_project_type(project_root)`
  - `detect_project_root(path)`
  - `rebuildability_for(path, project_root, item_type)`
- Safety tools:
  - `is_protected_path(path)`
  - `classify_file_risk(path)`
  - `validate_cleanup_plan(plan)`
- Quarantine tools:
  - `quarantine_item(path, reason, expected_identity, artifact_name, project_type)`
  - `restore_item(quarantine_id)`
  - `list_quarantine()`
- Reporting tools:
  - `write_audit_log(event)`
  - `generate_maintenance_report()`

Hard-block these behaviors:

```text
run_any_command
delete_any_file
format_disk
edit_registry
kill_process
install_update
modify_system_settings
scan_full_disk_by_default
```

Protected macOS paths:

```text
/System
/Library
/bin
/sbin
/usr
/Applications
/private
```

Protected Windows paths for future compatibility:

```text
C:\Windows
C:\Program Files
C:\Program Files (x86)
```

### Agent Layer

Implement agents in `agents/`:

- `monitor_agent.py`
  - Calls system and file scan tools.
  - Produces structured observations.
- `diagnosis_agent.py`
  - Uses Groq when available.
  - Produces structured performance and storage diagnosis: summary, top risks, recommended scenario, urgency, confidence, and fallback flag.
  - Falls back to deterministic template summaries.
- `maintenance_planner_agent.py`
  - Creates a structured `MaintenancePlan`.
  - Separates advisory performance recommendations from reversible cleanup actions.
  - Prioritizes rebuildable project artifacts and includes recovery recipes.
  - Marks stale, rebuildable, manifest-backed artifacts as Safe Autopilot eligible.
- `risk_safety_agent.py`
  - Validates every action using hard-coded rules.
  - Blocks unsafe paths even if the LLM recommends them.
- `orchestrator_agent.py`
  - Runs the full observe -> diagnose -> plan -> validate -> approval -> execute/report loop.
- `report_agent.py`
  - Generates final before/after summary and audit-friendly report.

Groq usage:

- Use Groq for structured diagnosis wording.
- Do not rely on Groq for safety.
- Use redacted, aggregated observations rather than raw full paths or process command lines.
- If `GROQ_API_KEY` is missing or the API fails, use deterministic fallback and show "Demo/Fallback mode active" in the app.

### JavaScript UI + FastAPI Backend

Build the frontend in `frontend/` and expose agent actions through `api/main.py`:

- Dashboard:
  - CPU, RAM, disk, health score, pressure score, recoverable storage estimate.
  - Top CPU and memory processes.
  - Idle heavy app suggestions.
- Scan view:
  - Folder picker input.
  - Scan Folder action.
  - Home Scan action that targets the user-owned home area while protected OS paths remain blocked.
- Diagnosis view:
  - Structured agent diagnosis summary, top risks, urgency, confidence, scan delta, and recommended scenario.
  - Main storage and performance issues.
- Approval queue:
  - List cleanup actions with path, size, reason, risk.
  - Allow selecting individual items for quarantine.
  - Show advisory actions separately from cleanup actions.
- Quarantine view:
  - List quarantined items.
  - Restore selected item.
- Report view:
  - Before/after metrics.
  - Recovered storage.
  - Safety blocks.
  - Audit log summary.

Important UI rule:

- No automatic destructive action.
- The app must clearly separate "Advice" from "Approved cleanup".
- Quarantine, not delete.
- No cleanup happens from a background scheduler. Users explicitly start cleanup sessions, and optional weekly scans are report-only.

### Docs and Submission Assets

- Real-data demo flow:
  - Select a real folder or use Home Scan.
  - Show empty states before any scan data exists.
  - Keep protected paths blocked and cleanup approval explicit.
- `docs/architecture.md`
  - Include multi-agent diagram and data flow.
- `docs/safety_model.md`
  - Explain no arbitrary shell, no permanent delete, selected-folder scanning, Home Scan, hard path blocks, path identity revalidation, approval, quarantine, restore, and feedback learning.
- `docs/mcp_tools.md`
  - List every exposed tool and blocked behavior.
- `docs/demo_script.md`
  - Exact 5-minute video script.
- README must include:
  - Problem
  - Solution
  - Architecture
  - Setup
  - `.env` usage
  - Backend and frontend run commands
  - Real folder and Home Scan behavior
  - Safety guarantees
  - Screenshots/GIF placeholders
  - Kaggle writeup link placeholder
  - YouTube link placeholder

## 14-Day Schedule

### Day 1: Project Setup and Skeleton

- Create repository structure.
- Add `requirements.txt`, `.env.example`, basic `README.md`.
- Add Pydantic models.
- Add config loader for Groq key and fallback mode.
- Acceptance: app imports cleanly and models validate sample data.

### Day 2: System Metrics Tools

- Implement CPU/RAM/disk metrics with `psutil`.
- Implement process snapshot and top process sorting.
- Implement performance pressure scoring.
- Acceptance: command/script can print metrics and top processes without crashing.

### Day 3: File Scanner and Developer Junk Detector

- Implement selected-folder scanner and Home Scan scope.
- Detect developer junk folders.
- Detect large files above threshold.
- Detect project type and manifest/lockfile evidence.
- Generate rebuildability score and recovery recipe.
- Require nearby project evidence before treating broad build/cache names as high-confidence rebuildable cleanup.
- Estimate recoverable space.
- Acceptance: scanner finds expected junk in a local test folder.

### Day 4: Safety Rules

- Implement protected path blacklist.
- Implement risk classification.
- Implement maintenance plan validation.
- Ensure full-disk/system folders are blocked.
- Acceptance: tests prove protected paths cannot be quarantined.

### Day 5: Quarantine and Restore

- Implement SQLite quarantine database.
- Implement move-to-quarantine with metadata and execution-time identity checks.
- Implement restore by quarantine id.
- Implement list quarantine.
- Acceptance: item can be quarantined and restored to original path.

### Day 6: Audit Logging and Reports

- Implement SQLite audit events.
- Log scans, plans, approvals, quarantine, restore, blocked actions, and errors.
- Generate maintenance report.
- Acceptance: report includes recovered space, advisory actions, cleanup actions, safety blocks, and restore status.

### Day 7: Agent Orchestration

- Implement monitor, diagnosis, planner, safety, execution, and report agents.
- Add Groq structured diagnosis call with deterministic fallback.
- Add deterministic fallback.
- Acceptance: orchestrator produces a validated `MaintenancePlan` from metrics plus scan data.

### Day 8: FastAPI Backend

- Add REST endpoints for health, scan, scan progress, quarantine, restore, scheduler status, reports, and audit.
- Acceptance: frontend can call `/api/scan` and receive a validated plan.

### Day 9: JavaScript Dashboard

- Build React UI with Vite and Tailwind.
- Show metrics, health score, top processes, pressure score, recoverable storage.
- Add selected-folder input and Home Scan trigger.
- Acceptance: user can open the UI and see live system metrics.

### Day 10: Scan, Diagnosis, and Plan UI

- Add scan results, diagnosis, and maintenance plan views in the frontend.
- Separate advisory recommendations from cleanup actions.
- Acceptance: scanning demo folder produces visible plan.

### Day 11: Approval, Quarantine, Restore UI

- Add approval queue with checkboxes.
- Execute approved quarantine actions through the API.
- Add quarantine list and restore button.
- Acceptance: demo folder item can be quarantined and restored from UI.

### Day 11: End-to-End Polish

- Polish the real-data scan flow.
- Verify empty states do not show fake/demo data.
- Add deterministic fallback structured diagnosis if live Groq fails.
- Polish copy and labels.
- Acceptance: full demo flow works on macOS without touching system folders.

### Day 12: Tests and Safety Verification

- Add tests:
  - safety rules
  - protected path blocking
  - developer junk detection
  - cleanup plan validation
  - quarantine/restore
  - fallback mode
- Run tests and fix failures.
- Acceptance: core tests pass and no unsafe action path exists.

### Day 13: Documentation and Kaggle Assets

- Finish README.
- Finish `docs/architecture.md`, `docs/safety_model.md`, `docs/mcp_tools.md`, `docs/demo_script.md`.
- Draft Kaggle writeup under 2,500 words using `Proposal.md`.
- Add architecture diagram image or Mermaid diagram.
- Acceptance: a new user can run demo from README.

### Day 14: Video, Final QA, and Submission Prep

- Record 5-minute demo video:
  - problem
  - why agents
  - architecture
  - safety
  - live demo
  - result
- Add screenshots/media.
- Final test from clean setup.
- Check no secrets are committed.
- Prepare public GitHub link, YouTube link, and Kaggle writeup.
- Acceptance: submission package is complete and reproducible.

## Test Plan

Run these before final submission:

- Unit tests:
  - `is_protected_path()` blocks system paths.
  - `validate_cleanup_plan()` rejects unsafe actions.
  - scanner detects all demo junk folders.
  - quarantine preserves artifact/project metadata.
  - path identity and live process checks run immediately before execution.
  - restore returns file/folder to original path.
  - fallback mode works without Groq key.
- Manual app tests:
  - Backend starts with `uvicorn api.main:app --reload`.
  - Frontend starts with `npm run dev` in `frontend/`.
  - Dashboard shows metrics.
  - Selected-folder scan works.
  - Home Scan maps to the user-owned home area and does not scan protected OS roots.
  - Agent plan is created.
  - Advisory actions are not executable.
  - Cleanup actions require approval.
  - Quarantine moves files.
  - Restore works.
  - Report shows before/after state.
- Safety tests:
  - Attempting to scan or quarantine protected macOS paths is blocked.
  - No arbitrary shell command path exists.
  - No permanent delete action exists in MVP.
  - No process-kill action exists in MVP.
- Submission tests:
  - README setup works from scratch.
  - `.env.example` exists.
  - No API keys are present in files.
  - Video under 5 minutes.
  - Kaggle writeup under 2,500 words.

## Assumptions and Defaults

- Build target: **macOS first**, with Windows protected-path definitions included but not deeply tested.
- Time budget: **3-4 hours/day for 14 days**.
- LLM: **Groq API key**, stored in `.env`.
- Fallback: deterministic diagnosis/planning so demos and tests work without live API access.
- UI: React + Vite + Tailwind with FastAPI backend, not Streamlit, to deliver a polished judge-facing demo.
- Scheduling: optional weekly report-only scan through `cron` or `launchd`; user approval is still required for cleanup.
- Execution safety: quarantine only; no automatic permanent delete; execution revalidates path identity, symlink status, and live process links.
- Process handling: advisory only; no automatic process killing.
- Scanning: selected-folder scan plus Home Scan through the user-owned home area; no unsafe raw full-disk scan.
- Submission goal: Kaggle Concierge Agents track.
- First implementation task after leaving Plan Mode: create `plan.md` with this plan, then scaffold the project.
