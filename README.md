# OSPilot

OSPilot is a local-first AI system health agent for the Kaggle AI Agents capstone. It helps students and developers understand laptop slowdowns, identify performance pressure, and safely recover wasted storage from old project folders and caches.

## Problem

Developer laptops often fill up with old `node_modules`, virtual environments, build artifacts, Python caches, notebook checkpoints, and large forgotten files. Heavy background apps can also create RAM pressure. Generic cleaner apps are risky because they often do not explain what they are doing.

## Solution

OSPilot observes local system metrics, scans only a user-selected folder, creates a maintenance plan, validates safety with hard-coded rules, waits for human approval, and moves approved cleanup items to quarantine instead of deleting them.

## Architecture

```text
Observe -> Diagnose -> Plan -> Validate Safety -> Human Approval -> Quarantine -> Audit -> Restore
```

Main pieces:

- Streamlit dashboard
- Restricted MCP-style Python tools
- Multi-agent orchestration
- Groq-backed diagnosis with deterministic fallback
- SQLite audit and quarantine database
- Demo workspace generator

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Optional Groq setup:

```text
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

If no Groq key is configured, OSPilot runs in deterministic fallback mode.

## Run

```bash
streamlit run app.py
```

In the app:

1. Click **Create demo workspace**.
2. Click **Run OSPilot scan**.
3. Review advisory recommendations and cleanup actions.
4. Approve selected cleanup items.
5. Quarantine approved items.
6. Restore an item from quarantine.
7. Review the report and audit events.

## Safety Guarantees

- No arbitrary shell access.
- No permanent delete in the MVP.
- No automatic process killing.
- No registry edits or OS repair.
- No default full-disk scan.
- Protected system paths are blocked.
- Cleanup requires human approval.
- Quarantined items can be restored.
- Every important action is logged.

## Project Docs

- [Architecture](docs/architecture.md)
- [Safety Model](docs/safety_model.md)
- [MCP Tools](docs/mcp_tools.md)
- [Demo Script](docs/demo_script.md)

## Kaggle Submission Links

- Kaggle writeup: TBD
- YouTube demo: TBD
- Screenshots/GIF: TBD
