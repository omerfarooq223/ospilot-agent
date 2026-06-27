# OS Pilot: Local-First AI System Health Agent

## 1. Project Summary

**OS Pilot** is a local-first AI developer workspace recovery agent that helps students, developers, and laptop users understand slowdowns, identify performance pressure, and safely recover wasted storage from rebuildable project artifacts.

The agent observes system health, analyzes CPU/RAM/process pressure, scans only user-approved folders, detects developer junk such as `node_modules`, `.venv`, `__pycache__`, `.pytest_cache`, `.next`, `.turbo`, Rust `target`, Java `.gradle`, `dist`, and `build`, identifies project type and manifest evidence, scores rebuildability, then creates a structured diagnosis and human-readable maintenance plan with recovery recipes. It never kills processes or deletes files directly. Approved cleanup items are moved into a quarantine folder with audit logs, scan-time identity checks, restore support, and feedback learning.

The project is designed for Kaggle's AI Agents capstone as a practical, safe, demo-friendly agent system that demonstrates:

* Multi-agent reasoning
* Restricted local MCP tools
* Human-in-the-loop approval
* Safety validation
* Audit logging
* Rebuildability-aware cleanup planning
* Structured diagnosis with top risks, urgency, confidence, and recommended scenario
* Local scan memory for growth/shrinkage deltas
* Safe Autopilot automation for stale rebuildable artifacts
* Rollback through quarantine
* A public, reproducible real-data demo flow

## 2. One-Line Pitch

**OS Pilot is a safe local AI maintenance agent that diagnoses laptop performance issues, understands developer workspaces, identifies rebuildable artifacts, and executes only approved quarantine actions through restricted MCP tools with rollback support.**

## 3. Problem Statement

Many laptops become slow or run out of storage because of accumulated junk files, old project dependencies, caches, logs, temporary files, forgotten development environments, and heavy background processes. Existing cleaner apps can find large folders, but they usually do not understand whether a developer artifact is rebuildable from `package-lock.json`, `requirements.txt`, `pyproject.toml`, notebooks, or other project evidence.

For students, developers, and AI/ML learners, this creates a repeated problem:

* Storage fills up unexpectedly.
* RAM or CPU usage becomes high without a clear explanation.
* Heavy background processes keep running while idle.
* Old project folders contain gigabytes of dependencies.
* Python virtual environments and notebook caches accumulate silently.
* Users cannot tell which artifacts are safely rebuildable.
* Users do not know what is safe to remove.
* Manual cleanup is tedious and risky.
* Normal scripts can scan files, but they do not explain tradeoffs or create safe plans.

OS Pilot solves this by combining real system data with agentic diagnosis, safety checks, human approval, and reversible execution.

## 4. Target Users

The hackathon MVP focuses on:

**Students and developers on macOS or Windows who want to understand laptop slowdowns, identify heavy background processes, and safely recover storage from old projects, caches, and temporary files without accidentally deleting important work.**

## 5. Recommended Track

**Concierge Agents**

OS Pilot is a personal assistant for device health and everyday productivity. It helps individuals maintain their own laptop safely, keeps users in control, and protects personal files through local-first execution.

## 6. Core Workflow

OS Pilot follows a controlled maintenance loop:

```text
Observe -> Diagnose -> Plan -> Validate Safety -> Human Approval -> Act or Advise -> Audit -> Restore if Needed
```

The agent cannot run arbitrary terminal commands. It communicates with a local MCP server that exposes only safe, purpose-built tools.

Example tools:

```text
get_system_metrics()
get_top_processes()
analyze_performance_pressure()
detect_idle_heavy_apps()
scan_selected_folder()
find_developer_junk()
classify_file_risk()
validate_cleanup_plan()
quarantine_item()
restore_item()
write_audit_log()
generate_maintenance_report()
```

This makes the project safer and more production-like than a normal script wrapped in an LLM.

## 7. Why Agents Are Needed

This is not only a file deletion problem. A plain script can list large folders, but it cannot easily explain context, compare risk, create alternative cleanup plans, or communicate tradeoffs clearly.

