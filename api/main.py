from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.orchestrator_agent import build_plan, execute_approved_actions, run_report
from config import fallback_mode_enabled
from core.audit_log import list_audit_events
from core.models import DiagnosisResult, MaintenancePlan, Observation, QuarantineRecord
from core.audit_log import write_audit_log
from core.feedback_store import record_restore
from core.quarantine_db import list_quarantine, permanently_delete_item, restore_item
from core.scan_history_db import get_last_snapshot, save_scan_snapshot
from core.scheduler import install_scheduler, scheduler_status, uninstall_scheduler
from core.scheduler_config import SchedulerConfig, load_scheduler_config, save_scheduler_config
from core.scoring import format_bytes
from core.user_preferences import (
    add_ignored_folder,
    append_scan_history,
    is_ignored,
    list_ignored_folders,
    remove_ignored_folder,
    scan_history,
)
from core.weekly_report import list_weekly_reports, run_weekly_scan
from mcp_server.safety_rules import is_protected_path


app = FastAPI(title="OSPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCAN_SESSION_TTL = timedelta(hours=2)
SCAN_SESSIONS: dict[str, dict[str, object]] = {}
SCAN_JOBS: dict[str, dict[str, object]] = {}


def clean_path_input(path: str) -> str:
    cleaned = path.strip()
    if cleaned.startswith("file://"):
        parsed = urlparse(cleaned)
        cleaned = unquote(parsed.path)
    cleaned = cleaned.strip().rstrip(",;")
    while len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        cleaned = cleaned[1:-1].strip().rstrip(",;")
    return cleaned


def resolve_user_path(path: str) -> Path:
    return Path(clean_path_input(path)).expanduser().resolve()


def prune_scan_sessions() -> None:
    now = datetime.now(timezone.utc)
    expired = [
        session_id
        for session_id, session in SCAN_SESSIONS.items()
        if now - session["created_at"] > SCAN_SESSION_TTL  # type: ignore[operator]
    ]
    for session_id in expired:
        SCAN_SESSIONS.pop(session_id, None)


def major_folder_locations() -> list[Path]:
    home = Path.home().resolve()
    candidates = [
        home,
        home / "Desktop",
        home / "Documents",
        home / "Downloads",
        home / "Applications",
        Path("/Applications"),
        Path("/Volumes"),
    ]
    return [item.resolve() for item in candidates if item.exists() and item.is_dir() and not is_protected_path(item)]


def folder_entry(path: Path) -> "FolderEntry":
    return FolderEntry(name=path.name or str(path), path=str(path), is_ignored=is_ignored(path))


def validate_scan_folder(raw_folder: str) -> Path:
    folder = clean_path_input(raw_folder)
    if not folder:
        raise HTTPException(status_code=400, detail="Folder path is required.")
    path = resolve_user_path(folder)
    if not path.exists():
        raise HTTPException(status_code=400, detail="That folder does not exist.")
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Choose a folder, not a file.")
    if is_ignored(path):
        raise HTTPException(status_code=400, detail="This folder is on your ignore list.")
    return path


def build_scan_result(path: Path, min_size_mb: int) -> "ScanResponse":
    prev_snapshot = get_last_snapshot(str(path))
    observation, plan, diagnosis_result = build_plan(path, min_size_mb=min_size_mb, previous_snapshot=prev_snapshot)

    save_scan_snapshot(str(path), observation, plan)

    session_id = uuid4().hex
    prune_scan_sessions()
    SCAN_SESSIONS[session_id] = {
        "created_at": datetime.now(timezone.utc),
        "folder": str(path),
        "observation": observation,
        "plan": plan,
    }
    append_scan_history(
        {
            "folder": str(path),
            "recoverable_bytes": plan.estimated_recoverable_bytes,
            "recoverable_label": format_bytes(plan.estimated_recoverable_bytes),
            "automation_candidate_bytes": sum(action.size_bytes for action in plan.cleanup_actions if action.automation_eligible),
            "automation_candidate_count": sum(1 for action in plan.cleanup_actions if action.automation_eligible),
            "cleanup_actions": len(plan.cleanup_actions),
            "advisory_actions": len(plan.performance_recommendations),
            "blocked_actions": len(plan.blocked_actions),
            "rebuildable_artifacts": sum(
                1
                for action in [*plan.cleanup_actions, *plan.performance_recommendations, *plan.blocked_actions]
                if action.rebuildability.value in {"High", "Medium"}
            ),
            "project_types": sorted(
                {
                    action.project_type
                    for action in [*plan.cleanup_actions, *plan.performance_recommendations, *plan.blocked_actions]
                    if action.project_type != "Unknown"
                }
            ),
            "disk_percent": observation.metrics.disk_percent,
            "available_disk_bytes": observation.metrics.available_disk_bytes,
            "available_disk_label": format_bytes(observation.metrics.available_disk_bytes),
        }
    )
    return ScanResponse(session_id=session_id, folder=str(path), observation=observation, plan=plan, fallback=diagnosis_result.used_fallback)


def run_scan_job(job_id: str, path: Path, min_size_mb: int) -> None:
    job = SCAN_JOBS[job_id]
    if job.get("status") == "cancelled":
        return
    job.update({"status": "running", "progress": 35, "message": "Reading folder contents..."})
    try:
        result = build_scan_result(path, min_size_mb)
        if job.get("status") == "cancelled":
            return
        job.update(
            {
                "status": "completed",
                "progress": 100,
                "message": "Scan complete.",
                "session_id": result.session_id,
                "observation": result.observation,
                "plan": result.plan,
                "fallback": result.fallback,
            }
        )
    except Exception as exc:  # pragma: no cover - surfaced through API
        job.update({"status": "failed", "progress": 100, "message": "Scan failed.", "error": str(exc)})


class ScanRequest(BaseModel):
    folder: str
    min_size_mb: int = Field(default=30, ge=30, le=5000)


class ScanResponse(BaseModel):
    session_id: str
    folder: str
    observation: Observation
    plan: MaintenancePlan
    fallback: bool


class ScanStartResponse(BaseModel):
    job_id: str


class ScanJobResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    session_id: str | None = None
    observation: Observation | None = None
    plan: MaintenancePlan | None = None
    fallback: bool | None = None
    error: str | None = None


class QuarantineRequest(BaseModel):
    session_id: str | None = None
    observation: Observation | None = None
    plan: MaintenancePlan | None = None
    approved_action_ids: list[str] = Field(default_factory=list)


class QuarantineResponse(BaseModel):
    quarantined: list[QuarantineRecord]
    report: dict[str, object]


class AutopilotQuarantineRequest(BaseModel):
    session_id: str


class AutopilotQuarantineResponse(BaseModel):
    approved_action_ids: list[str]
    quarantined: list[QuarantineRecord]
    report: dict[str, object]


class RestoreResponse(BaseModel):
    record: QuarantineRecord


class FolderEntry(BaseModel):
    name: str
    path: str
    is_ignored: bool = False


class FolderBrowseResponse(BaseModel):
    current_path: str
    parent_path: str | None
    breadcrumbs: list[FolderEntry]
    quick_access: list[FolderEntry]
    children: list[FolderEntry]
    major_locations: list[FolderEntry]


class IgnoreFolderRequest(BaseModel):
    path: str


class ScanHistoryResponse(BaseModel):
    items: list[dict[str, object]]


class ReportExportRequest(BaseModel):
    report: dict[str, object]
    format: str = "html"


@app.get("/api/health")
def health() -> dict[str, object]:
    status = scheduler_status()
    return {
        "status": "ok",
        "fallback_mode": fallback_mode_enabled(),
        "ui": "javascript",
        "weekly_scan_enabled": status["enabled"],
        "scheduler_supported": status["supported"],
    }


@app.post("/api/report/export")
def export_report(body: ReportExportRequest) -> Response:
    generated = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    report = body.report or {}
    lines = [
        "<!doctype html><html><head><meta charset='utf-8'><title>OSPilot Report</title>",
        "<style>body{font-family:Inter,system-ui,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;line-height:1.6;background:#0d1420;color:#e2e8f0}h1,h2{color:#5eead4}.card{border:1px solid #334155;border-radius:12px;padding:16px;margin:12px 0;background:#111827}code{color:#67e8f9}</style>",
        "</head><body>",
        "<h1>OSPilot Scan Report</h1>",
        f"<p>Generated: {generated}</p>",
    ]
    for key, value in report.items():
        lines.append("<div class='card'>")
        lines.append(f"<h2>{escape(str(key).replace('_', ' ').title())}</h2>")
        lines.append(f"<pre>{escape(str(value))}</pre>")
        lines.append("</div>")
    lines.append("</body></html>")
    html = "\n".join(lines)
    if body.format == "html":
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": "attachment; filename=ospilot-report.html"},
        )
    if body.format == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        except ImportError as exc:
            raise HTTPException(status_code=500, detail="PDF export requires reportlab. Run pip install -r requirements.txt.") from exc

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, title="OSPilot Report")
        styles = getSampleStyleSheet()
        story = [
            Paragraph("OSPilot Scan Report", styles["Title"]),
            Paragraph(f"Generated: {generated}", styles["Normal"]),
            Spacer(1, 12),
        ]
        for key, value in report.items():
            story.append(Paragraph(escape(str(key).replace("_", " ").title()), styles["Heading2"]))
            story.append(Paragraph(escape(str(value)), styles["BodyText"]))
            story.append(Spacer(1, 8))
        doc.build(story)
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=ospilot-report.pdf"},
        )
    return Response(
        content="\n".join(str(item) for item in report.items()),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ospilot-report.txt"},
    )


