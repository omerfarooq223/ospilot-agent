from __future__ import annotations

import os
from pathlib import Path

from core.models import RebuildabilityLevel, RiskLevel, ScanItem
from mcp_server.safety_rules import classify_file_risk, is_protected_path, normalize_path, path_identity


DEVELOPER_JUNK_NAMES = {
    # JavaScript / TypeScript
    "node_modules",
    ".next",
    ".turbo",
    ".nx",
    ".parcel-cache",
    ".angular",
    ".svelte-kit",
    # Python
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ipynb_checkpoints",
    ".tox",
    ".eggs",
    # Build outputs (generic)
    "dist",
    "build",
    ".cache",
    "coverage",
    "__snapshots__",
    # Rust
    "target",
    # Java / Kotlin
    ".gradle",
    # Dart / Flutter
    ".dart_tool",
    ".pub-cache",
}

PROJECT_MARKERS = {
    # JavaScript / TypeScript
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    # Python
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "environment.yml",
    "environment.yaml",
    "setup.py",
    # Rust
    "Cargo.toml",
    "Cargo.lock",
    # Java / Kotlin
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    # Go
    "go.mod",
    # Ruby
    "Gemfile",
    # PHP
    "composer.json",
    # Dart / Flutter
    "pubspec.yaml",
}


def _contains_notebook(path: Path) -> bool:
    try:
        return any(child.is_file() and child.suffix == ".ipynb" for child in path.iterdir())
    except OSError:
        return False


def detect_project_root(path: str | Path) -> Path:
    current = Path(path)
    if current.is_file():
        current = current.parent
    for parent in [current, *current.parents]:
        try:
            names = {child.name for child in parent.iterdir()}
        except OSError:
            continue
        if names.intersection(PROJECT_MARKERS) or _contains_notebook(parent):
            return parent
    return current.parent if current.name in DEVELOPER_JUNK_NAMES else current


def detect_project_type(project_root: str | Path) -> tuple[str, list[str]]:
    root = Path(project_root)
    try:
        names = {child.name for child in root.iterdir()}
    except OSError:
        return "Unknown", []

    evidence: list[str] = []

    # Next.js (must check before generic Node)
    next_markers = {"next.config.js", "next.config.mjs", "next.config.ts"}
    if names.intersection(next_markers):
        evidence.extend(sorted(names.intersection(next_markers)))
        if "package.json" in names:
            evidence.append("package.json")
        return "Next.js", evidence

    # Node
    if "package.json" in names:
        evidence.append("package.json")
        for lockfile in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock"):
            if lockfile in names:
                evidence.append(lockfile)
        return "Node", evidence

    # Python
    for marker in ("pyproject.toml", "requirements.txt", "Pipfile", "environment.yml", "environment.yaml", "setup.py"):
        if marker in names:
            evidence.append(marker)
    if evidence:
        return "Python", evidence

    # Jupyter (checked after Python so a notebook-only repo lands here)
    if _contains_notebook(root):
        return "Jupyter", ["notebook files"]

    # Rust
    if "Cargo.toml" in names:
        evidence.append("Cargo.toml")
        if "Cargo.lock" in names:
            evidence.append("Cargo.lock")
        return "Rust", evidence

    # Java / Kotlin — Maven
    if "pom.xml" in names:
        return "Java (Maven)", ["pom.xml"]

    # Java / Kotlin — Gradle
    for gf in ("build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"):
        if gf in names:
            evidence.append(gf)
    if evidence:
        return "Java (Gradle)", evidence

    # Go
    if "go.mod" in names:
        return "Go", ["go.mod"]

    # Ruby
    if "Gemfile" in names:
        return "Ruby", ["Gemfile"]

    # PHP
    if "composer.json" in names:
        return "PHP", ["composer.json"]

    # Dart / Flutter
    if "pubspec.yaml" in names:
        return "Dart/Flutter", ["pubspec.yaml"]

    return "Unknown", []