OS Pilot uses agents because the system must:

* Interpret raw system and storage data
* Explain why a machine appears unhealthy
* Connect RAM, CPU, process, and storage signals
* Distinguish between cleanup actions and non-destructive advice
* Separate safe cleanup from risky cleanup
* Understand developer-specific waste
* Detect project type and rebuildability
* Generate recovery recipes for quarantined artifacts
* Compare current scans against previous local snapshots
* Learn from restored items and become more cautious about similar future suggestions
* Create multiple cleanup plans
* Ask for approval before action
* Validate every action through hard-coded safety rules
* Produce a clear report after execution

The agent adds value by turning technical system data into an understandable, reversible maintenance plan.

## 8. MVP Scope

The MVP is focused so it can be completed, tested, documented, and demonstrated before the deadline.

### 8.1 Included in MVP

1. **System Health Dashboard**
   * CPU usage
   * RAM usage
   * Disk usage
   * Top memory-consuming processes
   * Top CPU-consuming processes
   * Performance pressure score
   * Recoverable storage estimate
   * Health score

2. **Performance Triage**
   * Detects high RAM usage.
   * Detects high CPU usage.
   * Identifies top resource-consuming apps.
   * Labels items as "Close manually", "Investigate", or "Normal".
   * Does not kill processes automatically.

3. **Idle Heavy App Detection**
   * Finds apps that are using significant memory while the system appears idle.
   * Gives non-destructive recommendations such as closing browser tabs, stopping Docker Desktop, or quitting inactive IDEs.
   * Keeps process actions advisory in the MVP.

4. **Startup and Background Item Review**
   * Shows common startup/background items in read-only mode where available.
   * Explains which items may contribute to slower boot or background load.
   * Does not disable startup items automatically in the MVP.

5. **User-Selected Folder Scan**
   * The app scans only folders selected by the user.
   * No full-drive scan by default.
   * Demo mode creates a safe synthetic folder for judging.

6. **Developer Junk Detector**
   * `node_modules`
   * `.venv`
   * `venv`
   * `__pycache__`
   * `.pytest_cache`
   * `.mypy_cache`
   * `.ipynb_checkpoints`
   * `.next`
   * `dist`
   * `build`
   * `.cache`

7. **Workspace Intelligence**
   * Detects Node, Next.js, Python, Jupyter, and ML-style projects.
   * Uses evidence such as `package-lock.json`, `requirements.txt`, `pyproject.toml`, and notebooks.
   * Scores rebuildability: High, Medium, Low, Unknown, or Not Rebuildable.
   * Generates recovery recipes such as `npm ci` or `pip install -r requirements.txt`.

8. **Large File Scanner**
   * Finds large files above a configurable size.
   * Labels large files as "Needs Review" instead of auto-cleaning them.

9. **Maintenance Planner**
   * Creates a safe maintenance plan.
   * Explains each recommendation.
   * Estimates recoverable space.
   * Assigns risk levels: Low, Medium, High, Needs Review.
   * Separates reversible cleanup actions from advisory performance recommendations.
   * Prioritizes rebuildable project artifacts over unknown user files.

10. **Safety Validator**
   * Blocks protected system paths.
   * Blocks hidden or risky paths unless explicitly allowed.
   * Rejects unsafe actions before execution.
   * Prevents the LLM from overriding hard-coded safety rules.

11. **Human Approval Dashboard**
   * Shows proposed actions.
   * Allows approving or rejecting individual items.
   * Shows risk level, reason, and estimated recovered space.

12. **Quarantine and Restore**
   * Moves approved items to `~/.ospilot/quarantine/`.
   * Stores original path, size, timestamp, reason, and restore status in SQLite.
   * Supports one-click restore.

13. **Audit Logs**
   * Records scan results, agent decisions, approvals, quarantined files, restored files, blocked actions, and errors.

14. **Before/After Report**
   * Shows recovered space.
   * Shows health score change.
   * Shows RAM/CPU pressure summary.
   * Shows what was moved.
   * Shows rollback availability.

