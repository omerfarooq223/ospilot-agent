from __future__ import annotations

import shutil
from pathlib import Path


DEMO_ROOT = Path(__file__).resolve().parent / "demo_workspace"


def _write_dummy_file(path: Path, size_kb: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunk = b"OSPilot demo data\n" * 64
    remaining = size_kb * 1024
    with path.open("wb") as handle:
        while remaining > 0:
            data = chunk[: min(len(chunk), remaining)]
            handle.write(data)
            remaining -= len(data)


def create_demo_workspace(reset: bool = False) -> Path:
    if reset and DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)
    DEMO_ROOT.mkdir(parents=True, exist_ok=True)

    folders = {
        "old_react_app/node_modules/react": 256,
        "old_react_app/node_modules/vite": 256,
        "old_python_project/.venv/lib/python/site-packages": 512,
        "notebooks/.ipynb_checkpoints": 64,
        "package_build/dist": 128,
        "package_build/build": 128,
        "python_cache/__pycache__": 64,
        "temp_logs": 64,
        "large_files": 1024,
    }
    for folder in ("old_react_app", "old_python_project", "notebooks", "package_build"):
        (DEMO_ROOT / folder).mkdir(parents=True, exist_ok=True)
    (DEMO_ROOT / "old_react_app" / "package.json").write_text('{"scripts":{"build":"vite build"},"dependencies":{"react":"latest"}}\n')
    (DEMO_ROOT / "old_react_app" / "package-lock.json").write_text('{"lockfileVersion":3}\n')
    (DEMO_ROOT / "old_python_project" / "requirements.txt").write_text("pandas\nscikit-learn\n")
    (DEMO_ROOT / "notebooks" / "analysis.ipynb").write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}\n')
    (DEMO_ROOT / "package_build" / "pyproject.toml").write_text("[project]\nname = \"demo-package\"\nversion = \"0.1.0\"\n")
    for folder, size_kb in folders.items():
        _write_dummy_file(DEMO_ROOT / folder / "demo_blob.bin", size_kb)
    _write_dummy_file(DEMO_ROOT / "large_files" / "old_screen_recording.mov", 2048)
    return DEMO_ROOT


if __name__ == "__main__":
    print(create_demo_workspace(reset=True))
