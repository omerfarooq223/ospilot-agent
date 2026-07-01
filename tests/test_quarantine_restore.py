from __future__ import annotations

import pytest
from pathlib import Path

from core.quarantine_db import quarantine_item, restore_item
from mcp_server.safety_rules import path_identity


def test_quarantine_and_restore_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    target = tmp_path / "project" / "__pycache__"
    target.mkdir(parents=True)
    (target / "mod.pyc").write_text("cached")

    record = quarantine_item(target, "test cache", db_path=db_path, artifact_name="__pycache__", project_type="Python")

    assert not target.exists()
    assert Path(record.quarantine_path).exists()
    assert record.artifact_name == "__pycache__"
    assert record.project_type == "Python"

    restored = restore_item(record.id, db_path=db_path)

    assert restored.restored
    assert restored.artifact_name == "__pycache__"
    assert restored.project_type == "Python"
    assert target.exists()
    assert (target / "mod.pyc").read_text() == "cached"


def test_quarantine_blocks_path_identity_change(tmp_path: Path) -> None:
    db_path = tmp_path / "test.sqlite3"
    target = tmp_path / "project" / "__pycache__"
    target.mkdir(parents=True)
    expected = path_identity(target)

    moved_original = tmp_path / "project" / "__pycache___old"
    target.rename(moved_original)
    target.mkdir()

    with pytest.raises(ValueError, match="changed after scan"):
        quarantine_item(target, "changed cache", db_path=db_path, expected_identity=expected)