15. **Safe Autopilot**
   * Automatically identifies stale, rebuildable, manifest-backed artifacts.
   * Lets the user trigger backend-governed quarantine for only those items.
   * Never lets the browser submit arbitrary files as Autopilot candidates.
   * Keeps permanent delete, process killing, and updates out of automation.

### 8.2 Explicitly Not in MVP

To keep the project safe and achievable, the hackathon version will not include:

* Automatic permanent deletion
* Automatic process killing
* Automatic software update installation
* Automatic malware removal
* Registry editing
* Antivirus claims
* Deep system repair
* Silent update installation
* Full background daemon with admin privileges (no `cron` or `launchd` in MVP — OS Pilot runs on demand when you open the app)
* Full-drive scanning by default
* Editing system folders
* Running arbitrary shell commands

## 9. Demo Scenario

The demo will use a generated safe folder that simulates a cluttered developer laptop.

Demo flow:

```text
1. User opens OS Pilot dashboard.
2. OS Pilot shows CPU, RAM, disk, and process metrics.
3. OS Pilot flags high memory pressure and heavy idle apps.
4. User selects a real folder or chooses Home Scan for the user-owned home scope.
5. MCP scan tools detect recoverable storage.
6. Diagnosis agent returns structured output explaining performance, storage pressure, top risks, urgency, recommended scenario, and confidence.
7. Maintenance planner creates a safe plan.
8. Safety validator blocks risky paths.
9. User approves selected cleanup items.
10. Execution revalidates path identity and live process links, then moves approved items to quarantine.
11. Report shows recovered space, performance advice, and restore option.
12. User restores one item to prove rollback works.
```

Example output:

```text
System Health Score: 62/100
RAM Pressure: High
Top Heavy App: Docker Desktop using 2.4 GB while idle
Recoverable Storage Found: 13.8 GB

Main Issues:
- Memory pressure is high
- Docker Desktop appears idle but is using significant RAM
- 5 rebuildable node_modules folders found with package lockfiles
- 3 Python virtual environments found with requirements files
- 912 MB Python cache found
- 1.4 GB build artifacts found

Maintenance Plan:
- Recommendation: Stop Docker Desktop manually if containers are not needed
- Recommendation: Close unused browser tabs
- Quarantine old node_modules folders; recovery: npm ci
- Quarantine unused .venv folders; recovery: python -m venv .venv && pip install -r requirements.txt
- Quarantine __pycache__ folders

Recovered Space: 12.6 GB
Rollback: Available
Audit Log: Saved
```

This creates a clear before/after moment for the required video.

## 10. Multi-Agent Architecture

```text
User-Selected Folder + System Metrics + Process Snapshot
        |
        v
System Monitor Agent
        |
        v
Diagnosis Agent
        |
        v
Maintenance Planner Agent
        |
        v
Risk & Safety Agent
        |
        v
Human Approval Gate
        |
        v
Restricted MCP Tool Server
        |
        v
Advice + Quarantine + Audit Log + Report
```

### 10.1 System Monitor Agent

Collects CPU, RAM, disk, top processes, idle heavy apps, selected-folder or Home Scan results, developer junk scan results, project type, manifest evidence, filesystem identity, and rebuildability. It only observes and does not perform cleanup.

### 10.2 Diagnosis Agent

Turns aggregated local observations and previous-scan deltas into structured AI output: summary, top risks, recommended scenario, urgency level, and confidence. When Groq is unavailable, it returns deterministic fallback fields with the same shape.

Example:

```text
Your system has high memory pressure and low available storage. Docker Desktop and browser processes are using significant RAM, while most recoverable storage appears to come from old development dependencies and Python virtual environments inside the selected workspace.
```

### 10.3 Maintenance Planner Agent

Creates a structured maintenance plan with item path, item type, project type, rebuildability, evidence, recovery recipe, risk level, recommended action, and action mode: advisory or quarantine. The safety layer validates this plan before execution.

### 10.4 Risk & Safety Agent

Applies deterministic safety rules with final authority. The LLM can explain and recommend, but it cannot override protected-path checks, symlink blocking, active-process blocking, browser-plan distrust, or execution-time path identity validation.

