"""Diagnosis Agent — analyses an Observation and returns a structured DiagnosisResult.

Two modes:
* **Groq mode** — sends a pre-aggregated scan summary to the LLM and asks for a
  structured JSON response with ``summary``, ``top_risks``, ``recommended_scenario``,
  ``urgency_level``, and ``agent_confidence``.
* **Fallback mode** — deterministic path used when no Groq key is configured or the
  LLM call fails.  Returns a ``DiagnosisResult`` with ``used_fallback=True``.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

try:
    from groq import Groq
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    Groq = None

from config import GROQ_API_KEY, GROQ_MODEL
from core.models import DiagnosisResult, Observation, ScanDelta, UrgencyLevel
from core.scoring import format_bytes


# ---------------------------------------------------------------------------
# Pre-aggregated scan summary builder (Feature 2)
# ---------------------------------------------------------------------------

def _build_scan_summary(observation: Observation, scan_delta: ScanDelta | None = None) -> dict:
    """Build a compact, LLM-friendly summary of the full scan result.

    Instead of sending the raw first-15 items we send grouped totals so the LLM
    has a complete picture of the workspace even for very large scans.
    """
    items = observation.scan_items
    metrics = observation.metrics

    # Reclaimable bytes: Low + Medium risk
    reclaimable = sum(
        item.size_bytes for item in items if item.risk_level.value in {"Low", "Medium"}
    )
    total_bytes = sum(item.size_bytes for item in items)

    # By project type
    by_type: dict[str, dict[str, int]] = {}
    for item in items:
        pt = item.project_type or "Unknown"
        if pt not in by_type:
            by_type[pt] = {"count": 0, "bytes": 0}
        by_type[pt]["count"] += 1
        by_type[pt]["bytes"] += item.size_bytes

    # Top artifact categories (by name of the path's final component)
    name_counter: Counter[str] = Counter()
    name_bytes: dict[str, int] = {}
    for item in items:
        name = Path(item.path).name
        name_counter[name] += 1
        name_bytes[name] = name_bytes.get(name, 0) + item.size_bytes
    top_artifacts = [
        {"name": name, "count": name_counter[name], "bytes": format_bytes(name_bytes[name])}
        for name, _ in name_counter.most_common(8)
    ]

    # Rebuildability breakdown
    rebuild_counts: Counter[str] = Counter(item.rebuildability.value for item in items)

    # Stale candidates (dormant ≥ 30 days)
    stale = [item for item in items if (item.dormant_days or 0) >= 30]

    # Active (linked to a running process)
    active_count = sum(1 for item in items if item.linked_processes)

    summary: dict = {
        "system_metrics": {
            "cpu_percent": round(metrics.cpu_percent),
            "ram_percent": round(metrics.ram_percent),
            "disk_percent": round(metrics.disk_percent),
            "available_disk": format_bytes(metrics.available_disk_bytes),
        },
        "scan_totals": {
            "total_items": len(items),
            "total_bytes": format_bytes(total_bytes),
            "reclaimable_bytes": format_bytes(reclaimable),
            "active_process_linked": active_count,
        },
        "by_project_type": {
            pt: {"count": v["count"], "bytes": format_bytes(v["bytes"])}
            for pt, v in sorted(by_type.items(), key=lambda kv: kv[1]["bytes"], reverse=True)
        },
        "top_artifact_categories": top_artifacts,
        "rebuildability_breakdown": dict(rebuild_counts),
        "stale_candidates": {
            "count": len(stale),
            "bytes": format_bytes(sum(item.size_bytes for item in stale)),
        },
        "idle_heavy_apps": [
            {"name": p.name, "memory_mb": round(p.memory_mb)}
            for p in observation.idle_heavy_apps[:5]
        ],
    }

    if scan_delta and scan_delta.summary:
        summary["scan_delta"] = scan_delta.summary

    return summary


# ---------------------------------------------------------------------------
# Fallback (deterministic) diagnosis (Feature 1 — returns DiagnosisResult)
# ---------------------------------------------------------------------------

def _fallback_diagnosis(observation: Observation, scan_delta: ScanDelta | None = None) -> DiagnosisResult:
    metrics = observation.metrics
    recoverable = sum(
        item.size_bytes for item in observation.scan_items
        if item.risk_level.value in {"Low", "Medium"}
    )
    heavy = observation.idle_heavy_apps[0].name if observation.idle_heavy_apps else None
    rebuildable = [
        item for item in observation.scan_items
        if item.rebuildability.value in {"High", "Medium"}
    ]
    project_types = sorted(
        {item.project_type for item in observation.scan_items if item.project_type != "Unknown"}
    )

    summary = (
        f"OSPilot sees {metrics.ram_percent:.0f}% RAM, {metrics.cpu_percent:.0f}% CPU, "
        f"and {metrics.disk_percent:.0f}% disk usage. "
        f"The selected folder contains about {format_bytes(recoverable)} of low/medium-risk "
        f"developer artifacts across "
        f"{', '.join(project_types) if project_types else 'unknown'} workspaces "
        f"({len(rebuildable)} rebuildable items)."
    )
    if scan_delta and scan_delta.summary:
        summary += f" {scan_delta.summary}"

    top_risks: list[str] = []
    if heavy:
        top_risks.append(f"{heavy} is consuming notable RAM while idle.")
    if metrics.disk_percent > 85:
        top_risks.append(f"Disk is {metrics.disk_percent:.0f}% full — cleanup is advisable soon.")
    if recoverable > 1024 ** 3:
        top_risks.append(f"Over {format_bytes(recoverable)} of rebuildable artifacts detected.")

    urgency = (
        UrgencyLevel.HIGH if metrics.disk_percent > 85
        else UrgencyLevel.MEDIUM if recoverable > 500 * 1024 * 1024
        else UrgencyLevel.LOW
    )
    recommended = "conservative" if urgency == UrgencyLevel.LOW else "balanced"

    return DiagnosisResult(
        summary=summary,
        top_risks=top_risks,
        recommended_scenario=recommended,
        urgency_level=urgency,
        agent_confidence=40,
        used_fallback=True,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def diagnose(
    observation: Observation,
    scan_delta: ScanDelta | None = None,
) -> DiagnosisResult:
    """Return a structured DiagnosisResult for the given observation.

    Falls back to deterministic mode when Groq is unavailable or the LLM
    response cannot be parsed.
    """
    if not GROQ_API_KEY or Groq is None:
        return _fallback_diagnosis(observation, scan_delta)

    scan_summary = _build_scan_summary(observation, scan_delta)

    system_prompt = (
        "You are OSPilot, a cautious local system health agent. "
        "Analyse the workspace scan summary and return ONLY a valid JSON object with these exact keys:\n"
        "  summary          — 2-3 sentence plain-English diagnosis (string)\n"
        "  top_risks        — list of up to 4 concise risk strings\n"
        "  recommended_scenario — one of: conservative, balanced, deep (string)\n"
        "  urgency_level    — one of: low, medium, high (string)\n"
        "  agent_confidence — integer 0-100 reflecting your confidence in the diagnosis\n\n"
        "Focus on project type, rebuildability, manifest evidence, and recovery recipes. "
        "Never recommend deleting files permanently or killing processes automatically. "
        "Do not output markdown, code fences, or any text outside the JSON object."
    )

    user_prompt = f"Diagnose this workspace scan:\n{json.dumps(scan_summary, indent=2)}"

    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        content = (response.choices[0].message.content or "").strip()
        if not content:
            return _fallback_diagnosis(observation, scan_delta)

        raw = json.loads(content)

        # Validate and coerce urgency_level
        urgency_raw = str(raw.get("urgency_level", "medium")).lower()
        try:
            urgency = UrgencyLevel(urgency_raw)
        except ValueError:
            urgency = UrgencyLevel.MEDIUM

        # Validate recommended_scenario
        scenario = str(raw.get("recommended_scenario", "balanced")).lower()
        if scenario not in {"conservative", "balanced", "deep"}:
            scenario = "balanced"

        top_risks = raw.get("top_risks", [])
        if not isinstance(top_risks, list):
            top_risks = []
        top_risks = [str(r) for r in top_risks[:5]]

        confidence_raw = raw.get("agent_confidence", 70)
        try:
            confidence = max(0, min(100, int(confidence_raw)))
        except (TypeError, ValueError):
            confidence = 70

        return DiagnosisResult(
            summary=str(raw.get("summary", "")).strip() or _fallback_diagnosis(observation, scan_delta).summary,
            top_risks=top_risks,
            recommended_scenario=scenario,
            urgency_level=urgency,
            agent_confidence=confidence,
            used_fallback=False,
        )

    except Exception:
        return _fallback_diagnosis(observation, scan_delta)
