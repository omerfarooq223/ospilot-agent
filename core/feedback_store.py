"""User feedback store — tracks which items were restored from quarantine.

When a user restores an item, we record it here. Future confidence scoring
calls ``restore_penalty()`` to apply a discount for artifact names / project
types that the user has repeatedly chosen to keep.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from config import DB_PATH, ensure_data_dirs

# Look back 90 days when computing a penalty
_LOOKBACK_DAYS = 90
# Each restore event contributes this many penalty points, capped at 30
_POINTS_PER_RESTORE = 10
_MAX_PENALTY = 30


def _init_table(db_path: Path = DB_PATH) -> None:
    ensure_data_dirs()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_name TEXT NOT NULL,
                project_type TEXT NOT NULL,
                original_path TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )


def record_restore(
    original_path: str,
    artifact_name: str | None = None,
    project_type: str = "Unknown",
    db_path: Path = DB_PATH,
) -> None:
    """Record that the user restored *original_path* from quarantine.

    *artifact_name* defaults to the final path component (e.g. ``node_modules``).
    """
    _init_table(db_path)
    name = artifact_name or Path(original_path).name
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO user_feedback (artifact_name, project_type, original_path, feedback_type, timestamp)
            VALUES (?, ?, ?, 'restored', ?)
            """,
            (name, project_type, original_path, timestamp),
        )
    _restore_penalty_cached.cache_clear()


@lru_cache(maxsize=512)
def _restore_penalty_cached(artifact_name: str, project_type: str, db_path_str: str) -> int:
    db_path = Path(db_path_str)
    _init_table(db_path)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)).isoformat()
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM user_feedback
            WHERE artifact_name = ?
              AND project_type = ?
              AND feedback_type = 'restored'
              AND timestamp >= ?
            """,
            (artifact_name, project_type, cutoff),
        ).fetchone()
    count = row[0] if row else 0
    return min(_MAX_PENALTY, count * _POINTS_PER_RESTORE)


def restore_penalty(artifact_name: str, project_type: str, db_path: Path = DB_PATH) -> int:
    """Return a confidence penalty (0–30) for restored similar items."""
    return _restore_penalty_cached(artifact_name, project_type, str(db_path))


def list_feedback(limit: int = 50, db_path: Path = DB_PATH) -> list[dict[str, str]]:
    """Return recent feedback events (newest first)."""
    _init_table(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, artifact_name, project_type, original_path, feedback_type, timestamp
            FROM user_feedback
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "id": str(row[0]),
            "artifact_name": row[1],
            "project_type": row[2],
            "original_path": row[3],
            "feedback_type": row[4],
            "timestamp": row[5],
        }
        for row in rows
    ]
