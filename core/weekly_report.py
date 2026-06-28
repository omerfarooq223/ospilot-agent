from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path

from agents.orchestrator_agent import build_plan
from config import REPORTS_DIR, ensure_data_dirs
from core.audit_log import write_audit_log
from core.models import MaintenancePlan, Observation
from core.scan_history_db import get_last_snapshot, save_scan_snapshot
from core.scheduler_config import SchedulerConfig, load_scheduler_config, weekday_label
from core.scoring import format_bytes, health_score, pressure_score


def _pressure_label(metrics) -> str:
    ram = metrics.ram_percent
    cpu = metrics.cpu_percent
    if ram >= 85 or cpu >= 85:
        return "High"
    if ram >= 70 or cpu >= 70:
        return "Medium"
    return "Low"


def _format_action_lines(actions, empty_message: str) -> list[str]:
    if not actions:
        return [empty_message]
    lines = []
    for action in actions:
        size = format_bytes(action.size_bytes) if action.size_bytes else "n/a"
        path = action.path or "system advice"
        lines.append(f"- [{action.risk_level.value}] {size} | {path}")
        lines.append(f"  {action.reason}")
    return lines


def _folder_section(folder: str, observation: Observation, plan: MaintenancePlan) -> str:
    metrics = observation.metrics
    lines = [
        f"## Folder: {folder}",
        "",
        plan.diagnosis_summary,
        "",
        f"- Recoverable cleanup candidates: {format_bytes(plan.estimated_recoverable_bytes)}",
        f"- Reversible cleanup actions: {len(plan.cleanup_actions)}",
        f"- Advisory recommendations: {len(plan.performance_recommendations)}",
        f"- Blocked items: {len(plan.blocked_actions)}",
        "",
        "### Advisory recommendations",
        "",
    ]
    lines.extend(_format_action_lines(plan.performance_recommendations, "No advisory recommendations."))
    lines.extend(["", "### Cleanup candidates (review in OSPilot — nothing was quarantined automatically)", ""])
    lines.extend(_format_action_lines(plan.cleanup_actions, "No reversible cleanup actions found."))
    if plan.blocked_actions:
        lines.extend(["", "### Blocked items", ""])
        lines.extend(_format_action_lines(plan.blocked_actions, ""))
    lines.append("")
    return "\n".join(lines)


