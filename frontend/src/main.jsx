import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  browseFolders,
  cancelScanJob,
  disableWeeklyScan,
  enableWeeklyScan,
  getScanHistory,
  getScanJob,
  getHealth,
  getSchedulerStatus,
  ignoreFolder,
  listAudit,
  listIgnoredFolders,
  listQuarantine,
  permanentlyDeleteItem,
  quarantineAutopilot,
  quarantineItems,
  restoreItem,
  startScan,
  unignoreFolder,
  runWeeklyScanNow,
} from "./api";
import Dashboard from "./components/Dashboard";
import PlanView from "./components/PlanView";
import QuarantineView from "./components/QuarantineView";
import ReportView from "./components/ReportView";
import ScanPanel from "./components/ScanPanel";
import SchedulerPanel from "./components/SchedulerPanel";
import "./index.css";

const TABS = [
  { id: "overview", label: "Overview", icon: "grid" },
  { id: "scan", label: "Scan", icon: "search" },
  { id: "plan", label: "Plan & Approval", icon: "check" },
  { id: "quarantine", label: "Quarantine", icon: "box" },
  { id: "report", label: "Reports", icon: "chart" },
  { id: "settings", label: "Settings", icon: "gear" },
];

const USER_NAME = "Muhammad Omer Farooq";
const USER_INITIALS = "MO";