@app.post("/api/scan", response_model=ScanResponse)
def scan(body: ScanRequest) -> ScanResponse:
    return build_scan_result(validate_scan_folder(body.folder), body.min_size_mb)


@app.post("/api/scan/start", response_model=ScanStartResponse)
def start_scan(body: ScanRequest, background_tasks: BackgroundTasks) -> ScanStartResponse:
    path = validate_scan_folder(body.folder)
    job_id = uuid4().hex
    SCAN_JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 10,
        "message": "Preparing scan...",
        "created_at": datetime.now(timezone.utc),
    }
    background_tasks.add_task(run_scan_job, job_id, path, body.min_size_mb)
    return ScanStartResponse(job_id=job_id)


@app.get("/api/scan/jobs/{job_id}", response_model=ScanJobResponse)
def get_scan_job(job_id: str) -> ScanJobResponse:
    job = SCAN_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown scan job.")
    return ScanJobResponse(**job)


@app.post("/api/scan/jobs/{job_id}/cancel")
def cancel_scan_job(job_id: str) -> dict[str, object]:
    job = SCAN_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown scan job.")
    if job.get("status") in {"completed", "failed"}:
        return {"job_id": job_id, "status": job["status"], "cancelled": False}
    job.update({"status": "cancelled", "progress": 100, "message": "Scan cancelled."})
    return {"job_id": job_id, "status": "cancelled", "cancelled": True}


