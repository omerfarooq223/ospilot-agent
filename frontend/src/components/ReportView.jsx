import { exportReport } from "../api";

function eventLabel(type) {
  return String(type || "Audit Event")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function ReportView({ report, auditEvents }) {
  async function handleExport(format) {
    if (!report) return;
    const blob = await exportReport(report, format);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ospilot-report.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
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
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl font-bold text-white">Cleaning Reports</h2>
          <p className="text-sm font-semibold text-slate-300">Performance metrics, exports, and local audit history.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" disabled={!report} onClick={() => handleExport("html")}>
            Export HTML
          </button>
          <button type="button" className="btn-secondary" disabled={!report} onClick={() => handleExport("pdf")}>
            Export PDF
          </button>
          <button type="button" className="btn-primary" disabled={!report} onClick={handleShare}>
            Share Report
          </button>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="panel p-6">
          <p className="text-sm font-bold uppercase tracking-wide text-slate-400">Recovered Space</p>
          <p className="mt-4 font-display text-5xl font-bold text-mint-300">
            {report?.recovered || "0 B"}
          </p>
          <p className="mt-4 font-bold text-mint-300">Local quarantine report</p>
        </div>
        <div className="panel p-6">
          <p className="text-sm font-bold uppercase tracking-wide text-slate-400">Before vs After</p>
          <div className="mt-5 flex justify-between text-sm font-bold text-slate-400">
            <span>Before: {report ? `${healthBefore}%` : "Pending"}</span>
            <span>After: {report ? `${healthAfter}%` : "Pending"}</span>
          </div>
          <div className="mt-2 h-3 overflow-hidden rounded-full bg-[#333333]">
            <div className="h-full bg-sky-300" style={{ width: improvementWidth }} />
          </div>
          <p className="mt-5 text-sm font-semibold text-slate-300">Run quarantine to generate a measured before/after report.</p>
        </div>
        <div className="panel p-6">
          <p className="text-sm font-bold uppercase tracking-wide text-slate-400">Health Score</p>
          <div className="mt-6 flex items-center gap-5">
            <div className="grid h-16 w-16 place-items-center rounded-full border-4 border-mint-300 font-bold text-white">
              {report?.after_health_score || "--"}%
            </div>
            <p className="font-semibold text-slate-300">
              {report ? `${report.quarantined_count} item(s) quarantined in the latest cleanup.` : "No generated report yet."}
            </p>
          </div>
        </div>
      </div>

      <div className="table-shell">
        <div className="border-b border-[#303a39] px-5 py-4">
          <h3 className="font-display text-xl font-bold text-white">Recent Audit Events</h3>
          <p className="mt-1 text-sm text-slate-500">
            These are real local backend audit log entries from scans, plans, quarantine actions, restores, and reports.
          </p>
        </div>
        {auditEvents?.length ? (
          <div className="divide-y divide-[#303a39]">
            {auditEvents.map((event, index) => (
              <div key={`${event.event_type}-${index}`} className="grid gap-3 px-5 py-5 md:grid-cols-[1fr_auto]">
                <div className="flex min-w-0 gap-4">
                  <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full border border-mint-300 text-mint-300">+</div>
                  <div className="min-w-0">
                    <p className="font-bold text-white">{eventLabel(event.event_type)}</p>
                    <p className="truncate text-sm font-semibold text-slate-500">
                      {typeof event.payload === "string" ? event.payload : JSON.stringify(event.payload)}
                    </p>
                  </div>
                </div>
                <p className="font-bold text-slate-300">{event.timestamp}</p>
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
          <pre className="mt-4 overflow-x-auto border border-[#303a39] bg-[#101212] p-4 text-xs text-slate-300">
            {JSON.stringify(report, null, 2)}
          </pre>
        </details>
      ) : null}
    </section>
  );
}
