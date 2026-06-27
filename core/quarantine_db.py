from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH, QUARANTINE_DIR, ensure_data_dirs
from core.models import QuarantineRecord
from core.scanner import get_path_size
from mcp_server.safety_rules import is_protected_path, normalize_path, path_identity


def init_quarantine_db(db_path: Path = DB_PATH) -> None:
    ensure_data_dirs()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quarantine_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                quarantine_path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                restored INTEGER NOT NULL DEFAULT 0,
                permanently_deleted INTEGER NOT NULL DEFAULT 0,
                artifact_name TEXT NOT NULL DEFAULT '',
                project_type TEXT NOT NULL DEFAULT 'Unknown'
            )
            """
        )
        # Add column to existing DBs that were created before this change
        try:
            conn.execute("ALTER TABLE quarantine_records ADD COLUMN permanently_deleted INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            conn.execute("ALTER TABLE quarantine_records ADD COLUMN artifact_name TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            conn.execute("ALTER TABLE quarantine_records ADD COLUMN project_type TEXT NOT NULL DEFAULT 'Unknown'")
        except sqlite3.OperationalError:
            pass  # Column already exists


def _record_from_row(row: tuple) -> QuarantineRecord:
    return QuarantineRecord(
        id=row[0],
        original_path=row[1],
        quarantine_path=row[2],
        size_bytes=row[3],
        reason=row[4],
        timestamp=datetime.fromisoformat(row[5]),
        restored=bool(row[6]),
        permanently_deleted=bool(row[7]) if len(row) > 7 else False,
        artifact_name=row[8] if len(row) > 8 and row[8] else Path(row[1]).name,
        project_type=row[9] if len(row) > 9 and row[9] else "Unknown",
    )


def _identity_matches(
    current: dict[str, int | bool | None],
    expected: dict[str, int | bool | None] | None,
) -> bool:
    if not expected or all(expected.get(key) is None for key in ("path_device", "path_inode", "path_mtime_ns")):
        return True
    return (
        current.get("path_device") == expected.get("path_device")
        and current.get("path_inode") == expected.get("path_inode")
        and current.get("path_mtime_ns") == expected.get("path_mtime_ns")
        and not current.get("path_is_symlink")
        and not expected.get("path_is_symlink")
    )


def quarantine_item(
    path: str | Path,
    reason: str,
    db_path: Path = DB_PATH,
    expected_identity: dict[str, int | bool | None] | None = None,
    artifact_name: str | None = None,
    project_type: str = "Unknown",
) -> QuarantineRecord:
    init_quarantine_db(db_path)
    raw_source = Path(path).expanduser()
    current_identity = path_identity(raw_source)
    if current_identity["path_is_symlink"]:
        raise ValueError(f"Symlink paths cannot be quarantined: {raw_source}")
    if not _identity_matches(current_identity, expected_identity):
        raise ValueError(f"Path changed after scan and must be rescanned before quarantine: {raw_source}")
    source = Path(normalize_path(path))
    if is_protected_path(source):
        raise ValueError(f"Protected path cannot be quarantined: {source}")
    if not source.exists():
        raise FileNotFoundError(str(source))

    size_bytes = get_path_size(source)
    artifact = artifact_name or source.name
    timestamp = datetime.now(timezone.utc)
    safe_name = f"{timestamp.strftime('%Y%m%d%H%M%S')}_{source.name}"
    destination = QUARANTINE_DIR / safe_name
    counter = 1
    while destination.exists():
        destination = QUARANTINE_DIR / f"{safe_name}_{counter}"
        counter += 1

    shutil.move(str(source), str(destination))

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO quarantine_records
                (original_path, quarantine_path, size_bytes, reason, timestamp, restored, permanently_deleted, artifact_name, project_type)
            VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
            """,
            (str(source), str(destination), size_bytes, reason, timestamp.isoformat(), artifact, project_type),
        )
        record_id = int(cursor.lastrowid)

    return QuarantineRecord(
        id=record_id,
        original_path=str(source),
        quarantine_path=str(destination),
        size_bytes=size_bytes,
        reason=reason,
        timestamp=timestamp,
        restored=False,
        permanently_deleted=False,
        artifact_name=artifact,
        project_type=project_type,
    )


def list_quarantine(db_path: Path = DB_PATH) -> list[QuarantineRecord]:
    init_quarantine_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, original_path, quarantine_path, size_bytes, reason, timestamp, restored, permanently_deleted
            , artifact_name, project_type
            FROM quarantine_records
            ORDER BY id DESC
            """
        ).fetchall()
    return [_record_from_row(row) for row in rows]


def restore_item(quarantine_id: int, db_path: Path = DB_PATH) -> QuarantineRecord:
    init_quarantine_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, original_path, quarantine_path, size_bytes, reason, timestamp, restored, permanently_deleted
            , artifact_name, project_type
            FROM quarantine_records
            WHERE id = ?
            """,
            (quarantine_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Unknown quarantine id: {quarantine_id}")
        record = _record_from_row(row)
        if record.restored:
            return record
        if record.permanently_deleted:
            raise ValueError("Cannot restore a permanently deleted item.")
        source = Path(record.quarantine_path)
        destination = Path(record.original_path)
        if not source.exists():
            raise FileNotFoundError(record.quarantine_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"Restore target already exists: {destination}")
        shutil.move(str(source), str(destination))
        conn.execute("UPDATE quarantine_records SET restored = 1 WHERE id = ?", (quarantine_id,))
    return record.model_copy(update={"restored": True})


def permanently_delete_item(quarantine_id: int, db_path: Path = DB_PATH) -> QuarantineRecord:
    """Permanently remove a quarantined item from disk and mark the DB record as deleted.

    The record is NOT removed from the database so the audit trail is preserved.
    """
    init_quarantine_db(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, original_path, quarantine_path, size_bytes, reason, timestamp, restored, permanently_deleted
            , artifact_name, project_type
            FROM quarantine_records
            WHERE id = ?
            """,
            (quarantine_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Unknown quarantine id: {quarantine_id}")
        record = _record_from_row(row)
        if record.restored:
            raise ValueError("Cannot permanently delete an item that has already been restored.")
        if record.permanently_deleted:
            return record  # Already gone, idempotent

        quarantine_path = Path(record.quarantine_path)
        if quarantine_path.exists():
            if quarantine_path.is_dir():
                shutil.rmtree(str(quarantine_path))
            else:
                quarantine_path.unlink()

        conn.execute(
            "UPDATE quarantine_records SET permanently_deleted = 1 WHERE id = ?",
            (quarantine_id,),
        )

    return record.model_copy(update={"permanently_deleted": True})
