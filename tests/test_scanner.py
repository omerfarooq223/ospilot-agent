from __future__ import annotations

from pathlib import Path

from core.models import RebuildabilityLevel, RiskLevel
from core.scanner import detect_project_type, find_developer_junk, rebuildability_for, scan_selected_folder


def test_scanner_detects_developer_junk(tmp_path: Path) -> None:
    node_modules = tmp_path / "app" / "node_modules"
    pycache = tmp_path / "app" / "__pycache__"
    node_modules.mkdir(parents=True)
    pycache.mkdir(parents=True)
    (node_modules / "lib.js").write_text("demo")
    (pycache / "mod.pyc").write_text("demo")

    items = find_developer_junk(tmp_path)
    names = {Path(item.path).name for item in items}

    assert "node_modules" in names
    assert "__pycache__" in names


def test_scanner_adds_rebuildability_context_for_node_project(tmp_path: Path) -> None:
    project = tmp_path / "app"
    node_modules = project / "node_modules"
    node_modules.mkdir(parents=True)
    (project / "package.json").write_text("{}")
    (project / "package-lock.json").write_text("{}")
    (node_modules / "lib.js").write_text("demo")

    item = next(item for item in find_developer_junk(tmp_path) if Path(item.path).name == "node_modules")

    assert item.project_type == "Node"
    assert item.rebuildability == RebuildabilityLevel.HIGH
    assert "package-lock.json" in item.evidence
    assert item.recovery_recipe == "Rebuild with: npm ci"


def test_detect_project_type_for_python_project(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pandas")
    project_type, evidence = detect_project_type(tmp_path)

    assert project_type == "Python"
    assert evidence == ["requirements.txt"]


def test_scan_selected_folder_blocks_system_path() -> None:
    items = scan_selected_folder("/System")
    assert len(items) == 1
    assert items[0].risk_level == RiskLevel.BLOCKED


def test_generic_build_folder_without_project_evidence_is_not_high_rebuildability(tmp_path: Path) -> None:
    build = tmp_path / "build"
    build.mkdir()

    rebuildability, recipe, evidence = rebuildability_for(build, tmp_path, "developer_junk")

    assert rebuildability == RebuildabilityLevel.UNKNOWN
    assert "Review manually" in recipe
    assert evidence == []


def test_gradle_cache_requires_gradle_project_evidence(tmp_path: Path) -> None:
    gradle = tmp_path / ".gradle"
    gradle.mkdir()
    rebuildability, _recipe, _evidence = rebuildability_for(gradle, tmp_path, "developer_junk")
    assert rebuildability == RebuildabilityLevel.UNKNOWN

    (tmp_path / "build.gradle").write_text("plugins {}")
    rebuildability, recipe, evidence = rebuildability_for(gradle, tmp_path, "developer_junk")
    assert rebuildability == RebuildabilityLevel.HIGH
    assert "gradlew" in recipe
    assert "build.gradle" in evidence
