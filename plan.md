# OSPilot 2-Week Execution Plan

## Summary

Build a polished MVP of **OSPilot**, a local-first AI system health agent for the Kaggle AI Agents capstone. The MVP will run on **macOS first**, use **Groq + deterministic fallback**, and assume **3-4 hours/day for 14 days**.

The finished project must include a working Streamlit app, restricted MCP-style local tools, multi-agent orchestration, system/performance diagnosis, selected-folder scanning, developer junk detection, human approval, quarantine/restore, audit logs, tests, README, docs, demo workspace, Kaggle writeup, and a 5-minute video.

Core demo story:

```text
Observe system health -> detect RAM/process pressure -> scan selected folder -> diagnose issues -> create maintenance plan -> validate safety -> user approves cleanup -> quarantine files -> generate report -> restore one item
```

## Key Implementation Plan

### Foundation and Architecture

- Create project structure under the workspace:
  - `app.py`
  - `requirements.txt`
  - `.env.example`
  - `README.md`
  - `agents/`
  - `mcp_server/`
  - `core/`
  - `ui/`
  - `demo/`
  - `tests/`
  - `docs/`
- Use Python, Streamlit, `psutil`, Pydantic, SQLite, `python-dotenv`, and Groq SDK/client.
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
  - path, item type, size bytes, risk level, reason, recommended action.
- `MaintenanceAction`
  - action id, action mode, path, reason, size bytes, risk level, approved boolean.
- `MaintenancePlan`
  - diagnosis summary, performance recommendations, cleanup actions, blocked actions, estimated recoverable bytes.
- `QuarantineRecord`
  - id, original path, quarantine path, size bytes, reason, timestamp, restored boolean.
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
- Safety tools:
  - `is_protected_path(path)`
  - `classify_file_risk(path)`
  - `validate_cleanup_plan(plan)`
- Quarantine tools:
  - `quarantine_item(path, reason)`
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
  - Produces plain-language performance and storage diagnosis.
  - Falls back to deterministic template summaries.
- `maintenance_planner_agent.py`
  - Creates a structured `MaintenancePlan`.
  - Separates advisory performance recommendations from reversible cleanup actions.
- `risk_safety_agent.py`
  - Validates every action using hard-coded rules.
  - Blocks unsafe paths even if the LLM recommends them.
- `orchestrator_agent.py`
  - Runs the full observe -> diagnose -> plan -> validate -> approval -> execute/report loop.
- `report_agent.py`
  - Generates final before/after summary and audit-friendly report.

Groq usage:

- Use Groq for diagnosis and maintenance-plan wording.
- Do not rely on Groq for safety.
- If `GROQ_API_KEY` is missing or the API fails, use deterministic fallback and show "Demo/Fallback mode active" in the app.

### Streamlit App

Build Streamlit views:

- Dashboard:
  - CPU, RAM, disk, health score, pressure score.
  - Top CPU and memory processes.
  - Idle heavy app suggestions.
- Scan view:
  - Folder picker text input.
  - Demo workspace button.
  - Scan selected folder only.
- Diagnosis view:
  - Agent diagnosis summary.
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

### Demo, Docs, and Submission Assets

- `demo/create_demo_workspace.py`
  - Creates fake project folders:
    - `old_react_app/node_modules/`
    - `old_python_project/.venv/`
    - `notebooks/.ipynb_checkpoints/`
    - `package_build/dist/`
    - `package_build/build/`
    - `python_cache/__pycache__/`
    - `temp_logs/`
    - `large_files/`
  - Uses generated dummy files so judges can safely test.
- `docs/architecture.md`
  - Include multi-agent diagram and data flow.
- `docs/safety_model.md`
  - Explain no arbitrary shell, no permanent delete, selected-folder scanning, hard path blocks, approval, quarantine, restore.
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
  - Running demo mode
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

- Implement selected-folder scanner.
- Detect developer junk folders.
- Detect large files above threshold.
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
- Implement move-to-quarantine with metadata.
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
- Add Groq diagnosis/planning call.
- Add deterministic fallback.
- Acceptance: orchestrator produces a validated `MaintenancePlan` from metrics plus scan data.

### Day 8: Streamlit Dashboard

- Build main dashboard.
- Show metrics, health score, top processes, pressure score.
- Add selected-folder input and demo workspace trigger.
- Acceptance: user can open app and see live system metrics.

### Day 9: Scan, Diagnosis, and Plan UI

- Add scan results view.
- Add diagnosis summary view.
- Add maintenance plan view.
- Separate advisory recommendations from cleanup actions.
- Acceptance: scanning demo folder produces visible plan.

### Day 10: Approval, Quarantine, Restore UI

- Add approval queue.
- Add checkboxes for cleanup actions.
- Execute approved quarantine actions.
- Add quarantine list and restore button.
- Acceptance: demo folder item can be quarantined and restored from UI.

### Day 11: Demo Workspace and End-to-End Polish

- Finish demo workspace generator.
- Add reset demo workspace option.
- Add fallback sample data if live Groq fails.
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
  - quarantine preserves metadata.
  - restore returns file/folder to original path.
  - fallback mode works without Groq key.
- Manual app tests:
  - App starts with `streamlit run app.py`.
  - Dashboard shows metrics.
  - Demo workspace can be generated.
  - Selected-folder scan works.
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
- UI: Streamlit, not React, to maximize completion speed.
- Execution safety: quarantine only; no permanent delete.
- Process handling: advisory only; no automatic process killing.
- Scanning: selected-folder only; no default full-disk scan.
- Submission goal: Kaggle Concierge Agents track.
- First implementation task after leaving Plan Mode: create `plan.md` with this plan, then scaffold the project.
