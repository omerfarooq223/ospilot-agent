from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DB_PATH, ensure_data_dirs
from core.models import AuditEvent


def init_audit_db(db_path: Path = DB_PATH) -> None:
    ensure_data_dirs()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )


def write_audit_log(event: AuditEvent | str, payload: dict[str, Any] | None = None, db_path: Path = DB_PATH) -> None:
    init_audit_db(db_path)
    audit_event = event if isinstance(event, AuditEvent) else AuditEvent(event_type=event, payload=payload or {})
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO audit_events (event_type, payload, timestamp) VALUES (?, ?, ?)",
            (
                audit_event.event_type,
                json.dumps(audit_event.payload, default=str),
                audit_event.timestamp.isoformat(),
            ),
        )


def list_audit_events(limit: int = 50, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    init_audit_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT id, event_type, payload, timestamp FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    events = []
    for row in rows:
        events.append(
            {
                "id": row[0],
                "event_type": row[1],
                "payload": json.loads(row[2]),
                "timestamp": row[3],
            }
        )
    return events


def audit_summary(db_path: Path = DB_PATH) -> dict[str, Any]:
    events = list_audit_events(limit=200, db_path=db_path)
    counts: dict[str, int] = {}
    for event in events:
        counts[event["event_type"]] = counts.get(event["event_type"], 0) + 1
    return {"total_events": len(events), "counts": counts, "generated_at": datetime.utcnow().isoformat()}
