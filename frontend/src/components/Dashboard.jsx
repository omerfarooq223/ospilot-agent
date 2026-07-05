import { formatBytes, healthScore, pressureScore, riskClass } from "../utils";

function RingScore({ score }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div
      className="grid h-24 w-24 shrink-0 place-items-center rounded-full"
      style={{ background: `conic-gradient(#eab766 ${pct * 3.6}deg, #1c2422 0deg)` }}
    >
      <div className="grid h-16 w-16 place-items-center rounded-full bg-ink-900">
        <div className="text-center">
          <p className="font-display text-3xl font-bold text-white">{pct}</p>
          <p className="mono text-[10px] text-slate-500">/100</p>
        </div>
      </div>
    </div>
  );
}

function StatTile({ label, value, tone = "muted" }) {
  const color = tone === "mint" ? "text-mint-300 border-l-mint-300" : "text-white border-l-transparent";
  return (
    <div className={`min-h-32 rounded-md border border-ink-700 bg-ink-900 p-4 border-l-2 ${color}`}>
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mono mt-16 text-3xl font-bold ${tone === "mint" ? "text-mint-300" : "text-white"}`}>{value}</p>
    </div>
  );
}

function Recommendation({ title, text, value, tone = "mint" }) {
  const accents = {
    mint: "border-t-mint-300 text-mint-300",
    amber: "border-t-[#eab766] text-[#f6cf98]",
    rose: "border-t-[#ff8f83] text-[#ffbcb2]",
  };
  return (
    <article className={`rounded-md border border-ink-700 border-t-2 bg-ink-900 p-5 ${accents[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <h4 className="font-display text-lg font-bold text-white">{title}</h4>
        <span className="channel-dot mt-2" style={{ background: tone === "rose" ? "#ff8f83" : tone === "amber" ? "#eab766" : "#3fd6bb" }} />
      </div>
      <p className="mt-3 min-h-12 text-sm font-medium leading-relaxed text-slate-400">{text}</p>
      <div className="mt-5 flex items-end justify-between gap-3">
        <p className={`mono text-2xl font-bold ${accents[tone].split(" ")[1]}`}>{value}</p>
      </div>
    </article>
  );
}

function RecentHistory({ scanHistory }) {
  const rows = scanHistory?.slice(0, 3) || [];

  return (
    <div className="table-shell">
      <div className="flex items-center justify-between border-b border-ink-700 px-5 py-4">
        <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300">Recent Scan History</h3>
        <span className="mono text-sm font-bold text-mint-300">{rows.length} scans</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left">
          <thead className="text-xs uppercase text-slate-500">
            <tr className="border-b border-ink-700">
              <th className="px-5 py-3">Workspace</th>
              <th className="px-5 py-3">Last Scan</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((item, index) => {
                const label = item.recoverable_label || (item.recoverable_bytes ? formatBytes(item.recoverable_bytes) : "0 B");
                const tone = item.recoverable_bytes > 0 ? "bg-[#eab766]/15 text-[#f6cf98]" : "bg-mint-500/15 text-mint-300";
                return (
                  <tr key={`${item.timestamp}-${index}`} className="border-b border-ink-700 last:border-0">
                    <td className="mono max-w-[360px] break-all px-5 py-3 text-sm font-bold text-white">{item.folder || item.path || "Workspace"}</td>
                    <td className="px-5 py-3 font-medium text-slate-400">{item.timestamp || item.date || "Recent"}</td>
                    <td className="px-5 py-3">
                      <span className={`status-pill normal-case ${tone}`}>{label}</span>
                    </td>
                    <td className="px-5 py-3 text-right text-sm text-slate-500">Recorded</td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="4" className="px-5 py-8 text-center text-sm text-slate-500">
                  No scan history yet. Run a real folder scan to populate this table.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatPercent(value) {
  const number = Number(value || 0);
  return `${number.toFixed(number >= 10 ? 0 : 1)}%`;
}

function ProcessRow({ process, metric }) {
  const value = metric === "cpu" ? formatPercent(process.cpu_percent) : `${Number(process.memory_mb || 0).toFixed(0)} MB`;
  const max = metric === "cpu" ? 100 : 4096;
  const raw = metric === "cpu" ? Number(process.cpu_percent || 0) : Number(process.memory_mb || 0);
  const width = Math.max(4, Math.min(100, (raw / max) * 100));

  return (
    <div className="border-b border-ink-700 px-4 py-3 last:border-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-display text-base font-bold text-white" title={process.command_preview || process.name}>
            {process.name || "Unknown process"}
          </p>
          <p className="mono mt-1 truncate text-xs text-slate-500" title={process.command_preview || `PID ${process.pid}`}>
            PID {process.pid || "--"} {process.status ? `- ${process.status}` : ""}
          </p>
        </div>
        <p className="mono shrink-0 text-sm font-bold text-mint-300">{value}</p>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-700">
        <div className="h-full rounded-full bg-mint-300" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function ProcessList({ title, subtitle, processes, metric }) {
  const rows = processes?.slice(0, 5) || [];

  return (
    <div className="rounded-md border border-ink-700 bg-ink-900">
      <div className="border-b border-ink-700 px-4 py-3">
        <h4 className="text-sm font-bold uppercase tracking-wide text-slate-300">{title}</h4>
        <p className="mt-1 text-xs font-medium text-slate-500">{subtitle}</p>
      </div>
      {rows.length ? (
        rows.map((process) => <ProcessRow key={`${metric}-${process.pid}-${process.name}`} process={process} metric={metric} />)
      ) : (
        <p className="px-4 py-8 text-center text-sm text-slate-500">Run a scan to load live process data.</p>
      )}
    </div>
  );
}

function SystemHealthPanel({ observation }) {
  const metrics = observation?.metrics || {};
  const idleApps = observation?.idle_heavy_apps?.slice(0, 3) || [];

  return (
    <div className="panel p-5">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300">System Health</h3>
          <p className="mt-2 text-sm font-medium text-slate-400">Live RAM, CPU, and process pressure from the latest scan.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-right sm:grid-cols-3">
          <div className="rounded-md border border-ink-700 bg-ink-900 px-3 py-2">
            <p className="text-[11px] font-bold uppercase text-slate-500">CPU</p>
            <p className="mono text-lg font-bold text-mint-300">{observation ? formatPercent(metrics.cpu_percent) : "--"}</p>
          </div>
          <div className="rounded-md border border-ink-700 bg-ink-900 px-3 py-2">
            <p className="text-[11px] font-bold uppercase text-slate-500">RAM</p>
            <p className="mono text-lg font-bold text-[#f6cf98]">{observation ? formatPercent(metrics.ram_percent) : "--"}</p>
          </div>
          <div className="rounded-md border border-ink-700 bg-ink-900 px-3 py-2">
            <p className="text-[11px] font-bold uppercase text-slate-500">Disk</p>
            <p className="mono text-lg font-bold text-[#ffbcb2]">{observation ? formatPercent(metrics.disk_percent) : "--"}</p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ProcessList title="Top RAM Apps" subtitle="Highest memory use right now" processes={observation?.top_memory_processes} metric="memory" />
        <ProcessList title="Top CPU Apps" subtitle="Highest processor use right now" processes={observation?.top_cpu_processes} metric="cpu" />
      </div>

      {idleApps.length ? (
        <div className="mt-4 rounded-md border border-ink-700 bg-ink-900 px-4 py-3">
          <p className="text-sm font-bold uppercase tracking-wide text-slate-300">Idle Heavy Apps</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {idleApps.map((process) => (
              <span key={`idle-${process.pid}-${process.name}`} className="status-pill bg-[#eab766]/15 normal-case text-[#f6cf98]" title={process.command_preview || process.name}>
                {process.name}: {Number(process.memory_mb || 0).toFixed(0)} MB
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function Dashboard({ observation, plan, scanHistory }) {
  const metrics = observation?.metrics || {};
  const health = observation ? healthScore(metrics) : 0;
  const recoverable = plan?.estimated_recoverable_bytes ?? 0;
  const diskPercent = metrics.disk_percent ?? 0;
  const diskPressure = observation ? pressureScore(metrics) : "No scan";
  const recommendations = (plan?.cleanup_actions || []).slice(0, 3);

  return (
    <section className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(280px,420px)_1fr]">
        <div className="panel border-l-2 border-l-[#eab766] p-5">
          <div className="mb-5 flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300">Health Score</h3>
            <span className="channel-dot" style={{ background: "#eab766" }} />
          </div>
          <div className="flex flex-wrap items-center gap-5">
            <RingScore score={health} />
            <div className="min-w-0 flex-1">
              <p className="font-display text-xl font-bold text-[#f6cf98]">
                {observation ? (health >= 80 ? "Healthy Workspace" : health >= 60 ? "Stable but Heavy" : "Needs Attention") : "Awaiting Real Scan"}
              </p>
              <p className="mt-2 max-w-sm text-sm font-medium leading-relaxed text-slate-400">
                {observation
                  ? "Artifacts, caches, and workspace pressure are ready for local review."
                  : "Run a scan to load live local metrics and recommendations."}
              </p>
            </div>
          </div>
        </div>

        <div className="panel p-5">
          <div className="mb-5 flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300">Storage Allocation</h3>
            <span className="mono text-xs font-bold text-mint-300">DB</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatTile label="Total Space" value={metrics.total_disk_bytes ? formatBytes(metrics.total_disk_bytes) : "--"} />
            <StatTile label="Available" value={metrics.available_disk_bytes ? formatBytes(metrics.available_disk_bytes) : "--"} />
            <StatTile label="Recoverable" value={formatBytes(recoverable)} tone="mint" />
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(280px,520px)_1fr]">
        <div className="panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300">Disk Pressure</h3>
              <p className="mono mt-2 text-xl font-bold text-mint-300">{observation?.folder || "No folder scanned"}</p>
            </div>
            <span className="status-pill bg-[#ff8f83]/15 text-[#ffbcb2]">{diskPressure}</span>
          </div>
          <div className="mt-8 flex items-center justify-between">
            <p className="text-sm font-medium text-slate-400">Utilization</p>
            <p className="mono text-xl font-bold text-[#ffbcb2]">{diskPercent.toFixed ? diskPercent.toFixed(0) : diskPercent}%</p>
          </div>
          <div className="mt-2 h-3 overflow-hidden rounded-full bg-ink-700">
            <div className="h-full rounded-full bg-[#ff8f83]" style={{ width: `${Math.min(100, diskPercent)}%` }} />
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border border-ink-700 bg-ink-900 p-3">
              <p className="text-[11px] font-bold uppercase text-slate-500">I/O Wait</p>
              <p className="mono text-lg font-bold text-white">{metrics.io_wait_ms !== undefined ? `${metrics.io_wait_ms.toFixed?.(1) || metrics.io_wait_ms}ms` : "--"}</p>
            </div>
            <div className="rounded-md border border-ink-700 bg-ink-900 p-3">
              <p className="text-[11px] font-bold uppercase text-slate-500">Throughput</p>
              <p className="mono text-lg font-bold text-white">{metrics.disk_throughput || "--"}</p>
            </div>
          </div>
        </div>

        <RecentHistory scanHistory={scanHistory} />
      </div>

      <SystemHealthPanel observation={observation} />

      <div className="panel p-5">
        <div className="mb-5 flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wide text-slate-300">Cleaning Recommendations</h3>
          <div className="flex gap-1">
            <span className="channel-dot bg-mint-300" />
            <span className="channel-dot bg-ink-600" />
            <span className="channel-dot bg-ink-600" />
          </div>
        </div>
        {recommendations.length ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {recommendations.map((action, index) => (
              <Recommendation
                key={action.action_id || action.path || index}
                title={action.project_type || action.risk_level || "Cleanup Candidate"}
                text={action.reason || action.path}
                value={formatBytes(action.size_bytes || 0)}
                tone={action.risk_level === "High" ? "rose" : action.risk_level === "Medium" ? "amber" : "mint"}
              />
            ))}
          </div>
        ) : (
          <p className="rounded-md border border-ink-700 bg-ink-900 px-5 py-8 text-center text-sm text-slate-500">
            No real cleanup recommendations yet. Run a scan to generate local candidates.
          </p>
        )}
      </div>
    </section>
  );
}

export { riskClass };