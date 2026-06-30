import { useEffect, useState } from "react";

function shortPath(path) {
  if (!path) return "";
  if (path.length <= 46) return path;
  return `${path.slice(0, 20)}...${path.slice(-22)}`;
}

function FolderExplorer({ folder, setFolder, browseFolders, ignoredFolders, onIgnoreFolder, onUnignoreFolder }) {
  const [browser, setBrowser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(path) {
    setLoading(true);
    setError("");
    try {
      const result = await browseFolders(path);
      setBrowser(result);
      setFolder(result.current_path);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(folder || undefined);
  }, []);

  const currentPath = browser?.current_path || folder;
  const currentIgnored = ignoredFolders?.includes(currentPath);

  return (
    <div className="panel p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Folder Explorer</p>
          <p className="mono truncate text-sm text-slate-300">{currentPath || "Loading folders..."}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" disabled={!currentPath || currentIgnored} onClick={() => setFolder(currentPath)}>
            Select
          </button>
          {currentPath ? (
            currentIgnored ? (
              <button type="button" className="btn-secondary" onClick={() => onUnignoreFolder(currentPath)}>
                Unignore
              </button>
            ) : (
              <button type="button" className="btn-secondary" onClick={() => onIgnoreFolder(currentPath)}>
                Ignore
              </button>
            )
          ) : null}
        </div>
      </div>

      {error ? <p className="mb-3 border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">{error}</p> : null}

      <div className="grid gap-3 lg:grid-cols-[200px_1fr]">
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Major Locations</p>
          {browser?.major_locations?.map((item) => (
            <button
              key={item.path}
              type="button"
              className={`block w-full border px-3 py-2 text-left text-sm transition ${
                item.path === currentPath
                  ? "border-mint-300 bg-mint-500/10 text-mint-200"
                  : "border-[#303a39] bg-[#202222] text-slate-300 hover:bg-[#292b2b]"
              }`}
              onClick={() => load(item.path)}
            >
              <span className="block truncate">{item.name}</span>
              {item.is_ignored ? <span className="text-xs text-[#ffd09d]">Ignored</span> : null}
            </button>
          ))}
        </div>

        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            {browser?.breadcrumbs?.map((crumb, index) => (
              <button
                key={crumb.path}
                type="button"
                className="border border-[#303a39] bg-[#202222] px-2 py-1 hover:bg-[#292b2b]"
                onClick={() => load(crumb.path)}
              >
                {index === 0 ? crumb.path : crumb.name}
              </button>
            ))}
          </div>

          <div className="max-h-56 overflow-y-auto border border-[#303a39] bg-[#151717]">
            {browser?.parent_path ? (
              <button
                type="button"
                className="block w-full border-b border-[#252c2b] px-3 py-2 text-left text-sm font-semibold text-mint-300 hover:bg-[#202222]"
                onClick={() => load(browser.parent_path)}
              >
                Up one folder
              </button>
            ) : null}
            {loading ? <p className="px-3 py-3 text-sm text-slate-400">Loading folders...</p> : null}
            {!loading && browser?.children?.length ? (
              browser.children.map((item) => (
                <button
                  key={item.path}
                  type="button"
                  className={`block w-full border-b border-[#252c2b] px-3 py-2 text-left text-sm hover:bg-[#202222] ${
                    item.is_ignored ? "text-[#ffd09d]" : "text-slate-300"
                  }`}
                  onClick={() => load(item.path)}
                >
                  <span className="block truncate">{item.name}</span>
                  {item.is_ignored ? <span className="text-xs text-[#ffd09d]">Ignored</span> : null}
                </button>
              ))
            ) : null}
            {!loading && browser && !browser.children?.length ? (
              <p className="px-3 py-3 text-sm text-slate-500">No visible subfolders here.</p>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ScanPanel({
  folder,
  setFolder,
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
  browseFolders,
  ignoredFolders,
  onIgnoreFolder,
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
              <p className="text-sm font-bold uppercase tracking-wide text-slate-300">Target Path</p>
              <span className="mono text-sm font-bold text-mint-300">Local Storage</span>
            </div>
            <div className="flex flex-wrap items-center gap-3 border border-[#3a4545] bg-[#101212] px-4 py-3">
              <span className="text-slate-300">Folder</span>
              <input
                className="mono min-w-[220px] flex-1 bg-transparent text-base text-white outline-none"
                placeholder="Choose a real local folder below or paste a path"
                value={folder}
                onChange={(event) => setFolder(event.target.value)}
              />
            </div>
          </div>

          <div className="panel p-5">
            <div className="mb-7 flex items-center justify-between gap-3">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-300">File Size Threshold</p>
              <span className="mono border border-sky-400/30 bg-sky-400/10 px-3 py-2 text-sm text-sky-200">{thresholdLabel}</span>
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
            <div className="mt-4 flex justify-between text-sm text-slate-400">
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
                    className="rounded-full border border-[#4a5555] bg-[#333939] px-3 py-1 text-sm text-slate-300 hover:border-mint-300 hover:text-mint-300"
                    onClick={() => onUnignoreFolder(item)}
                    title="Remove ignored folder"
                  >
                    {shortPath(item)} x
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">No ignored folders configured. Use the folder explorer to ignore real folders.</p>
            )}
          </div>

          <FolderExplorer
            folder={folder}
            setFolder={setFolder}
            browseFolders={browseFolders}
            ignoredFolders={ignoredFolders}
            onIgnoreFolder={onIgnoreFolder}
            onUnignoreFolder={onUnignoreFolder}
          />
        </div>

        <aside className="space-y-6">
          <div className="panel p-5">
            <p className="mb-4 text-sm font-bold uppercase tracking-wide text-slate-300">Control Center</p>
            <button type="button" className="btn-primary h-16 w-full text-lg" onClick={onScan} disabled={loading || !folder}>
              {loading ? "Scanning..." : "Scan Folder"}
            </button>
            <button type="button" className="btn-secondary mt-3 w-full" onClick={onWholePcScan} disabled={loading}>
              Home Scan
            </button>
            <p className="mt-3 text-xs leading-relaxed text-slate-500">
              Home scans cover your user-owned home area and skip protected OS folders.
            </p>
          </div>

          {loading ? (
            <div className="panel border-l-4 border-l-[#ffd09d] bg-[#2b2b2b] p-5">
              <div className="mb-3 flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-display text-xl font-bold text-[#ffd09d]">Active Scan</h3>
                  <p className="mono mt-1 break-all text-sm text-slate-300">{scanTargetLabel || "Preparing scan target..."}</p>
                </div>
                <div className="text-right">
                  <p className="font-display text-2xl font-bold text-[#ffd09d]">{scanProgress || 10}%</p>
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-300">Progress</p>
                </div>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-[#161717]">
                <div className="h-full rounded-full bg-[#ffd09d]" style={{ width: `${scanProgress || 10}%` }} />
              </div>
              <div className="mt-5 flex items-end justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase text-slate-400">Current Task</p>
                  <p className="mono text-sm font-bold text-white">{scanMessage || "Scanning real folder data"}</p>
                </div>
                <button type="button" className="btn-danger" onClick={onCancelScan}>
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="panel border-l-4 border-l-mint-300 p-5">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-300">{fallback ? "Local Scan Ready" : "Scanner Ready"}</p>
              <p className="mt-2 text-sm font-semibold leading-relaxed text-slate-300">
                Files remain local. Cleanup candidates move to approval before quarantine.
              </p>
            </div>
          )}

          <div className="panel p-5">
            <p className="text-sm font-bold uppercase tracking-wide text-slate-300">Selected Folder</p>
            <p className="mono mt-2 break-all text-sm text-slate-300">{folder || "No folder selected"}</p>
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
          <span className="text-sm font-bold text-mint-300">{scanHistory?.length || 0} recorded</span>
        </div>
        <div className="table-shell overflow-x-auto">
          <table className="w-full min-w-[760px] text-left">
            <thead className="bg-[#292b2b] text-sm uppercase text-slate-300">
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
                  <tr key={`${item.folder || item.path}-${index}`} className="border-t border-[#303a39]">
                    <td className="mono max-w-[520px] break-all px-5 py-4 text-white">{item.folder || item.path}</td>
                    <td className="px-5 py-4 text-slate-300">{item.timestamp || item.date}</td>
                    <td className="mono px-5 py-4 font-bold text-mint-300">{item.recoverable_label || "0 B"}</td>
                    <td className="px-5 py-4">
                      <span className="status-pill border border-mint-300/30 bg-mint-300/10 text-mint-300">
                        Recorded
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="border-t border-[#303a39] px-5 py-8 text-center text-sm text-slate-500">
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
