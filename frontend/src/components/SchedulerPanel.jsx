import { useEffect, useState } from "react";

const WEEKDAYS = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

export default function SchedulerPanel({
  status,
  folder,
  minSizeMb,
  loading,
  onEnable,
  onDisable,
  onRunNow,
  onRefresh,
}) {
  const [scheduleFolder, setScheduleFolder] = useState(folder || status?.folders?.[0] || "");
  const [weekday, setWeekday] = useState(status?.weekday ?? 0);
  const [hour, setHour] = useState(status?.hour ?? 9);
  const [minute, setMinute] = useState(status?.minute ?? 0);

  useEffect(() => {
    if (folder) setScheduleFolder(folder);
  }, [folder]);

  useEffect(() => {
    if (!status) return;
    setWeekday(status.weekday ?? 0);
    setHour(status.hour ?? 9);
    setMinute(status.minute ?? 0);
    if (!folder && status.folders?.[0]) setScheduleFolder(status.folders[0]);
  }, [status, folder]);

  if (!status) {
    return (
      <section className="panel p-6">
        <p className="text-sm text-slate-400">Loading weekly scan settings...</p>
      </section>
    );
  }

  return (
    <section className="panel p-6">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-semibold text-white">Weekly scan (opt-in)</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Allow OS Pilot to scan selected folders on a schedule and write a human-readable report.
            Nothing is deleted or quarantined automatically — you review results in the app first.
          </p>
        </div>
        <span
          className={`mono flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${status.enabled
              ? "border-mint-500/30 bg-mint-500/10 text-mint-200"
              : "border-ink-600 bg-ink-850 text-slate-400"
            }`}
        >
          <span className={`channel-dot ${status.enabled ? "bg-mint-300" : "bg-ink-600"}`} />
          {status.enabled ? "Weekly scan enabled" : "Weekly scan off"}
        </span>
      </div>

      {!status.supported ? (
        <p className="rounded-md border border-[#eab766]/30 bg-[#eab766]/10 px-4 py-3 text-sm text-[#f6cf98]">
          Weekly scheduling is currently supported on macOS (launchd) and Linux (cron) only.
        </p>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="block">
              <span className="mb-2 block text-sm text-slate-400">Folder to scan weekly</span>
              <input
                className="field"
                value={scheduleFolder}
                onChange={(event) => setScheduleFolder(event.target.value)}
                placeholder="/Users/you/projects"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm text-slate-400">Day of week</span>
              <select
                className="field"
                value={weekday}
                onChange={(event) => setWeekday(Number(event.target.value))}
              >
                {WEEKDAYS.map((label, index) => (
                  <option key={label} value={index}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="mb-2 block text-sm text-slate-400">Hour (24h)</span>
              <input
                type="number"
                min="0"
                max="23"
                className="field mono"
                value={hour}
                onChange={(event) => setHour(Number(event.target.value))}
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm text-slate-400">Minute</span>
              <input
                type="number"
                min="0"
                max="59"
                className="field mono"
                value={minute}
                onChange={(event) => setMinute(Number(event.target.value))}
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            {!status.enabled ? (
              <button
                type="button"
                className="btn-primary"
                disabled={loading || !scheduleFolder.trim()}
                onClick={() =>
                  onEnable({
                    folders: [scheduleFolder.trim()],
                    weekday,
                    hour,
                    minute,
                    min_size_mb: minSizeMb,
                  })
                }
              >
                {loading ? "Installing..." : "Enable weekly scan"}
              </button>
            ) : (
              <button type="button" className="btn-secondary" disabled={loading} onClick={onDisable}>
                {loading ? "Removing..." : "Disable weekly scan"}
              </button>
            )}
            <button
              type="button"
              className="btn-secondary"
              disabled={loading || !scheduleFolder.trim()}
              onClick={() =>
                onRunNow({
                  folders: [scheduleFolder.trim()],
                  weekday,
                  hour,
                  minute,
                  min_size_mb: minSizeMb,
                })
              }
            >
              Run report now
            </button>
            <button type="button" className="btn-secondary" disabled={loading} onClick={onRefresh}>
              Refresh status
            </button>
          </div>

          {status.enabled ? (
            <p className="mt-4 text-sm text-slate-400">
              Scheduled for <span className="mono">{status.schedule_label}</span> via {status.platform}. Installed:{" "}
              {status.installed ? "yes" : "pending"}
            </p>
          ) : null}

          {status.latest_report ? (
            <div className="mt-5 rounded-md border border-ink-700 bg-ink-850 px-4 py-3 text-sm text-slate-300">
              Latest report:{" "}
              <code className="mono text-mint-300">{status.latest_report.path}</code>
              <p className="mt-2 text-xs text-slate-500">
                Open the HTML file in your browser for the easiest read.
              </p>
            </div>
          ) : null}

          {status.recent_reports?.length ? (
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-medium text-slate-300">Recent reports</h3>
              <ul className="mono space-y-1 text-xs text-slate-500">
                {status.recent_reports.slice(0, 6).map((report) => (
                  <li key={report.path}>
                    {report.name} · {report.path}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}