function Icon({ name }) {
  const paths = {
    grid: "M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z",
    search: "M10.5 18a7.5 7.5 0 1 1 5.3-12.8A7.5 7.5 0 0 1 10.5 18Zm5.3-2.2L21 21",
    check: "M4 5h16v14H4V5Zm4 7 2.5 2.5L16 9",
    box: "M5 7h14v13H5V7Zm2-3h10l2 3H5l2-3Z",
    chart: "M5 19V5h14v14H5Zm4-3v-5m4 5V8m4 8v-3",
    gear: "M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Zm0-5v3m0 11v3m8.5-8.5h-3m-11 0h-3m14.5-6.5-2.1 2.1M8.1 15.9 6 18m12 0-2.1-2.1M8.1 8.1 6 6",
    broom: "M8 21h8M10 21V9h4v12M9 9h6M11 9V4a1 1 0 0 1 2 0v5M6 15h12v6H6v-6Z",
    plus: "M12 5v14M5 12h14",
    sun: "M12 4V2m0 20v-2m8-8h2M2 12h2m14.95-6.95 1.4-1.4M3.65 20.35l1.4-1.4m0-13.9-1.4-1.4m16.7 16.7-1.4-1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
    moon: "M21 14.6A7.8 7.8 0 0 1 9.4 3 8.8 8.8 0 1 0 21 14.6Z",
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d={paths[name]} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function App() {
  const [tab, setTab] = useState("overview");
  const [folder, setFolder] = useState("");
  const [minSizeMb, setMinSizeMb] = useState(30);
  const [fallback, setFallback] = useState(true);
  const [observation, setObservation] = useState(null);
  const [plan, setPlan] = useState(null);
  const [scanSessionId, setScanSessionId] = useState(null);
  const [report, setReport] = useState(null);
  const [quarantineRecords, setQuarantineRecords] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [scanLoading, setScanLoading] = useState(false);
  const [quarantineLoading, setQuarantineLoading] = useState(false);
  const [restoreLoadingId, setRestoreLoadingId] = useState(null);
  const [deleteLoadingId, setDeleteLoadingId] = useState(null);
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [scanJobId, setScanJobId] = useState(null);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanMessage, setScanMessage] = useState("");
  const [scanTargetLabel, setScanTargetLabel] = useState("");
  const [ignoredFolders, setIgnoredFolders] = useState([]);
  const [scanHistory, setScanHistory] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [theme, setTheme] = useState(() => localStorage.getItem("os-pilot-theme") || "dark");

  async function refreshSideData() {
    const [records, events, scheduler, ignored, history] = await Promise.all([
      listQuarantine(),
      listAudit(10),
      getSchedulerStatus(),
      listIgnoredFolders(),
      getScanHistory(12),
    ]);
    setQuarantineRecords(records);
    setAuditEvents(events);
    setSchedulerStatus(scheduler);
    setIgnoredFolders(ignored.folders || []);
    setScanHistory(history.items || []);
  }

  async function handleRefreshData() {
    setError("");
    try {
      await refreshSideData();
      setMessage("Local data refreshed.");
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    getHealth()
      .then((health) => setFallback(Boolean(health.fallback_mode)))
      .catch(() => setFallback(true));
    refreshSideData().catch(() => {});
  }, []);

  useEffect(() => {
    localStorage.setItem("os-pilot-theme", theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  async function handleScan() {
    setError("");
    setMessage("");
    setTab("scan");
    setScanLoading(true);
    setScanProgress(10);
    setScanTargetLabel(folder);
    setScanMessage(`Preparing scan for ${folder}...`);
    try {
      const started = await startScan(folder, minSizeMb);
      setScanJobId(started.job_id);
      pollScanJob(started.job_id);
    } catch (err) {
      setError(err.message);
      setScanLoading(false);
    } finally {
      // completion happens in pollScanJob
    }
  }

  async function handleWholePcScan() {
    setFolder("~");
    setError("");
    setTab("scan");
    setMessage("Home scan uses your user-owned home area and skips protected OS folders.");
    setScanLoading(true);
    setScanProgress(10);
    setScanTargetLabel("Home scan: user-owned home area (~)");
    setScanMessage("Preparing home scan...");
    try {
      const started = await startScan("~", minSizeMb);
      setScanJobId(started.job_id);
      pollScanJob(started.job_id);
    } catch (err) {
      setError(err.message);
      setScanLoading(false);
    }
  }

  async function pollScanJob(jobId) {
    try {
      const job = await getScanJob(jobId);
      setScanProgress(job.progress || 10);
      setScanMessage(job.message || "Scanning...");
      if (job.status === "completed") {
        setObservation(job.observation);
        setPlan(job.plan);
        setScanSessionId(job.session_id);
        setFallback(Boolean(job.fallback));
        setReport(null);
        setMessage("Scan complete. Review the plan below.");
        setTab("plan");
        setScanLoading(false);
        setScanJobId(null);
        await refreshSideData();
        return;
      }
      if (job.status === "failed") {
        setError(job.error || "Scan failed.");
        setScanLoading(false);
        setScanJobId(null);
        return;
      }
      if (job.status === "cancelled") {
        setMessage("Scan cancelled.");
        setScanLoading(false);
        setScanJobId(null);
        return;
      }
      window.setTimeout(() => pollScanJob(jobId), 700);
    } catch (err) {
      setError(err.message);
      setScanLoading(false);
      setScanJobId(null);
    }
  }

  async function handleCancelScan() {
    if (!scanJobId) return;
    try {
      await cancelScanJob(scanJobId);
      setMessage("Scan cancelled.");
    } catch (err) {
      setError(err.message);
    } finally {
      setScanLoading(false);
      setScanJobId(null);
    }
  }

  async function handleIgnoreFolder(path) {
    setError("");
    try {
      const result = await ignoreFolder(path);
      setIgnoredFolders(result.folders || []);
      setMessage("Folder added to ignore list.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUnignoreFolder(path) {
    setError("");
    try {
      const result = await unignoreFolder(path);
      setIgnoredFolders(result.folders || []);
      setMessage("Folder removed from ignore list.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleQuarantine(approvedActionIds) {
    setError("");
    setMessage("");
    setQuarantineLoading(true);
    try {
      const result = await quarantineItems(scanSessionId, approvedActionIds);
      setReport(result.report);
      setMessage(`Quarantined ${result.quarantined.length} item(s).`);
      setTab("report");
      await refreshSideData();
    } catch (err) {
      setError(err.message);
    } finally {
      setQuarantineLoading(false);
    }
  }

  async function handleAutopilotQuarantine() {
    setError("");
    setMessage("");
    setQuarantineLoading(true);
    try {
      const result = await quarantineAutopilot(scanSessionId);
      setReport(result.report);
      setMessage(`Safe Autopilot quarantined ${result.quarantined.length} server-approved item(s).`);
      setTab("report");
      await refreshSideData();
    } catch (err) {
      setError(err.message);
    } finally {
      setQuarantineLoading(false);
    }
  }

  async function handlePermanentDelete(recordId) {
    setError("");
    setMessage("");
    setDeleteLoadingId(recordId);
    try {
      await permanentlyDeleteItem(recordId);
      setMessage("Item permanently deleted and removed from disk.");
      await refreshSideData();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleteLoadingId(null);
    }
  }

  async function handleRestore(recordId) {
    setError("");
    setMessage("");
    setRestoreLoadingId(recordId);
    try {
      const result = await restoreItem(recordId);
      setMessage(`Restored ${result.record.original_path}`);
      await refreshSideData();
    } catch (err) {
      setError(err.message);
    } finally {
      setRestoreLoadingId(null);
    }
  }

  async function handleEnableWeeklyScan(payload) {
    setError("");
    setMessage("");
    setSchedulerLoading(true);
    try {
      const status = await enableWeeklyScan(payload);
      setSchedulerStatus(status);
      setMessage(`Weekly scan enabled for ${status.schedule_label}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSchedulerLoading(false);
    }
  }

  async function handleDisableWeeklyScan() {
    setError("");
    setMessage("");
    setSchedulerLoading(true);
    try {
      const status = await disableWeeklyScan();
      setSchedulerStatus(status);
      setMessage("Weekly scan disabled.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSchedulerLoading(false);
    }
  }

  async function handleRunWeeklyScanNow(payload) {
    setError("");
    setMessage("");
    setSchedulerLoading(true);
    try {
      const result = await runWeeklyScanNow(payload);
      setMessage(`Weekly report saved. HTML: ${result.reports?.html || "see reports folder"}`);
      await refreshSideData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSchedulerLoading(false);
    }
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    const query = searchQuery.trim().toLowerCase();
    if (!query) return;

    const target = TABS.find((item) => item.label.toLowerCase().includes(query) || item.id.includes(query));
    if (target) {
      setTab(target.id);
      setMessage(`Opened ${target.label}.`);
      return;
    }

    const keywordTarget = [
      { words: ["file", "folder", "path", "scan"], tab: "scan", label: "Scan" },
      { words: ["approve", "approval", "candidate", "cleanup"], tab: "plan", label: "Plan & Approval" },
      { words: ["restore", "delete", "quarantine"], tab: "quarantine", label: "Quarantine" },
      { words: ["audit", "export", "report"], tab: "report", label: "Reports" },
      { words: ["weekly", "schedule", "security", "safe"], tab: "settings", label: "Settings" },
    ].find((item) => item.words.some((word) => query.includes(word)));

    if (keywordTarget) {
      setTab(keywordTarget.tab);
      setMessage(`Opened ${keywordTarget.label}.`);
      return;
    }

    setMessage("Search checks navigation and local task areas. Run a scan to create searchable results.");
  }

  const contentTitle = {
    overview: "System Overview",
    scan: "Scan Panel",
    plan: "Plan & Approval",
    quarantine: "Quarantine & Reports",
    report: "Reports",
    settings: "Settings",
  }[tab];

  return (
    <div className={`app-frame theme-${theme}`}>
      <div className="grid min-h-screen grid-cols-1 bg-[#101111] text-slate-200 lg:h-screen lg:grid-cols-[250px_1fr]">
        <aside className="flex border-b border-[#35403f] bg-[#1b1d1d] lg:sticky lg:top-0 lg:h-screen lg:flex-col lg:border-b-0 lg:border-r">
          <div className="hidden px-8 py-8 lg:block">
            <div className="flex items-center gap-3">
              <span className="text-mint-400"><Icon name="broom" /></span>
              <div>
                <h1 className="font-display text-xl font-bold text-mint-300">OS Pilot</h1>
                <p className="text-sm text-slate-400">Local-First Utility</p>
              </div>
            </div>
          </div>

          <nav className="flex w-full gap-1 overflow-x-auto px-3 py-3 lg:block lg:space-y-1 lg:px-0 lg:py-5">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`flex min-w-max items-center gap-3 border-l-4 px-4 py-3 text-left text-sm font-semibold transition lg:w-full lg:min-w-0 lg:px-8 ${
                  tab === item.id
                    ? "border-mint-300 bg-[#233031] text-mint-300"
                    : "border-transparent text-slate-300 hover:bg-[#232626]"
                }`}
              >
                <Icon name={item.icon} />
                {item.label}
              </button>
            ))}
          </nav>

          <div className="mt-auto hidden border-t border-[#35403f] p-6 lg:block">
            <button type="button" className="btn-primary w-full" onClick={() => setTab("scan")}>
              <Icon name="plus" /> New Scan
            </button>
          </div>
        </aside>

        <main className="min-w-0 lg:h-screen lg:overflow-y-auto">
          <header className="sticky top-0 z-10 border-b border-[#35403f] bg-[#101111]/95 backdrop-blur">
            <div className="flex min-h-[72px] flex-wrap items-center justify-between gap-4 px-5 py-4 xl:px-8">
              <form className="relative min-w-[260px] flex-1 lg:max-w-xl" onSubmit={handleSearchSubmit}>
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                  <Icon name="search" />
                </span>
                <input
                  className="field pl-11"
                  placeholder="Search paths, files, or tasks..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </form>
              <div className="flex items-center gap-5">
                <button
                  type="button"
                  className="btn-secondary min-h-10 px-3"
                  onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
                  title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                >
                  <Icon name={theme === "dark" ? "sun" : "moon"} />
                  <span className="hidden sm:inline">{theme === "dark" ? "Light" : "Dark"}</span>
                </button>
                <div className="hidden h-9 border-l border-[#35403f] sm:block" />
                <button
                  type="button"
                  className="flex items-center gap-3 text-left"
                  title="Open profile settings"
                  onClick={() => {
                    setTab("settings");
                    setMessage("Opened your local profile and settings.");
                  }}
                >
                  <div className="hidden text-right sm:block">
                    <p className="font-bold text-white">{USER_NAME}</p>
                    <p className="text-xs font-semibold uppercase text-slate-400">
                      {fallback ? "NODE_01_LOCAL" : "System Active"}
                    </p>
                  </div>
                  <div className="grid h-10 w-10 place-items-center rounded-full bg-[#1284c7] text-sm font-bold text-white">
                    {USER_INITIALS}
                  </div>
                </button>
              </div>
            </div>
          </header>

          <div className="px-5 py-6 xl:px-8">
            {message ? (
              <div className="mb-4 border border-mint-500/30 bg-mint-500/10 px-4 py-3 text-sm text-mint-100">
                {message}
              </div>
            ) : null}
            {error ? (
              <div className="mb-4 border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </div>
            ) : null}

            <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="font-display text-3xl font-bold text-white">{contentTitle}</h2>
                <p className="mt-1 text-lg text-slate-300">
                  {tab === "overview" ? "Local-First / Secure (No Cloud Uploads)" : null}
                  {tab === "scan" ? "Scan one folder or your user-owned whole-computer space." : null}
                  {tab === "plan" ? "Simulation mode: nothing moves until you approve quarantine." : null}
                  {tab === "quarantine" ? "Safe storage for flagged files awaiting review." : null}
                  {tab === "report" ? "Performance metrics, exports, and audit history." : null}
                  {tab === "settings" ? "Weekly scans remain opt-in and review-first." : null}
                </p>
              </div>
              {tab === "overview" ? (
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="btn-secondary" onClick={handleRefreshData}>
                    Refresh Data
                  </button>
                  <button type="button" className="btn-primary" onClick={handleWholePcScan}>
                    Home Scan
                  </button>
                </div>
              ) : null}
            </div>

            {tab === "overview" ? <Dashboard observation={observation} plan={plan} scanHistory={scanHistory} /> : null}
            {tab === "scan" ? (
              <ScanPanel
                folder={folder}
                setFolder={setFolder}
                minSizeMb={minSizeMb}
                setMinSizeMb={setMinSizeMb}
                fallback={fallback}
                loading={scanLoading}
                scanProgress={scanProgress}
                scanMessage={scanMessage}
                scanTargetLabel={scanTargetLabel}
                onScan={handleScan}
                onWholePcScan={handleWholePcScan}
                onCancelScan={handleCancelScan}
                browseFolders={browseFolders}
                ignoredFolders={ignoredFolders}
                onIgnoreFolder={handleIgnoreFolder}
                onUnignoreFolder={handleUnignoreFolder}
                scanHistory={scanHistory}
              />
            ) : null}
            {tab === "plan" ? (
              <PlanView
                plan={plan}
                onQuarantine={handleQuarantine}
                onAutopilotQuarantine={handleAutopilotQuarantine}
                loading={quarantineLoading}
              />
            ) : null}
            {tab === "quarantine" ? (
              <QuarantineView
                records={quarantineRecords}
                onRestore={handleRestore}
                loadingId={restoreLoadingId}
                onPermanentDelete={handlePermanentDelete}
                deleteLoadingId={deleteLoadingId}
              />
            ) : null}
            {tab === "report" ? <ReportView report={report} auditEvents={auditEvents} /> : null}
            {tab === "settings" ? (
              <SchedulerPanel
                status={schedulerStatus}
                folder={folder}
                minSizeMb={minSizeMb}
                loading={schedulerLoading}
                onEnable={handleEnableWeeklyScan}
                onDisable={handleDisableWeeklyScan}
                onRunNow={handleRunWeeklyScanNow}
                onRefresh={() => refreshSideData().catch(() => {})}
              />
            ) : null}
          </div>
        </main>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