@app.post("/api/quarantine", response_model=QuarantineResponse)
def quarantine(body: QuarantineRequest) -> QuarantineResponse:
    if not body.approved_action_ids:
        raise HTTPException(status_code=400, detail="Select at least one cleanup action.")
    prune_scan_sessions()
    if not body.session_id or body.session_id not in SCAN_SESSIONS:
        raise HTTPException(status_code=400, detail="Scan session expired. Run the scan again before quarantining.")
    session = SCAN_SESSIONS[body.session_id]
    observation = session["observation"]
    plan = session["plan"]
    if not isinstance(observation, Observation) or not isinstance(plan, MaintenancePlan):
        raise HTTPException(status_code=400, detail="Scan session could not be read. Run the scan again.")
    quarantined = execute_approved_actions(plan, body.approved_action_ids)
    report = run_report(observation, plan, quarantined)
    return QuarantineResponse(quarantined=quarantined, report=report)


@app.post("/api/autopilot/quarantine", response_model=AutopilotQuarantineResponse)
def autopilot_quarantine(body: AutopilotQuarantineRequest) -> AutopilotQuarantineResponse:
    prune_scan_sessions()
    if body.session_id not in SCAN_SESSIONS:
        raise HTTPException(status_code=400, detail="Scan session expired. Run the scan again before using Autopilot.")
    session = SCAN_SESSIONS[body.session_id]
    observation = session["observation"]
    plan = session["plan"]
    if not isinstance(observation, Observation) or not isinstance(plan, MaintenancePlan):
        raise HTTPException(status_code=400, detail="Scan session could not be read. Run the scan again.")

    approved_action_ids = [action.action_id for action in plan.cleanup_actions if action.automation_eligible]
    if not approved_action_ids:
        raise HTTPException(status_code=400, detail="No cleanup actions currently match the Safe Autopilot policy.")

    write_audit_log(
        "autopilot_quarantine_started",
        {
            "session_id": body.session_id,
            "approved_action_ids": approved_action_ids,
            "candidate_count": len(approved_action_ids),
        },
    )
    quarantined = execute_approved_actions(plan, approved_action_ids)
    report = run_report(observation, plan, quarantined)
    write_audit_log(
        "autopilot_quarantine_completed",
        {
            "session_id": body.session_id,
            "quarantined_count": len(quarantined),
            "quarantined_paths": [record.original_path for record in quarantined],
        },
    )
    return AutopilotQuarantineResponse(
        approved_action_ids=approved_action_ids,
        quarantined=quarantined,
        report=report,
    )


