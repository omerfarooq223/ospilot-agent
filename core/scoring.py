from __future__ import annotations

from core.models import SystemMetrics


def pressure_score(metrics: SystemMetrics) -> int:
    weighted = (metrics.ram_percent * 0.45) + (metrics.cpu_percent * 0.35) + (metrics.disk_percent * 0.20)
    return max(0, min(100, round(weighted)))


def health_score(metrics: SystemMetrics) -> int:
    return max(0, min(100, 100 - pressure_score(metrics)))


def format_bytes(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
