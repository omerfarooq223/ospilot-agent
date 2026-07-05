import { useEffect, useState } from "react";
import { exportReport, exportReportFile } from "../api";

async function openDesktopPath(path) {
  try {
    const mod = await import("@tauri-apps/plugin-shell");
    await mod.open(path);
    return true;
  } catch (_) {
    return false;
  }
}

function canOpenDesktopPath() {
  return typeof window !== "undefined" && Boolean(window.__TAURI_INTERNALS__);
}

function eventLabel(type) {
  return String(type || "Audit Event")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/* ─── Animated toast notification ─────────────────────────────────────────── */
function PdfToast({ fileName, filePath, opened, onClose }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => handleClose(), 10000);
    return () => clearTimeout(t);
  }, []);

  function handleClose() {
    setVisible(false);
    setTimeout(onClose, 350);
  }

  async function openReport() {
    if (filePath) {
      await openDesktopPath(filePath);
    }
    handleClose();
  }

  return (
    <div
      style={{
        position: "fixed",
        bottom: "24px",
        right: "24px",
        zIndex: 9999,
        width: "360px",
        transform: visible ? "translateY(0) scale(1)" : "translateY(20px) scale(0.96)",
        opacity: visible ? 1 : 0,
        transition: "transform 0.35s cubic-bezier(0.34,1.56,0.64,1), opacity 0.35s ease",
        pointerEvents: visible ? "auto" : "none",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: "-1px",
          borderRadius: "16px",
          background: "linear-gradient(135deg, #14b8a6 0%, #7dd3fc 50%, #14b8a6 100%)",
          opacity: 0.35,
          filter: "blur(4px)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "relative",
          background: "linear-gradient(145deg, #111827 0%, #0d1420 100%)",
          border: "1px solid #1e2d3d",
          borderRadius: "16px",
          padding: "16px 18px",
          boxShadow: "0 20px 60px rgba(0,0,0,0.6), 0 4px 20px rgba(94,234,212,0.08)",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
          <div
            style={{
              flexShrink: 0,
              width: "40px",
              height: "40px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #14b8a6, #5eead4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 16px rgba(94,234,212,0.3)",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: "#ffffff", letterSpacing: "0.01em" }}>
              {opened ? "Report Opened" : "Report Saved"}
            </p>
            <p
              style={{ margin: "2px 0 0", fontSize: "11px", color: "#94a3b8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              title={fileName}
            >
              {filePath || `${fileName} saved to your downloads`}
            </p>
          </div>

          <button
            onClick={handleClose}
            style={{ flexShrink: 0, background: "none", border: "none", cursor: "pointer", padding: "2px", color: "#64748b", lineHeight: 1 }}
            title="Dismiss"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div style={{ marginTop: "14px", display: "flex", gap: "8px" }}>
          <button
            onClick={openReport}
            disabled={!filePath}
            style={{
              flex: 1,
              background: "linear-gradient(135deg, #14b8a6, #0e9488)",
              border: "none",
              borderRadius: "8px",
              padding: "8px 12px",
              color: "#ffffff",
              fontSize: "12px",
              fontWeight: 700,
              cursor: filePath ? "pointer" : "default",
              opacity: filePath ? 1 : 0.55,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "6px",
              letterSpacing: "0.02em",
              transition: "opacity 0.2s",
            }}
            onMouseEnter={(e) => {
              if (filePath) e.currentTarget.style.opacity = "0.85";
            }}
            onMouseLeave={(e) => {
              if (filePath) e.currentTarget.style.opacity = "1";
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            Open Report
          </button>
          <button
            onClick={handleClose}
            style={{
              background: "#1e2d3d",
              border: "1px solid #334155",
              borderRadius: "8px",
              padding: "8px 14px",
              color: "#94a3b8",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#e2e8f0")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#94a3b8")}
          >
            Dismiss
          </button>
        </div>

        <div style={{ marginTop: "12px", height: "3px", borderRadius: "2px", background: "#1e2d3d", overflow: "hidden" }}>
          <div
            style={{
              height: "100%",
              background: "linear-gradient(90deg, #14b8a6, #7dd3fc)",
              borderRadius: "2px",
              animation: "pdfToastTimer 10s linear forwards",
            }}
          />
        </div>
      </div>

      <style>{`
        @keyframes pdfToastTimer {
          from { width: 100%; }
          to   { width: 0%; }
        }
      `}</style>
    </div>
  );
}

/* ─── Main component ───────────────────────────────────────────────────────── */
export default function ReportView({ report, auditEvents }) {
  const [pdfToast, setPdfToast] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [htmlLoading, setHtmlLoading] = useState(false);

  async function handleExport(format) {
    if (!report) return;
    if (format === "pdf") setPdfLoading(true);
    else setHtmlLoading(true);

    try {
      if (format === "pdf" && canOpenDesktopPath()) {
        const saved = await exportReportFile(report, "pdf");
        const opened = await openDesktopPath(saved.path);
        if (opened) {
          setPdfToast({ fileName: saved.filename, filePath: saved.path, opened: true });
          return;
        }
      }

      const blob = await exportReport(report, format);
      const fileName = `ospilot-report.${format}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      anchor.click();
      URL.revokeObjectURL(url);

      if (format === "pdf") {
        setPdfToast({ fileName, filePath: "", opened: false });
      }
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      if (format === "pdf") setPdfLoading(false);
      else setHtmlLoading(false);
    }
  }

  async function handleShare() {
    if (!report) return;
    const text = `OS Pilot report: ${report.recovered || "0 B"} recovered, ${report.quarantined_count || 0} item(s) quarantined.`;
    if (navigator.share) {
      await navigator.share({ title: "OS Pilot Report", text });
      return;
    }
    await navigator.clipboard?.writeText(text);
  }

  const healthBefore = Number(report?.before_health_score || 0);
  const healthAfter = Number(report?.after_health_score || 0);
  const improvementWidth = report ? `${Math.max(0, Math.min(100, healthAfter))}%` : "0%";

  return (
    <>
      <section className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-bold text-white">Cleaning Reports</h2>
            <p className="text-sm font-medium text-slate-400">Performance metrics, exports, and local audit history.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              disabled={!report || htmlLoading}
              onClick={() => handleExport("html")}
            >
              {htmlLoading ? (
                <span className="flex items-center gap-2">
                  <SpinnerIcon /> Exporting…
                </span>
              ) : (
                "Export HTML"
              )}
            </button>

            <button
              type="button"
              className="btn-secondary"
              disabled={!report || pdfLoading}
              onClick={() => handleExport("pdf")}
            >
              {pdfLoading ? (
                <span className="flex items-center gap-2">
                  <SpinnerIcon /> Generating PDF…
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <PdfIcon />
                  Export PDF
                </span>
              )}
            </button>

            <button type="button" className="btn-primary" disabled={!report} onClick={handleShare}>
              Share Report
            </button>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <div className="panel p-6">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Recovered Space</p>
            <p className="mono mt-4 font-display text-5xl font-bold text-mint-300">
              {report?.recovered || "0 B"}
            </p>
            <p className="mt-4 text-sm font-bold text-mint-300">Local quarantine report</p>
          </div>
          <div className="panel p-6">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Before vs After</p>
            <div className="mono mt-5 flex justify-between text-sm font-bold text-slate-400">
              <span>Before: {report ? `${healthBefore}%` : "Pending"}</span>
              <span>After: {report ? `${healthAfter}%` : "Pending"}</span>
            </div>
            <div className="mt-2 h-3 overflow-hidden rounded-full bg-ink-700">
              <div className="h-full bg-sky-300" style={{ width: improvementWidth }} />
            </div>
            <p className="mt-5 text-sm font-medium text-slate-400">Run quarantine to generate a measured before/after report.</p>
          </div>
          <div className="panel p-6">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Health Score</p>
            <div className="mt-6 flex items-center gap-5">
              <div className="mono grid h-16 w-16 shrink-0 place-items-center rounded-full border-2 border-mint-300 font-bold text-white">
                {report?.after_health_score || "--"}%
              </div>
              <p className="text-sm font-medium text-slate-400">
                {report ? `${report.quarantined_count} item(s) quarantined in the latest cleanup.` : "No generated report yet."}
              </p>
            </div>
          </div>
        </div>

        <div className="table-shell">
          <div className="border-b border-ink-700 px-5 py-4">
            <h3 className="font-display text-xl font-bold text-white">Recent Audit Events</h3>
            <p className="mt-1 text-sm text-slate-500">
              These are real local backend audit log entries from scans, plans, quarantine actions, restores, and reports.
            </p>
          </div>
          {auditEvents?.length ? (
            <div className="divide-y divide-ink-700">
              {auditEvents.map((event, index) => (
                <div key={`${event.event_type}-${index}`} className="grid gap-3 px-5 py-5 md:grid-cols-[1fr_auto]">
                  <div className="flex min-w-0 gap-4">
                    <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full border border-mint-300 text-mint-300">+</div>
                    <div className="min-w-0">
                      <p className="font-bold text-white">{eventLabel(event.event_type)}</p>
                      <p className="truncate text-sm font-medium text-slate-500">
                        {typeof event.payload === "string" ? event.payload : JSON.stringify(event.payload)}
                      </p>
                    </div>
                  </div>
                  <p className="mono font-bold text-slate-400">{event.timestamp}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="px-5 py-8 text-sm text-slate-500">No audit events yet.</p>
          )}
        </div>

        {report ? (
          <details className="panel p-5">
            <summary className="cursor-pointer font-bold text-mint-300">Raw report data</summary>
            <pre className="mono mt-4 overflow-x-auto rounded-md border border-ink-700 bg-ink-950 p-4 text-xs text-slate-300">
              {JSON.stringify(report, null, 2)}
            </pre>
          </details>
        ) : null}
      </section>

      {pdfToast && (
        <PdfToast
          fileName={pdfToast.fileName}
          filePath={pdfToast.filePath}
          opened={pdfToast.opened}
          onClose={() => setPdfToast(null)}
        />
      )}
    </>
  );
}

function SpinnerIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      style={{ animation: "spin 0.9s linear infinite" }}
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </svg>
  );
}

function PdfIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="12" y1="18" x2="12" y2="12" />
      <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  );
}