@app.get("/api/folders", response_model=FolderBrowseResponse)
def browse_folders(path: str | None = Query(default=None)) -> FolderBrowseResponse:
    requested = resolve_user_path(path) if path else Path.home().resolve()
    if not requested.exists() or not requested.is_dir():
        requested = Path.home().resolve()
    if is_protected_path(requested):
        raise HTTPException(status_code=400, detail="Protected system folders are not available for browsing.")

    major_locations = [folder_entry(item) for item in major_folder_locations()]
    quick_access = major_locations[:4]
    breadcrumbs = [
        folder_entry(item)
        for item in reversed([requested, *requested.parents])
        if item.exists() and item.is_dir() and not is_protected_path(item)
    ]

    children: list[FolderEntry] = []
    try:
        for child in sorted(requested.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir() and not child.name.startswith(".") and not is_protected_path(child):
                children.append(folder_entry(child))
    except OSError:
        children = []

    parent = requested.parent if requested.parent != requested and not is_protected_path(requested.parent) else None
    return FolderBrowseResponse(
        current_path=str(requested),
        parent_path=str(parent) if parent else None,
        breadcrumbs=breadcrumbs,
        quick_access=quick_access,
        children=children[:200],
        major_locations=major_locations,
    )


@app.get("/api/ignored-folders")
def ignored_folders() -> dict[str, list[str]]:
    return {"folders": list_ignored_folders()}


@app.post("/api/ignored-folders")
def ignore_folder(body: IgnoreFolderRequest) -> dict[str, list[str]]:
    path = resolve_user_path(body.path)
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=400, detail="Choose an existing folder to ignore.")
    return {"folders": add_ignored_folder(str(path))}


@app.delete("/api/ignored-folders")
def unignore_folder(path: str = Query(...)) -> dict[str, list[str]]:
    return {"folders": remove_ignored_folder(str(resolve_user_path(path)))}


@app.get("/api/scan-history", response_model=ScanHistoryResponse)
def get_scan_history(limit: int = 30) -> ScanHistoryResponse:
    return ScanHistoryResponse(items=scan_history(limit=limit))


