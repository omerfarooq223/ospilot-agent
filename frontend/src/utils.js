export function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

export function healthScore(metrics) {
  const cpu = metrics.cpu_percent ?? 0;
  const ram = metrics.ram_percent ?? 0;
  const disk = metrics.disk_percent ?? 0;
  return Math.max(0, Math.round(100 - (cpu + ram + disk) / 3));
}

export function pressureScore(metrics) {
  const ram = metrics.ram_percent ?? 0;
  const cpu = metrics.cpu_percent ?? 0;
  if (ram >= 85 || cpu >= 85) return "High";
  if (ram >= 70 || cpu >= 70) return "Medium";
  return "Low";
}

export function riskClass(level) {
  switch (level) {
    case "Low":
      return "risk-low";
    case "Medium":
      return "risk-medium";
    case "High":
      return "risk-high";
    case "Needs Review":
      return "risk-review";
    default:
      return "risk-blocked";
  }
}