Blocked paths include:

macOS:

```text
/System
/Library
/bin
/sbin
/usr
/Applications
/private
```

Windows:

```text
C:\Windows
C:\Program Files
C:\Program Files (x86)
C:\Users\<user>\AppData\System-protected paths
```

The LLM cannot override these restrictions.

### 10.5 Execution Agent

Executes only approved cleanup actions through MCP tools. It cannot run arbitrary commands, cannot permanently delete files by default, and does not kill processes in the MVP.

### 10.6 Report Agent

Generates the health summary, performance summary, cleanup summary, before/after metrics, quarantine report, restore status, safety blocks, and suggested next steps.

## 11. Secure MCP Server Design

The local MCP server exposes narrow tools instead of unrestricted shell access.

### 11.1 System Tools

```text
get_system_metrics()
get_process_snapshot()
get_top_processes(metric="memory" | "cpu", limit=10)
analyze_performance_pressure()
detect_idle_heavy_apps()
get_disk_usage()
```

### 11.2 File Scan Tools

```text
scan_selected_folder(root_path, min_size_mb)
find_developer_junk(root_path)
scan_cache_folders(root_path)
estimate_cleanup_space(items)
detect_project_type(project_root)
rebuildability_for(path, project_root, item_type)
```

### 11.3 Safety Tools

```text
classify_file_risk(path)
is_protected_path(path)
validate_cleanup_plan(plan)
```

### 11.4 Quarantine Tools

```text
quarantine_item(path, reason, expected_identity, artifact_name, project_type)
restore_item(quarantine_id)
list_quarantine()
empty_quarantine_after_retention(days)
```

### 11.5 Reporting Tools

```text
write_audit_log(event)
generate_health_report()
generate_maintenance_report()
```

### 11.6 Tools Not Allowed

```text
run_any_command(command)
delete_any_file(path)
format_disk()
edit_registry_freely()
kill_any_process_without_approval()
install_update_silently()
modify_system_settings_without_approval()
```

## 12. Safety Model

OS Pilot's safety model is central to the project.

1. **No arbitrary shell access**
   * The agent can only call approved MCP tools.

2. **No permanent delete by default**
   * Files are moved to quarantine.

3. **Human approval required**
   * Cleanup actions require explicit approval.

4. **Protected path blacklist**
   * System-critical paths are blocked at the tool layer.

5. **Selected-folder scanning**
   * The MVP does not scan the full disk by default.

6. **Audit logging**
   * Every decision and action is recorded.

7. **Rollback support**
   * Quarantined files can be restored.

8. **Demo mode**
   * Judges can test safely without touching personal files.

## 13. Tech Stack

* Backend: Python, FastAPI, `psutil`, `pathlib`, `shutil`, `sqlite3`, and Pydantic models.
* Agent layer: Groq-backed structured diagnosis with deterministic fallback and structured outputs.
* MCP layer: local restricted parameterized tools with no open shell access.
* Frontend: JavaScript (React + Vite + Tailwind) dashboard for health, performance triage, scan results, approvals, quarantine, and reports.
* Storage: SQLite for audit, quarantine metadata, scan snapshots, restore feedback, and local filesystem quarantine.
* Scheduling: optional report-only weekly scans; cleanup remains interactive and approval-gated.

## 14. Suggested Repository Structure

```text
ospilot/
├── README.md
├── requirements.txt
├── .env.example
├── config.py
│
├── api/
│   └── main.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       └── components/
│
├── agents/
│   ├── orchestrator_agent.py
│   ├── monitor_agent.py
│   ├── diagnosis_agent.py
│   ├── maintenance_planner_agent.py
│   ├── risk_safety_agent.py
│   └── report_agent.py
│
├── mcp_server/
│   ├── server.py
│   ├── tools_system.py
│   ├── tools_files.py
│   ├── tools_quarantine.py
│   └── safety_rules.py
│
├── core/
│   ├── models.py
│   ├── scoring.py
│   ├── audit_log.py
│   ├── quarantine_db.py
│   └── scanner.py
│
├── demo/
│   ├── create_demo_workspace.py
│   └── sample_scan_results.json
│
├── tests/
│   ├── test_safety_rules.py
│   ├── test_quarantine_restore.py
│   └── test_cleanup_plan_validation.py
│
└── docs/
    ├── architecture.md
    ├── safety_model.md
    ├── mcp_tools.md
    └── demo_script.md
```

