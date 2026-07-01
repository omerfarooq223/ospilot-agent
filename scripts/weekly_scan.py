#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.weekly_report import run_weekly_scan  # noqa: E402


def main() -> int:
    result = run_weekly_scan()
    if result.get("skipped"):
        print(result.get("reason", "Weekly scan skipped."))
        return 0
    reports = result.get("reports", {})
    print(f"Weekly scan complete. Scanned {result.get('folders_scanned')} folder(s).")
    if reports:
        print(f"Markdown report: {reports.get('markdown')}")
        print(f"HTML report: {reports.get('html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