def build_weekly_report_markdown(folder_results: list[dict[str, object]], generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    if not folder_results:
        return "# OSPilot Weekly Report\n\nNo folders were scanned.\n"

    first_observation: Observation = folder_results[0]["observation"]  # type: ignore[index]
    metrics = first_observation.metrics
    lines = [
        f"# OSPilot Weekly Report",
        "",
        f"Generated: {generated_at.astimezone().strftime('%A, %B %d, %Y at %I:%M %p %Z')}",
        "",
        "> Read-only scheduled scan. Open OSPilot to approve any cleanup. Nothing was deleted or quarantined automatically.",
        "",
        "## System snapshot",
        "",
        f"- Health score: {health_score(metrics)}/100",
        f"- Pressure: {_pressure_label(metrics)} ({pressure_score(metrics)}/100)",
        f"- CPU: {metrics.cpu_percent:.0f}%",
        f"- RAM: {metrics.ram_percent:.0f}%",
        f"- Disk: {metrics.disk_percent:.0f}%",
        f"- Available disk: {format_bytes(metrics.available_disk_bytes)}",
        "",
        "## Top memory processes",
        "",
    ]
    for proc in first_observation.top_memory_processes[:8]:
        lines.append(f"- {proc.name}: {proc.memory_mb:.0f} MB RAM, {proc.cpu_percent:.0f}% CPU")
    if first_observation.idle_heavy_apps:
        lines.extend(["", "## Idle heavy apps", ""])
        for proc in first_observation.idle_heavy_apps:
            lines.append(f"- {proc.name}: {proc.memory_mb:.0f} MB while idle")
    lines.extend(["", "---", ""])
    total_recoverable = 0
    for result in folder_results:
        plan: MaintenancePlan = result["plan"]  # type: ignore[index]
        total_recoverable += plan.estimated_recoverable_bytes
        lines.append(_folder_section(str(result["folder"]), result["observation"], plan))  # type: ignore[arg-type]
    lines.extend(
        [
            "## Summary",
            "",
            f"- Folders scanned: {len(folder_results)}",
            f"- Total recoverable (if approved in UI): {format_bytes(total_recoverable)}",
            "",
            "Next step: open OSPilot, review the plan, and approve only the items you trust.",
            "",
        ]
    )
    return "\n".join(lines)


def markdown_to_html(markdown_text: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{'<br>'.join(escape(line) for line in paragraph)}</p>")
            paragraph.clear()

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line:
            flush_paragraph()
            continue
        if line.startswith("# "):
            flush_paragraph()
            blocks.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            flush_paragraph()
            blocks.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("### "):
            flush_paragraph()
            blocks.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("> "):
            flush_paragraph()
            blocks.append(f"<blockquote>{escape(line[2:])}</blockquote>")
        elif line.startswith("- "):
            flush_paragraph()
            blocks.append(f"<li>{escape(line[2:])}</li>")
        elif line.startswith("---"):
            flush_paragraph()
            blocks.append("<hr>")
        elif line.startswith("  "):
            flush_paragraph()
            blocks.append(f"<p class='indent'>{escape(line.strip())}</p>")
        else:
            paragraph.append(line)
    flush_paragraph()
    body = "\n".join(blocks).replace("<li>", "<ul><li>", 1)
    while "</li>\n<li>" in body:
        body = body.replace("</li>\n<li>", "</li><li>", 1)
    body = body.replace("</li>\n<h", "</li></ul>\n<h", 1)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OSPilot Weekly Report</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; background: #0d1420; color: #e2e8f0; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
    h1, h2, h3 {{ color: #5eead4; }}
    blockquote {{ border-left: 4px solid #2dd4bf; padding-left: 1rem; color: #94a3b8; }}
    hr {{ border: none; border-top: 1px solid #334155; margin: 2rem 0; }}
    ul {{ padding-left: 1.2rem; }}
    .indent {{ margin-left: 1rem; color: #cbd5e1; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""


def write_weekly_report(folder_results: list[dict[str, object]], generated_at: datetime | None = None) -> dict[str, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = generated_at or datetime.now(timezone.utc)
    stamp = generated_at.astimezone().strftime("%Y-%m-%d_%H%M")
    markdown_text = build_weekly_report_markdown(folder_results, generated_at=generated_at)
    markdown_path = REPORTS_DIR / f"weekly-report-{stamp}.md"
    html_path = REPORTS_DIR / f"weekly-report-{stamp}.html"
    markdown_path.write_text(markdown_text, encoding="utf-8")
    html_path.write_text(markdown_to_html(markdown_text), encoding="utf-8")
    latest_markdown = REPORTS_DIR / "latest-weekly-report.md"
    latest_html = REPORTS_DIR / "latest-weekly-report.html"
    latest_markdown.write_text(markdown_text, encoding="utf-8")
    latest_html.write_text(html_path.read_text(encoding="utf-8"), encoding="utf-8")
    return {"markdown": markdown_path, "html": html_path, "latest_markdown": latest_markdown, "latest_html": latest_html}


def list_weekly_reports(limit: int = 10) -> list[dict[str, str]]:
    ensure_data_dirs()
    reports = sorted(REPORTS_DIR.glob("weekly-report-*.md"), reverse=True)
    items = []
    for path in reports[:limit]:
        items.append({"name": path.name, "path": str(path), "kind": "markdown"})
        html_path = path.with_suffix(".html")
        if html_path.exists():
            items.append({"name": html_path.name, "path": str(html_path), "kind": "html"})
    return items


def run_weekly_scan(config: SchedulerConfig | None = None, *, force: bool = False) -> dict[str, object]:
    config = config or load_scheduler_config()
    if not force and not config.enabled:
        return {"skipped": True, "reason": "Weekly scan is disabled."}
    if not config.folders:
        return {"skipped": True, "reason": "No folders configured for weekly scan."}

    folder_results: list[dict[str, object]] = []
    for folder in config.folders:
        path = Path(folder).expanduser()
        if not path.exists():
            continue
        previous_snapshot = get_last_snapshot(str(path))
        observation, plan, diagnosis_result = build_plan(
            path,
            min_size_mb=config.min_size_mb,
            previous_snapshot=previous_snapshot,
        )
        save_scan_snapshot(str(path), observation, plan)
        folder_results.append(
            {
                "folder": str(path),
                "observation": observation,
                "plan": plan,
                "fallback": diagnosis_result.used_fallback,
            }
        )

    if not folder_results:
        return {"skipped": True, "reason": "Configured folders were missing or empty."}

    report_paths = write_weekly_report(folder_results)
    write_audit_log(
        "weekly_scan_completed",
        {
            "folders": [result["folder"] for result in folder_results],
            "markdown_report": str(report_paths["markdown"]),
            "html_report": str(report_paths["html"]),
        },
    )
    return {
        "skipped": False,
        "folders_scanned": len(folder_results),
        "reports": {key: str(value) for key, value in report_paths.items()},
        "schedule": f"{weekday_label(config.weekday)} at {config.hour:02d}:{config.minute:02d}",
    }
