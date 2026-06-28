"""Longitudinal scan history stored in the shared ospilot SQLite database.

Saves a lightweight snapshot after every scan so the Diagnosis Agent can
compute a delta ("workspace grew by 1.2 GB since the last scan 7 days ago").
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DB_PATH, ensure_data_dirs
from core.models import MaintenancePlan, Observation, ScanDelta
from core.scoring import format_bytes


def _init_table(db_path: Path = DB_PATH) -> None:
    ensure_data_dirs()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                total_items INTEGER NOT NULL DEFAULT 0,
                total_bytes INTEGER NOT NULL DEFAULT 0,
                reclaimable_bytes INTEGER NOT NULL DEFAULT 0,
                project_types TEXT NOT NULL DEFAULT '[]',
                artifact_summary TEXT NOT NULL DEFAULT '{}'
            )
            """
        )


def save_scan_snapshot(
    folder: str,
    observation: Observation,
    plan: MaintenancePlan,
    db_path: Path = DB_PATH,
) -> int:
    """Persist a compact snapshot of the scan result and return the new row id."""
    _init_table(db_path)
    all_actions = [*plan.cleanup_actions, *plan.performance_recommendations, *plan.blocked_actions]
    project_types = sorted({a.project_type for a in all_actions if a.project_type != "Unknown"})

    # Top artifact categories by total bytes
    by_name: dict[str, dict[str, int]] = {}
    for item in observation.scan_items:
        name = Path(item.path).name
        if name not in by_name:
            by_name[name] = {"count": 0, "bytes": 0}
        by_name[name]["count"] += 1
        by_name[name]["bytes"] += item.size_bytes
    top_artifacts = dict(
        sorted(by_name.items(), key=lambda kv: kv[1]["bytes"], reverse=True)[:10]
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO scan_snapshots
                (folder, timestamp, total_items, total_bytes, reclaimable_bytes, project_types, artifact_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                folder,
                timestamp,
                len(observation.scan_items),
                sum(item.size_bytes for item in observation.scan_items),
                plan.estimated_recoverable_bytes,
                json.dumps(project_types),
                json.dumps(top_artifacts),
            ),
        )
    return int(cursor.lastrowid)


def get_last_snapshot(folder: str, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    """Return the most recent snapshot for *folder* before the current scan is saved."""
    _init_table(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, folder, timestamp, total_items, total_bytes, reclaimable_bytes,
                   project_types, artifact_summary
            FROM scan_snapshots
            WHERE folder = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (folder,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "folder": row[1],
        "timestamp": row[2],
        "total_items": row[3],
        "total_bytes": row[4],
        "reclaimable_bytes": row[5],
        "project_types": json.loads(row[6]),
        "artifact_summary": json.loads(row[7]),
    }


def compute_delta(
    current_items: int,
    current_bytes: int,
    current_reclaimable: int,
    previous: dict[str, Any],
) -> ScanDelta:
    """Compute a human-readable delta between the current scan and a previous snapshot."""
    prev_at_str: str = previous["timestamp"]
    try:
        prev_at = datetime.fromisoformat(prev_at_str)
    except ValueError:
        prev_at = None

    days_since: int | None = None
    if prev_at:
        now = datetime.now(timezone.utc)
        prev_aware = prev_at if prev_at.tzinfo else prev_at.replace(tzinfo=timezone.utc)
        days_since = max(0, (now - prev_aware).days)

    bytes_delta = current_bytes - previous["total_bytes"]
    items_delta = current_items - previous["total_items"]
    reclaimable_delta = current_reclaimable - previous["reclaimable_bytes"]

    # Build a concise human-readable summary
    time_str = f"{days_since} day{'s' if days_since != 1 else ''} ago" if days_since is not None else "a previous scan"
    if abs(bytes_delta) < 1024 * 1024:  # < 1 MB change — treat as stable
        size_part = "remained roughly the same in total size"
    elif bytes_delta > 0:
        size_part = f"grew by {format_bytes(bytes_delta)}"
    else:
        size_part = f"shrank by {format_bytes(abs(bytes_delta))}"

    if items_delta > 0:
        items_part = f", adding {items_delta} new candidate item{'s' if items_delta != 1 else ''}"
    elif items_delta < 0:
        items_part = f", removing {abs(items_delta)} candidate item{'s' if abs(items_delta) != 1 else ''}"
    else:
        items_part = ""

    if abs(reclaimable_delta) >= 1024 * 1024:
        rec_dir = "More" if reclaimable_delta > 0 else "Less"
        rec_part = f" {rec_dir} reclaimable space is available ({format_bytes(abs(reclaimable_delta))} difference)."
    else:
        rec_part = ""

    summary = f"Since {time_str}, this workspace {size_part}{items_part}.{rec_part}"

    return ScanDelta(
        previous_scan_at=prev_at,
        days_since_last_scan=days_since,
        bytes_delta=bytes_delta,
        items_delta=items_delta,
        reclaimable_delta=reclaimable_delta,
        summary=summary,
    )