def rebuildability_for(path: str | Path, project_root: str | Path, item_type: str) -> tuple[RebuildabilityLevel, str, list[str]]:
    target = Path(path)
    root = Path(project_root)
    _project_type, evidence = detect_project_type(root)
    try:
        names = {child.name for child in root.iterdir()}
    except OSError:
        names = set()

    # --- JavaScript / TypeScript ---
    if target.name == "node_modules":
        if "package-lock.json" in names:
            return RebuildabilityLevel.HIGH, "Rebuild with: npm ci", evidence
        if "pnpm-lock.yaml" in names:
            return RebuildabilityLevel.HIGH, "Rebuild with: pnpm install --frozen-lockfile", evidence
        if "yarn.lock" in names:
            return RebuildabilityLevel.HIGH, "Rebuild with: yarn install --frozen-lockfile", evidence
        if "package.json" in names:
            return RebuildabilityLevel.MEDIUM, "Rebuild with: npm install", evidence

    js_markers = {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
    }
    python_markers = {"pyproject.toml", "requirements.txt", "Pipfile", "environment.yml", "environment.yaml", "setup.py"}
    gradle_markers = {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}
    dart_markers = {"pubspec.yaml"}

    if target.name in {".turbo", ".nx", ".parcel-cache", ".angular", ".svelte-kit"} and names.intersection(js_markers):
        return RebuildabilityLevel.HIGH, "Generated JS tooling cache. Recreate by rerunning your build.", evidence

    # --- Python ---
    if target.name in {".venv", "venv"}:
        if "requirements.txt" in names:
            return RebuildabilityLevel.HIGH, "Rebuild with: python -m venv .venv && pip install -r requirements.txt", evidence
        if "environment.yml" in names or "environment.yaml" in names:
            env_file = "environment.yml" if "environment.yml" in names else "environment.yaml"
            return RebuildabilityLevel.HIGH, f"Rebuild with: conda env create -f {env_file}", evidence
        if "pyproject.toml" in names:
            return RebuildabilityLevel.MEDIUM, "Rebuild with: python -m venv .venv && pip install -e .", evidence

    if target.name == ".tox" and names.intersection(python_markers):
        return RebuildabilityLevel.HIGH, "Rebuild with: tox", evidence

    if target.name == ".eggs" and names.intersection(python_markers):
        return RebuildabilityLevel.HIGH, "Recreated automatically on next setup.py install / pip install -e .", evidence

    # --- Rust ---
    if target.name == "target" and "Cargo.toml" in names:
        return RebuildabilityLevel.HIGH, "Rebuild with: cargo build", evidence

    # --- Java / Kotlin ---
    if target.name == ".gradle" and names.intersection(gradle_markers):
        return RebuildabilityLevel.HIGH, "Rebuild with: ./gradlew build (Gradle cache will be refetched)", evidence

    # --- Generic generated / test outputs ---
    if target.name in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ipynb_checkpoints",
                       "dist", "build", ".next", ".cache", "coverage", "__snapshots__"}:
        if not names.intersection(PROJECT_MARKERS):
            return RebuildabilityLevel.UNKNOWN, "Generated-looking folder without nearby project evidence. Review manually.", evidence
        return RebuildabilityLevel.HIGH, "Generated output. Recreate by rerunning tests, notebooks, or the project build.", evidence

    if target.name in {".dart_tool", ".pub-cache"} and names.intersection(dart_markers):
        return RebuildabilityLevel.HIGH, "Generated Dart/Flutter tooling cache. Recreate with pub get or flutter pub get.", evidence

    # --- Large files ---
    if item_type == "large_file":
        lowered = target.name.lower()
        if any(token in lowered for token in ("checkpoint", "model", ".pkl", ".pt", ".pth", ".onnx", ".h5")):
            return RebuildabilityLevel.NOT_REBUILDABLE, "Likely model/checkpoint artifact. Review manually before moving.", evidence
        return RebuildabilityLevel.UNKNOWN, "Large user file. Review manually before moving.", evidence

    return RebuildabilityLevel.UNKNOWN, "No reliable rebuild recipe found. Review manually.", evidence


def project_context_for(path: str | Path, item_type: str) -> tuple[str, str, RebuildabilityLevel, str, list[str]]:
    project_root = detect_project_root(path)
    project_type, base_evidence = detect_project_type(project_root)
    rebuildability, recipe, evidence = rebuildability_for(path, project_root, item_type)
    merged_evidence = list(dict.fromkeys([*base_evidence, *evidence]))
    return str(project_root), project_type, rebuildability, recipe, merged_evidence


def _scan_item(path: Path, item_type: str, size_bytes: int, risk_level: RiskLevel, reason: str, action: str) -> ScanItem:
    project_root, project_type, rebuildability, recipe, evidence = project_context_for(path, item_type)
    identity = path_identity(path)
    return ScanItem(
        path=str(path),
        item_type=item_type,
        size_bytes=size_bytes,
        risk_level=risk_level,
        reason=reason,
        recommended_action=action,
        project_root=project_root,
        project_type=project_type,
        rebuildability=rebuildability,
        recovery_recipe=recipe,
        evidence=evidence,
        **identity,
    )


def get_path_size(path: str | Path) -> int:
    """Sum the size of all files under *path* (or the file itself)."""
    target = Path(path)
    if not target.exists():
        return 0
    if target.is_file():
        try:
            return target.stat().st_size
        except OSError:
            return 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(target, followlinks=False):
        for fname in filenames:
            try:
                total += (Path(dirpath) / fname).stat().st_size
            except OSError:
                continue
    return total


