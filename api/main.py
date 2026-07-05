from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from io import BytesIO
import json
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.orchestrator_agent import build_plan, execute_approved_actions, run_report
from config import REPORTS_DIR, ensure_data_dirs, fallback_mode_enabled
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


class ReportFileResponse(BaseModel):
    path: str
    filename: str
    format: str


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


def _report_generated_label() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def _report_filename(format_name: str) -> str:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    return f"ospilot-report-{stamp}.{format_name}"


def _human_label(key: str) -> str:
    return key.replace("_", " ").title()


def _compact_value(value: object) -> str:
    if value is None:
        return "None"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, indent=2, default=str)
    return str(value)


def _short_value(value: object, *, max_chars: int = 900) -> str:
    text = _compact_value(value)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 24].rstrip() + "\n... truncated in summary"


def _friendly_report_value(value: object) -> str:
    if value is None:
        return "None"
    if isinstance(value, list):
        if not value:
            return "None"
        if all(not isinstance(item, (dict, list, tuple)) for item in value):
            return ", ".join(str(item) for item in value)
        lines: list[str] = []
        for index, item in enumerate(value, start=1):
            if isinstance(item, dict):
                parts = [f"{_human_label(str(key))}: {val}" for key, val in item.items()]
                lines.append(f"{index}. " + "; ".join(parts))
            else:
                lines.append(f"{index}. {item}")
        return "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "None"
        return "\n".join(f"{_human_label(str(key))}: {val}" for key, val in value.items())
    return str(value)


def _build_report_html(report: dict[str, object], generated: str) -> str:
    lines = [
        "<!doctype html><html><head><meta charset='utf-8'><title>OSPilot Report</title>",
        "<style>body{font-family:Inter,system-ui,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;line-height:1.6;background:#0d1420;color:#e2e8f0}h1,h2{color:#5eead4}.card{border:1px solid #334155;border-radius:12px;padding:16px;margin:12px 0;background:#111827}code{color:#67e8f9}</style>",
        "</head><body>",
        "<h1>OSPilot Scan Report</h1>",
        f"<p>Generated: {generated}</p>",
    ]
    for key, value in report.items():
        lines.append("<div class='card'>")
        lines.append(f"<h2>{escape(_human_label(str(key)))}</h2>")
        lines.append(f"<pre>{escape(_compact_value(value))}</pre>")
        lines.append("</div>")
    lines.append("</body></html>")
    return "\n".join(lines)