## 15. Success Metrics

OS Pilot can demonstrate success through:

* Recoverable storage found
* RAM/CPU pressure explained
* Heavy processes identified
* Storage safely quarantined
* Number of developer junk folders detected
* Number of rebuildable artifacts detected
* Recovery recipes generated
* Number of unsafe actions blocked
* Successful restore from quarantine
* Audit log completeness

## 16. Risks and Mitigations

### Risk 1: Accidental File Deletion

* Use quarantine instead of permanent delete.
* Maintain SQLite restore metadata.
* Require explicit approval.

### Risk 2: Unsafe LLM Recommendation

* Validate all plans with hard-coded safety rules.
* Reject protected paths at the MCP tool layer.
* Use structured JSON plans instead of free-form commands.

### Risk 3: Cross-Platform Complexity

* Keep MVP features mostly cross-platform through Python and `psutil`.
* Avoid platform-specific repair tools in the hackathon build.
* Treat Windows/macOS repair checks as future work.

### Risk 4: Judge Machine Safety

* Prefer real local data and clear empty states over fake UI data.
* Require user-scoped scanning and protected-path blocking.
* Provide dry-run output before quarantine.

### Risk 5: Scope Creep

* Build the performance diagnosis, storage diagnosis, planning, quarantine, restore, and audit loop first.
* Add optional features only after the core flow is stable.

## 17. Hackathon Deliverables

The final submission should include:

1. Public GitHub repository
2. README with setup instructions
3. Architecture diagram
4. JavaScript demo app (React) with FastAPI backend
5. Local MCP server code
6. Multi-agent orchestration code
7. Safety model documentation
8. Real-data scan flow with safe empty states
9. Tests for safety rules and quarantine restore
10. YouTube video under 5 minutes
11. Kaggle Writeup under 2,500 words

## 18. Suggested Video Story

The video should stay focused and practical:

1. **Problem**
   * "Developer laptops slow down and fill up because of heavy background apps, old dependencies, caches, and virtual environments. Normal cleaners find junk; OS Pilot understands which artifacts are rebuildable."

2. **Why Agents**
   * "A script can list files or processes, but an agent can connect system pressure, project manifests, rebuildability, scan history, recovery recipes, safety validation, and reporting."

3. **Architecture**
   * Show multi-agent flow and restricted MCP server.

4. **Safety**
   * Explain no arbitrary shell, no permanent delete, human approval, quarantine, restore, audit logs.

5. **Demo**
   * Select a real folder or use Home Scan.
   * Show RAM/process pressure.
   * Scan Folder.
   * Show structured diagnosis, scan delta, workspace intelligence, rebuildability, and maintenance plan.
   * Approve actions.
   * Quarantine files.
   * Restore one file.
   * Show final report.

6. **Result**
   * "Recovered storage without losing control or deleting files blindly."

## 19. Future Work

After the MVP, OS Pilot could add duplicate file review, optional update awareness, startup item controls, verify-only system repair checks, optional scheduled scans via `cron` or `launchd` (with explicit user opt-in), desktop packaging, advanced scoring, and classroom/lab maintenance mode.

## 20. Final Product Statement

OS Pilot is not a cleaner app with AI branding. It is a safe, local-first developer workspace recovery agent that observes laptop health, diagnoses performance and storage issues with structured AI output, understands project context, remembers previous scan snapshots, identifies rebuildable artifacts, recommends non-destructive performance fixes, plans reversible cleanup actions with recovery recipes, validates safety through restricted MCP tools, waits for human approval, quarantines files instead of deleting them, learns from restores, and records the full outcome.

The project is worth building because it is practical, visible in a short demo, technically aligned with the Kaggle agent rubric, and grounded in a strong safety story.
