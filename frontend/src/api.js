const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || "Request failed");
  }
  return payload;
}

export function getHealth() {
  return request("/api/health");
}

export function runScan(folder, minSizeMb) {
  return request("/api/scan", {
    method: "POST",
    body: JSON.stringify({ folder, min_size_mb: minSizeMb }),
  });
}

export function startScan(folder, minSizeMb) {
  return request("/api/scan/start", {
    method: "POST",
    body: JSON.stringify({ folder, min_size_mb: minSizeMb }),
  });
}

export function getScanJob(jobId) {
  return request(`/api/scan/jobs/${jobId}`);
}

export function cancelScanJob(jobId) {
  return request(`/api/scan/jobs/${jobId}/cancel`, { method: "POST" });
}

export function quarantineItems(sessionId, approvedActionIds) {
  return request("/api/quarantine", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      approved_action_ids: approvedActionIds,
    }),
  });
}

export function quarantineAutopilot(sessionId) {
  return request("/api/autopilot/quarantine", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export function browseFolders(path) {
  const query = path ? `?path=${encodeURIComponent(path)}` : "";
  return request(`/api/folders${query}`);
}

export function listIgnoredFolders() {
  return request("/api/ignored-folders");
}

export function ignoreFolder(path) {
  return request("/api/ignored-folders", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export function unignoreFolder(path) {
  return request(`/api/ignored-folders?path=${encodeURIComponent(path)}`, { method: "DELETE" });
}

export function getScanHistory(limit = 30) {
  return request(`/api/scan-history?limit=${limit}`);
}

export async function exportReport(report, format = "html") {
  const response = await fetch(`${API_BASE}/api/report/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ report, format }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Report export failed");
  }
  return response.blob();
}

export function exportReportFile(report, format = "pdf") {
  return request("/api/report/export-file", {
    method: "POST",
    body: JSON.stringify({ report, format }),
  });
}

export function listQuarantine() {
  return request("/api/quarantine");
}

export function restoreItem(recordId) {
  return request(`/api/quarantine/${recordId}/restore`, { method: "POST" });
}

export function permanentlyDeleteItem(recordId) {
  return request(`/api/quarantine/${recordId}/delete`, { method: "POST" });
}

export function listAudit(limit = 10) {
  return request(`/api/audit?limit=${limit}`);
}

export function getSchedulerStatus() {
  return request("/api/scheduler");
}

export function enableWeeklyScan(payload) {
  return request("/api/scheduler/enable", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function disableWeeklyScan() {
  return request("/api/scheduler/disable", { method: "POST" });
}

export function runWeeklyScanNow(payload) {
  return request("/api/scheduler/run-now", {
    method: "POST",
    body: JSON.stringify(payload || {}),
  });
}