def find_developer_junk(root_path: str | Path) -> list[ScanItem]:
    """Return junk dirs found under root_path (used by scan_cache_folders)."""
    root = Path(normalize_path(root_path))
    if is_protected_path(root) or not root.exists() or not root.is_dir():
        return []
    items: list[ScanItem] = []
    for dirpath, dirnames, _filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        remaining: list[str] = []
        for dname in dirnames:
            child = current / dname
            if dname in DEVELOPER_JUNK_NAMES:
                risk = classify_file_risk(child)
                _project_root, project_type, _rebuildability, _recipe, _evidence = project_context_for(child, "developer_junk")
                items.append(
                    _scan_item(
                        child,
                        "developer_junk",
                        get_path_size(child),
                        risk,
                        f"{dname} is a generated developer artifact in a {project_type} workspace.",
                        "Quarantine after review" if risk != RiskLevel.BLOCKED else "Blocked",
                    )
                )
                # Prune: don't recurse into this subtree
            else:
                remaining.append(dname)
        dirnames[:] = remaining
    return items


def scan_large_files(root_path: str | Path, min_size_mb: int = 30) -> list[ScanItem]:
    """Find files >= min_size_mb, skipping inside junk dirs."""
    root = Path(normalize_path(root_path))
    if is_protected_path(root) or not root.exists() or not root.is_dir():
        return []
    threshold = min_size_mb * 1024 * 1024
    items: list[ScanItem] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        # Prune junk dirs so we don't scan inside them
        dirnames[:] = [d for d in dirnames if d not in DEVELOPER_JUNK_NAMES]
        for fname in filenames:
            fpath = current / fname
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            if size >= threshold:
                _project_root, project_type, _rebuildability, _recipe, _evidence = project_context_for(fpath, "large_file")
                items.append(
                    _scan_item(
                        fpath,
                        "large_file",
                        size,
                        RiskLevel.NEEDS_REVIEW,
                        f"Large file found in a {project_type} workspace.",
                        "Review manually",
                    )
                )
    return items


def scan_cache_folders(root_path: str | Path) -> list[ScanItem]:
    return [
        item
        for item in find_developer_junk(root_path)
        if Path(item.path).name in {"__pycache__", ".pytest_cache", ".mypy_cache", ".ipynb_checkpoints", ".cache"}
    ]


def scan_selected_folder(root_path: str | Path, min_size_mb: int = 30) -> list[ScanItem]:
    """Single-pass scan combining junk-dir detection and large-file detection.

    Uses os.walk with topdown=True so that junk directories are pruned before
    os.walk recurses into them. This means a 400 k-file tree with a large
    node_modules subtree is traversed only once, and the node_modules contents
    are never visited by the main walk (only by get_path_size for that one dir).
    """
    root = Path(normalize_path(root_path))
    if is_protected_path(root):
        return [
            ScanItem(
                path=str(root),
                item_type="blocked_path",
                size_bytes=0,
                risk_level=RiskLevel.BLOCKED,
                reason="Protected system path cannot be scanned.",
                recommended_action="Choose a user-owned folder",
            )
        ]

    threshold = min_size_mb * 1024 * 1024
    junk_items: list[ScanItem] = []
    large_items: list[ScanItem] = []
    seen_paths: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)

        # Detect junk dirs and prune them from further recursion
        remaining: list[str] = []
        for dname in dirnames:
            child = current / dname
            child_str = str(child)
            if dname in DEVELOPER_JUNK_NAMES and child_str not in seen_paths:
                seen_paths.add(child_str)
                risk = classify_file_risk(child)
                size = get_path_size(child)
                _project_root, project_type, _rebuildability, _recipe, _evidence = project_context_for(child, "developer_junk")
                junk_items.append(
                    _scan_item(
                        child,
                        "developer_junk",
                        size,
                        risk,
                        f"{dname} is a generated developer artifact in a {project_type} workspace.",
                        "Quarantine after review" if risk != RiskLevel.BLOCKED else "Blocked",
                    )
                )
                # Pruned: os.walk will not descend into this directory
            else:
                remaining.append(dname)
        dirnames[:] = remaining

        # Check files at this level for large-file threshold
        for fname in filenames:
            fpath = current / fname
            fpath_str = str(fpath)
            if fpath_str in seen_paths:
                continue
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            if size >= threshold:
                seen_paths.add(fpath_str)
                _project_root, project_type, _rebuildability, _recipe, _evidence = project_context_for(fpath, "large_file")
                large_items.append(
                    _scan_item(
                        fpath,
                        "large_file",
                        size,
                        RiskLevel.NEEDS_REVIEW,
                        f"Large file found in a {project_type} workspace.",
                        "Review manually",
                    )
                )

    return junk_items + large_items


def estimate_cleanup_space(items: list[ScanItem]) -> int:
    return sum(item.size_bytes for item in items if item.risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM})