def _build_report_pdf(report: dict[str, object], generated: str) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            HRFlowable,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="PDF export requires reportlab. Run pip install -r requirements.txt.") from exc

    PAGE_W, _ = A4
    MARGIN = 1.55 * cm
    content_w = PAGE_W - (2 * MARGIN)

    INK = colors.HexColor("#17211f")
    MUTED = colors.HexColor("#60716d")
    SOFT = colors.HexColor("#f5faf8")
    LINE = colors.HexColor("#cbdad6")
    MINT = colors.HexColor("#0f9f87")
    MINT_DARK = colors.HexColor("#0b6f61")
    SKY = colors.HexColor("#2f8ec9")
    AMBER = colors.HexColor("#a36a00")
    WHITE = colors.white

    base = getSampleStyleSheet()["Normal"]
    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    font_candidates = [
        (
            "OSPilotSans",
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            "OSPilotSans-Bold",
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ),
        (
            "OSPilotSans",
            Path("/Library/Fonts/Arial.ttf"),
            "OSPilotSans-Bold",
            Path("/Library/Fonts/Arial Bold.ttf"),
        ),
        (
            "OSPilotSans",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            "OSPilotSans-Bold",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            "OSPilotSans",
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            "OSPilotSans-Bold",
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ),
    ]
    for regular_name, regular_path, bold_name, bold_path in font_candidates:
        if regular_path.exists() and bold_path.exists():
            pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
            pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
            regular_font = regular_name
            bold_font = bold_name
            break

    def ps(name: str, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base, **kw)

    style_title = ps("Title", fontName=bold_font, fontSize=24, leading=29, textColor=INK, alignment=TA_LEFT, spaceAfter=3)
    style_kicker = ps("Kicker", fontName=bold_font, fontSize=8.5, leading=11, textColor=MINT_DARK, alignment=TA_LEFT)
    style_body = ps("Body", fontName=regular_font, fontSize=8.7, leading=12.5, textColor=INK, alignment=TA_LEFT)
    style_small = ps("Small", fontName=regular_font, fontSize=7.4, leading=10, textColor=MUTED, alignment=TA_LEFT)
    style_label = ps("Label", fontName=bold_font, fontSize=7.4, leading=9.5, textColor=MUTED, alignment=TA_LEFT)
    style_section = ps("Section", fontName=bold_font, fontSize=12.5, leading=16, textColor=INK, alignment=TA_LEFT, spaceBefore=12, spaceAfter=5)
    style_stat = ps("Stat", fontName=bold_font, fontSize=20, leading=23, textColor=MINT_DARK, alignment=TA_CENTER)
    style_stat_label = ps("StatLabel", fontName=bold_font, fontSize=7.5, leading=9.5, textColor=MUTED, alignment=TA_CENTER)
    style_stat_note = ps("StatNote", fontName=regular_font, fontSize=7.2, leading=9.2, textColor=MUTED, alignment=TA_CENTER)
    style_table_header = ps("TableHeader", fontName=bold_font, fontSize=7.2, leading=9, textColor=WHITE, alignment=TA_LEFT)

    def para(text: object, style: ParagraphStyle = style_body) -> Paragraph:
        cleaned = escape(_short_value(_friendly_report_value(text))).replace("\n", "<br/>")
        return Paragraph(cleaned, style)

    def stat_card(label: str, value: object, note: str = "") -> list[Paragraph]:
        return [
            Paragraph(escape(label.upper()), style_stat_label),
            Paragraph(escape(str(value)), style_stat),
            Paragraph(escape(note), style_stat_note),
        ]

    recovered = report.get("recovered", "0 B")
    quarantined = report.get("quarantined_count", 0)
    health_before = report.get("before_health_score", "--")
    health_after = report.get("after_health_score", "--")
    pressure_before = report.get("before_pressure_score", "--")
    pressure_after = report.get("after_pressure_score", "--")
    session_id = report.get("session_id", "Not recorded")
    scan_folder = report.get("folder", "Not recorded")

    extra_fields = [
        (str(key), value)
        for key, value in report.items()
        if key not in {
            "recovered",
            "quarantined_count",
            "before_health_score",
            "after_health_score",
            "before_pressure_score",
            "after_pressure_score",
            "session_id",
            "folder",
            "recovered_bytes",
        }
    ]

    def draw_page_chrome(canvas, doc_obj):
        canvas.saveState()
        width, height = doc_obj.pagesize
        canvas.setFillColor(WHITE)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)

        canvas.setFillColor(MINT)
        canvas.rect(0, height - 18, width, 18, fill=1, stroke=0)
        canvas.setFillColor(MINT_DARK)
        canvas.rect(0, height - 21, width, 3, fill=1, stroke=0)

        canvas.setFillColor(MUTED)
        canvas.setFont(regular_font, 7.5)
        canvas.drawString(MARGIN, 21, "OS Pilot - Local report. No cloud uploads.")
        canvas.drawRightString(width - MARGIN, 21, f"Page {doc_obj.page}")
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 34, width - MARGIN, 34)
        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="OS Pilot Scan Report",
        author="OS Pilot",
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=1.25 * cm,
        bottomMargin=1.35 * cm,
    )

    story = [
        Paragraph("OS PILOT", style_kicker),
        Paragraph("System Scan Report", style_title),
        Paragraph(f"Generated {escape(generated)}", style_small),
        Spacer(1, 0.25 * cm),
        HRFlowable(width="100%", thickness=1.2, color=MINT, spaceAfter=12),
    ]

    stat_width = content_w / 4
    stats = [[
        stat_card("Recovered", recovered),
        stat_card("Quarantined", quarantined, "items"),
        stat_card("Health", f"{health_after}%", f"before {health_before}%"),
        stat_card("Pressure", pressure_after, f"before {pressure_before}"),
    ]]
    stat_table = Table(stats, colWidths=[stat_width] * 4)
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([stat_table, Spacer(1, 0.35 * cm)])

    story.append(Paragraph("Scan Details", style_section))
    detail_rows = [
        [para("Session ID", style_label), para(session_id)],
        [para("Scan Folder", style_label), para(scan_folder)],
        [para("Generated", style_label), para(generated)],
    ]
    detail_table = Table(detail_rows, colWidths=[3.3 * cm, content_w - 3.3 * cm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([detail_table, Spacer(1, 0.25 * cm)])

    scenario_rows = []
    for scenario in report.get("cleanup_scenarios") or []:
        if not isinstance(scenario, dict):
            continue
        scenario_rows.append([
            para(scenario.get("name", "Scenario")),
            para(scenario.get("estimated_recoverable", "--")),
            para(scenario.get("item_count", "--")),
            para(scenario.get("confidence", "--")),
        ])
    if scenario_rows:
        story.append(Paragraph("Cleanup Scenarios", style_section))
        scenario_table = Table(
            [[
                Paragraph("Scenario", style_table_header),
                Paragraph("Recoverable", style_table_header),
                Paragraph("Items", style_table_header),
                Paragraph("Confidence", style_table_header),
            ], *scenario_rows],
            colWidths=[content_w * 0.38, content_w * 0.24, content_w * 0.16, content_w * 0.22],
            repeatRows=1,
        )
        scenario_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), MINT_DARK),
            ("BACKGROUND", (0, 1), (-1, -1), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]),
            ("BOX", (0, 0), (-1, -1), 0.6, LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.extend([scenario_table, Spacer(1, 0.25 * cm)])

    project_types = report.get("project_types")
    if isinstance(project_types, list) and project_types:
        story.append(Paragraph("Detected Project Types", style_section))
        story.append(Paragraph(
            f"OS Pilot found signals for {escape(', '.join(str(item) for item in project_types))}. "
            "These labels help explain which cleanup recipes are safe to use.",
            style_body,
        ))
        story.append(Spacer(1, 0.2 * cm))

    recovery_recipes = report.get("recovery_recipes")
    if isinstance(recovery_recipes, list) and recovery_recipes:
        recipe_rows = []
        for recipe in recovery_recipes:
            if not isinstance(recipe, dict):
                continue
            recipe_rows.append([
                para(recipe.get("path", "Unknown path")),
                para(recipe.get("project_type", "Unknown")),
                para(recipe.get("recipe", "No recipe recorded.")),
            ])
        if recipe_rows:
            story.append(Paragraph("Recovery Recipes", style_section))
            story.append(Paragraph(
                "Use these commands only if you need to rebuild a quarantined development artifact.",
                style_small,
            ))
            recipe_table = Table(
                [[
                    Paragraph("Artifact Path", style_table_header),
                    Paragraph("Project", style_table_header),
                    Paragraph("Rebuild Command", style_table_header),
                ], *recipe_rows],
                colWidths=[content_w * 0.36, content_w * 0.18, content_w * 0.46],
                repeatRows=1,
            )
            recipe_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), MINT_DARK),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.extend([recipe_table, Spacer(1, 0.25 * cm)])

    audit = report.get("audit")
    if isinstance(audit, dict) and audit:
        audit_rows = [
            [para(_human_label(str(event_name))), para(count)]
            for event_name, count in audit.items()
        ]
        story.append(Paragraph("Audit Summary", style_section))
        story.append(Paragraph("A compact count of important local actions recorded by OS Pilot.", style_small))
        audit_table = Table(audit_rows, colWidths=[content_w * 0.65, content_w * 0.35])
        audit_table.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, SOFT]),
            ("BOX", (0, 0), (-1, -1), 0.6, LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.extend([audit_table, Spacer(1, 0.25 * cm)])

    if extra_fields:
        story.append(Paragraph("Report Summary", style_section))
        friendly_keys = {"cleanup_scenarios", "project_types", "recovery_recipes", "audit"}
        summary_rows = [
            [para(_human_label(key), style_label), para(value)]
            for key, value in extra_fields
            if key not in friendly_keys
        ]
        if summary_rows:
            summary_table = Table(summary_rows, colWidths=[4.4 * cm, content_w - 4.4 * cm])
            summary_table.setStyle(TableStyle([
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, SOFT]),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.extend([summary_table, Spacer(1, 0.25 * cm)])

    try:
        before_val = float(health_before)
        after_val = float(health_after)
        delta = after_val - before_val
        sign = "+" if delta >= 0 else ""
        story.append(Paragraph("Health Change", style_section))
        bar_width = content_w
        after_frac = max(0.0, min(1.0, after_val / 100))
        bar_table = Table([["", ""]], colWidths=[bar_width * after_frac, bar_width * (1 - after_frac)], rowHeights=[10])
        bar_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), SKY if delta >= 0 else AMBER),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#e7efed")),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.extend([
            bar_table,
            Spacer(1, 0.1 * cm),
            Paragraph(f"{sign}{delta:.1f}% change in health score after cleanup.", style_small),
            Spacer(1, 0.25 * cm),
        ])
    except (TypeError, ValueError):
        pass

    story.extend([
        HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=8, spaceAfter=8),
        Paragraph(
            "This report was generated locally by OS Pilot. Scan results, audit events, and quarantined files remain on this device.",
            style_small,
        ),
    ])

    doc.build(story, onFirstPage=draw_page_chrome, onLaterPages=draw_page_chrome)
    return buffer.getvalue()