@app.get("/api/quarantine")
def get_quarantine() -> list[QuarantineRecord]:
    return list_quarantine()


@app.post("/api/quarantine/{record_id}/restore", response_model=RestoreResponse)
def restore(record_id: int) -> RestoreResponse:
    try:
        record = restore_item(record_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Feature 5 — record restore feedback so future scans lower confidence
    # for similar artifact names / project types
    artifact_name = record.artifact_name or Path(record.original_path).name
    project_type = record.project_type or "Unknown"
    try:
        record_restore(
            original_path=record.original_path,
            artifact_name=artifact_name,
            project_type=project_type,
        )
    except Exception:
        pass  # feedback is best-effort; never block a restore

    write_audit_log(
        "user_restored",
        {
            "record_id": record_id,
            "original_path": record.original_path,
            "artifact_name": artifact_name,
            "project_type": project_type,
        },
    )
    return RestoreResponse(record=record)


@app.post("/api/quarantine/{record_id}/delete")
def permanent_delete(record_id: int) -> dict[str, object]:
    try:
        record = permanently_delete_item(record_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    write_audit_log(
        "permanently_deleted",
        {"record_id": record_id, "original_path": record.original_path, "size_bytes": record.size_bytes},
    )
    return {"record_id": record_id, "permanently_deleted": True, "original_path": record.original_path}


@app.get("/api/audit")
def audit(limit: int = 20) -> list[dict[str, object]]:
    return list_audit_events(limit=limit)


class SchedulerEnableRequest(BaseModel):
    folders: list[str] = Field(default_factory=list)
    weekday: int = Field(default=0, ge=0, le=6)
    hour: int = Field(default=9, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    min_size_mb: int = Field(default=30, ge=30, le=5000)


@app.get("/api/scheduler")
def get_scheduler() -> dict[str, object]:
    status = scheduler_status()
    reports = list_weekly_reports(limit=5)
    latest = next((item for item in reports if item["kind"] == "html"), None)
    return {**status, "latest_report": latest, "recent_reports": reports}


@app.post("/api/scheduler/enable")
def enable_scheduler(body: SchedulerEnableRequest) -> dict[str, object]:
    folders = [folder.strip() for folder in body.folders if folder.strip()]
    if not folders:
        raise HTTPException(status_code=400, detail="Add at least one folder to scan weekly.")
    for folder in folders:
        if not resolve_user_path(folder).exists():
            raise HTTPException(status_code=400, detail=f"Folder does not exist: {folder}")
    config = SchedulerConfig(
        folders=[str(resolve_user_path(folder)) for folder in folders],
        weekday=body.weekday,
        hour=body.hour,
        minute=body.minute,
        min_size_mb=body.min_size_mb,
    )
    try:
        install_scheduler(config)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return scheduler_status()


@app.post("/api/scheduler/disable")
def disable_scheduler() -> dict[str, object]:
    try:
        uninstall_scheduler()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return scheduler_status()


@app.post("/api/scheduler/run-now")
def run_scheduler_now(body: SchedulerEnableRequest | None = None) -> dict[str, object]:
    config = load_scheduler_config()
    if body and body.folders:
        folders = [str(resolve_user_path(folder)) for folder in body.folders if folder.strip()]
        if not folders:
            raise HTTPException(status_code=400, detail="Add at least one folder to scan.")
        for folder in folders:
            if not Path(folder).exists():
                raise HTTPException(status_code=400, detail=f"Folder does not exist: {folder}")
        config.folders = folders
        config.min_size_mb = body.min_size_mb
        save_scheduler_config(config)
    if not config.folders:
        raise HTTPException(status_code=400, detail="Configure folders before running a weekly scan.")
    result = run_weekly_scan(config, force=True)
    if result.get("skipped"):
        raise HTTPException(status_code=400, detail=str(result.get("reason", "Weekly scan skipped.")))
    return result
