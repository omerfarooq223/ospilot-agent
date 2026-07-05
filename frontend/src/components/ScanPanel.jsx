function shortPath(path) {
  if (!path) return "";
  if (path.length <= 46) return path;
  return `${path.slice(0, 20)}...${path.slice(-22)}`;
}

export default function ScanPanel({
  folder,
  minSizeMb,
  setMinSizeMb,
  fallback,
  loading,
  scanProgress,
  scanMessage,
  scanTargetLabel,
  onScan,
  onWholePcScan,
  onCancelScan,
  ignoredFolders,
  onUnignoreFolder,
  scanHistory,
}) {
  const thresholdLabel = minSizeMb >= 1000 ? `${(minSizeMb / 1000).toFixed(minSizeMb % 1000 === 0 ? 0 : 1)} GB` : `${minSizeMb} MB`;

  return (
    <section className="space-y-8">
      <div className="grid gap-6 xl:grid-cols-[1fr_420px]">
        <div className="space-y-6">
          <div className="panel p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-300">Selected Target</p>
              <span className="mono text-xs font-bold text-mint-300">Local Storage</span>
            </div>
            <p className="text-sm leading-relaxed text-slate-400">
              Use the scan controls on the right to choose a specific folder with your Mac folder picker, or scan your whole user-owned computer space.
            </p>
            <div className="mt-4 rounded-md border border-ink-700 bg-ink-950 px-4 py-3">
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Current selection</p>
              <p className="mono mt-1 break-all text-sm text-white">{folder || "No folder selected yet"}</p>
            </div>
          </div>

          <div className="panel p-5">
            <div className="mb-7 flex items-center justify-between gap-3">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-300">File Size Threshold</p>
              <span className="mono rounded border border-sky-400/25 bg-sky-400/10 px-3 py-2 text-sm text-sky-200">{thresholdLabel}</span>
            </div>
            <p className="mb-5 text-sm leading-relaxed text-slate-400">
              This only controls which individual large files are reported. For example, at {thresholdLabel}, OS Pilot flags files at least that large. It does not stop generated folders like <span className="mono text-slate-300">node_modules</span>, caches, or build folders from being detected.
            </p>
            <input
              type="range"
              min="30"
              max="5000"
              step="10"
              value={minSizeMb}
              onChange={(event) => setMinSizeMb(Number(event.target.value))}
              className="w-full accent-mint-300"
            />
            <div className="tick-rule mt-4" />
            <div className="mono mt-3 flex justify-between text-xs text-slate-500">
              <span>30 MB</span>
              <span>5 GB</span>
            </div>
          </div>

          <div className="panel p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-300">Ignored Folders</p>
              <span className="text-sm font-bold text-slate-500">{ignoredFolders?.length || 0} active</span>
            </div>
            {ignoredFolders?.length ? (
              <div className="flex flex-wrap gap-2">
                {ignoredFolders.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className="mono rounded-full border border-ink-600 bg-ink-850 px-3 py-1 text-xs text-slate-300 hover:border-mint-300 hover:text-mint-300"
                    onClick={() => onUnignoreFolder(item)}
                    title="Remove ignored folder"
                  >
                    {shortPath(item)} ×
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No ignored folders configured.</p>
            )}
          </div>
        </div>

        <aside className="space-y-6">
          <div className="panel p-5">
            <p className="mb-4 text-sm font-bold uppercase tracking-wide text-slate-300">Control Center</p>
            <button type="button" className="btn-primary h-16 w-full text-base" onClick={onScan} disabled={loading}>
              {loading ? "Scanning..." : "Scan a Specific Folder"}
            </button>
            <button type="button" className="btn-secondary mt-3 w-full" onClick={onWholePcScan} disabled={loading}>
              Scan Whole PC
            </button>
            <p className="mt-3 text-xs leading-relaxed text-slate-500">
              Whole PC scans cover your user-owned space and skip OS protected folders.
            </p>
          </div>

          {loading ? (
            <div className="panel border-l-2 border-l-[#eab766] bg-ink-850 p-5">
              <div className="mb-3 flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-display text-xl font-bold text-[#f6cf98]">Active Scan</h3>
                  <p className="mono mt-1 break-all text-sm text-slate-300">{scanTargetLabel || "Preparing scan target..."}</p>
                </div>
                <div className="text-right">
                  <p className="mono font-display text-2xl font-bold text-[#f6cf98]">{scanProgress || 10}%</p>
                  <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Progress</p>
                </div>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-ink-950">
                <div className="h-full rounded-full bg-[#eab766]" style={{ width: `${scanProgress || 10}%` }} />
              </div>
              <div className="mt-5 flex items-end justify-between gap-3">
                <div>
                  <p className="text-[11px] font-bold uppercase text-slate-500">Current Task</p>
                  <p className="mono text-sm font-bold text-white">{scanMessage || "Scanning real folder data"}</p>
                </div>
                <button type="button" className="btn-danger" onClick={onCancelScan}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="panel border-l-2 border-l-mint-300 p-5">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-300">{fallback ? "Local Scan Ready" : "Scanner Ready"}</p>
              <p className="mt-2 text-sm font-medium leading-relaxed text-slate-400">
                Files remain local. Cleanup candidates move to approval before quarantine.
              </p>
            </div>
          )}

          <div className="panel p-5">
            <p className="text-sm font-bold uppercase tracking-wide text-slate-300">Selected Folder</p>
            <p className="mono mt-2 break-all text-sm text-slate-400">{folder || "No folder selected"}</p>
          </div>
        </aside>
      </div>

      <div>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="font-display text-2xl font-bold text-white">Recent Scans</h3>
            <p className="mt-1 text-sm text-slate-500">
              Potential gain is the total recoverable estimate from that scan, not the sum of scenario cards.
            </p>
          </div>
          <span className="mono text-sm font-bold text-mint-300">{scanHistory?.length || 0} recorded</span>
        </div>
        <div className="table-shell overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-ink-850 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Path</th>
                <th className="px-5 py-3">Date</th>
                <th className="px-5 py-3">Potential Gain</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {scanHistory?.length ? (
                scanHistory.slice(0, 4).map((item, index) => (
                  <tr key={`${item.folder || item.path}-${index}`} className="border-t border-ink-700">
                    <td className="mono max-w-[520px] break-all px-5 py-4 text-white">{item.folder || item.path}</td>
                    <td className="px-5 py-4 text-slate-400">{item.timestamp || item.date}</td>
                    <td className="mono px-5 py-4 font-bold text-mint-300">{item.recoverable_label || "0 B"}</td>
                    <td className="px-5 py-4">
                      <span className="status-pill border border-mint-300/25 bg-mint-300/10 text-mint-300">
                        Recorded
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="border-t border-ink-700 px-5 py-8 text-center text-sm text-slate-500">
                    No scan history yet. Run a real scan to show local results here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}