def _build_report_content(report: dict[str, object], format_name: str, generated: str) -> tuple[bytes, str]:
    if format_name == "html":
        return _build_report_html(report, generated).encode("utf-8"), "text/html"
    if format_name == "pdf":
        return _build_report_pdf(report, generated), "application/pdf"
    text = "\n".join(f"{key}: {_compact_value(value)}" for key, value in report.items())
    return text.encode("utf-8"), "text/plain"


@app.post("/api/report/export")
def export_report(body: ReportExportRequest) -> Response:
    generated = _report_generated_label()
    report = body.report or {}
    format_name = body.format.lower()
    content, media_type = _build_report_content(report, format_name, generated)
    filename = f"ospilot-report.{format_name if format_name in {'html', 'pdf'} else 'txt'}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/report/export-file", response_model=ReportFileResponse)
def export_report_file(body: ReportExportRequest) -> ReportFileResponse:
    generated = _report_generated_label()
    report = body.report or {}
    format_name = body.format.lower()
    if format_name not in {"html", "pdf", "txt"}:
        format_name = "txt"
    content, _ = _build_report_content(report, format_name, generated)
    ensure_data_dirs()
    filename = _report_filename(format_name)
    path = REPORTS_DIR / filename
    path.write_bytes(content)
    return ReportFileResponse(path=str(path.resolve()), filename=filename, format=format_name)



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
