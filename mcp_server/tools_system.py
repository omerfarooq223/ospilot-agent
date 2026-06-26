from __future__ import annotations

from pathlib import Path

import psutil

from core.models import ProcessInfo, SystemMetrics


def get_disk_usage(path: str | Path = ".") -> dict[str, int | float]:
    usage = psutil.disk_usage(str(Path(path).resolve()))
    return {"total": usage.total, "used": usage.used, "free": usage.free, "percent": usage.percent}


def get_system_metrics() -> SystemMetrics:
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home()))
    return SystemMetrics(
        cpu_percent=cpu,
        ram_percent=ram.percent,
        disk_percent=disk.percent,
        available_disk_bytes=disk.free,
        total_disk_bytes=disk.total,
    )


def get_process_snapshot(limit: int = 20) -> list[ProcessInfo]:
    processes: list[ProcessInfo] = []
    try:
        iterator = psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status", "cmdline"])
        for proc in iterator:
            try:
                info = proc.info
                command = " ".join(info.get("cmdline") or [])[:160]
                memory_mb = (info.get("memory_info").rss / (1024 * 1024)) if info.get("memory_info") else 0.0
                processes.append(
                    ProcessInfo(
                        pid=info.get("pid") or 0,
                        name=info.get("name") or "unknown",
                        cpu_percent=float(info.get("cpu_percent") or 0.0),
                        memory_mb=round(memory_mb, 2),
                        status=info.get("status") or "unknown",
                        command_preview=command,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, PermissionError):
                continue
    except PermissionError:
        return []
    processes.sort(key=lambda item: item.memory_mb, reverse=True)
    return processes[:limit]


def get_top_processes(metric: str = "memory", limit: int = 10) -> list[ProcessInfo]:
    processes = get_process_snapshot(limit=200)
    key = (lambda item: item.cpu_percent) if metric == "cpu" else (lambda item: item.memory_mb)
    return sorted(processes, key=key, reverse=True)[:limit]


def analyze_performance_pressure() -> dict[str, str | float | int]:
    metrics = get_system_metrics()
    pressure = "Low"
    if metrics.ram_percent >= 85 or metrics.cpu_percent >= 85:
        pressure = "High"
    elif metrics.ram_percent >= 70 or metrics.cpu_percent >= 70:
        pressure = "Medium"
    return {
        "pressure": pressure,
        "cpu_percent": metrics.cpu_percent,
        "ram_percent": metrics.ram_percent,
        "disk_percent": metrics.disk_percent,
    }


def detect_idle_heavy_apps(memory_threshold_mb: int = 750, limit: int = 5) -> list[ProcessInfo]:
    processes = get_process_snapshot(limit=200)
    return [proc for proc in processes if proc.memory_mb >= memory_threshold_mb and proc.cpu_percent <= 10][:limit]
