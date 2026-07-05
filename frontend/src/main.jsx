import { StrictMode, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { open } from "@tauri-apps/plugin-dialog";
import {
  cancelScanJob,
  disableWeeklyScan,
  enableWeeklyScan,
  getScanHistory,
  getScanJob,
  getHealth,
  getSchedulerStatus,
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

const USER_NAME = "Muhammad Umar Farooq";
const USER_INITIALS = "MU";
const MESSAGE_DISMISS_MS = 5000;
const GITHUB_URL = "https://github.com/omerfarooq223/ospilot-agent";
const PORTFOLIO_URL = "https://omerfarooq223.github.io";

async function openExternalUrl(url) {
  try {
    if (window.__TAURI_INTERNALS__) {
      const mod = await import("@tauri-apps/plugin-shell");
      await mod.open(url);
      return;
    }
  } catch (_) {
    // Browser fallback below.
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

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
    external: "M14 3h7v7M21 3l-9 9M5 5h5M5 5v14h14v-5",
    x: "M6 6l12 12M18 6 6 18",
    github: "M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22",
  };
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
      <path d={paths[name]} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ProfileModal({ onClose }) {
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="profile-title">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="Close profile links" onClick={onClose} />
      <section className="relative w-full max-w-[39rem] overflow-hidden rounded-lg border border-mint-500/30 dark:border-mint-300/30 bg-white dark:bg-ink-950 px-5 py-8 shadow-[0_24px_90px_rgba(0,0,0,0.7)] sm:px-10 sm:py-10">
        <div className="pointer-events-none absolute left-1/2 top-0 h-1 w-64 -translate-x-1/2 bg-mint-300 shadow-[0_0_36px_rgba(63,214,187,0.9)]" />
        <button type="button" className="absolute right-5 top-5 grid h-10 w-10 place-items-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-ink-950 dark:hover:bg-ink-850 dark:hover:text-white" onClick={onClose} title="Close">
            <Icon name="x" />
        </button>

        <div className="mx-auto flex max-w-2xl flex-col items-center text-center">
          <div className="grid h-28 w-28 place-items-center rounded-full border-2 border-mint-200 bg-mint-300 text-4xl font-black text-ink-950 shadow-[0_0_54px_rgba(63,214,187,0.38)] sm:h-32 sm:w-32 sm:text-5xl">
            {USER_INITIALS}
          </div>

          <h3 id="profile-title" className="mt-7 font-display text-2xl font-black tracking-tight text-ink-950 dark:text-white sm:text-4xl whitespace-nowrap">
            {USER_NAME}
          </h3>
          <p className="mono mt-5 text-sm font-black uppercase tracking-[0.55em] text-mint-500 dark:text-mint-300 sm:text-base">
            AI Engineer
          </p>

          <div className="mt-7 w-full rounded-md border border-mint-500/20 dark:border-mint-300/20 bg-slate-50 dark:bg-ink-900/80 px-5 py-5">
            <p className="text-base font-bold text-slate-800 dark:text-slate-200">OS Pilot Developer</p>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-400">
              Building a local-first AI workspace recovery agent for safer scans, approvals, quarantine, restore, and report export.
            </p>
          </div>
        </div>

        <div className="mx-auto mt-7 w-full max-w-2xl space-y-4">
          <button
            type="button"
            className="flex w-full items-center justify-center gap-3 rounded-md px-5 py-4 text-base font-black transition bg-black text-white hover:bg-slate-800 dark:bg-white dark:text-black dark:hover:bg-slate-200"
            onClick={() => openExternalUrl(GITHUB_URL)}
          >
            <Icon name="github" />
            <span>GitHub Repository</span>
          </button>
          <button
            type="button"
            className="flex w-full items-center justify-center gap-3 rounded-md border border-mint-500/70 dark:border-mint-300/70 bg-mint-500/10 dark:bg-mint-300/10 px-5 py-4 text-base font-black text-mint-500 dark:text-mint-300 transition hover:bg-mint-500/20 dark:hover:bg-mint-300/20"
            onClick={() => openExternalUrl(PORTFOLIO_URL)}
          >
            <Icon name="external" />
            <span>Visit Developer Portfolio</span>
          </button>
        </div>
      </section>
    </div>
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
  const [profileOpen, setProfileOpen] = useState(false);
  const activeScanJobRef = useRef(null);

  function resetScanProgress() {
    setScanLoading(false);
    setScanJobId(null);
    setScanProgress(0);
    setScanMessage("");
    setScanTargetLabel("");
    activeScanJobRef.current = null;
  }

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
    refreshSideData().catch(() => { });
  }, []);

  useEffect(() => {
    localStorage.setItem("os-pilot-theme", theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (!message) return undefined;
    const timeoutId = window.setTimeout(() => {
      setMessage((current) => (current === message ? "" : current));
    }, MESSAGE_DISMISS_MS);
    return () => window.clearTimeout(timeoutId);
  }, [message]);

  async function handleScan() {
    setError("");
    setMessage("");
    setTab("scan");
    let selectedFolder = "";

    try {
      const picked = await open({
        directory: true,
        multiple: false,
        title: "Choose a folder to scan",
      });
      if (!picked) {
        setMessage("Folder scan cancelled.");
        return;
      }
      selectedFolder = Array.isArray(picked) ? picked[0] : picked;
      setFolder(selectedFolder);
    } catch (err) {
      setError("The Mac folder picker is available in the desktop app. Launch OS Pilot with npm run desktop:dev.");
      return;
    }

    setScanLoading(true);
    setScanProgress(5);
    setScanTargetLabel(selectedFolder);
    setScanMessage(`Preparing scan for ${selectedFolder}...`);
    try {
      const started = await startScan(selectedFolder, minSizeMb);
      setScanJobId(started.job_id);
      activeScanJobRef.current = started.job_id;
      setScanProgress(10);
      pollScanJob(started.job_id);
    } catch (err) {
      setError(err.message);
      resetScanProgress();
    } finally {
      // completion happens in pollScanJob
    }
  }

  async function handleWholePcScan() {
    setFolder("~");
    setError("");
    setTab("scan");
    setMessage("Whole PC scan uses your user-owned space and skips OS protected folders.");
    setScanLoading(true);
    setScanProgress(5);
    setScanTargetLabel("Whole PC scan: user-owned space (~)");
    setScanMessage("Preparing whole PC scan...");
    try {
      const started = await startScan("~", minSizeMb);
      setScanJobId(started.job_id);
      activeScanJobRef.current = started.job_id;
      setScanProgress(10);
      pollScanJob(started.job_id);
    } catch (err) {
      setError(err.message);
      resetScanProgress();
    }
  }

  async function pollScanJob(jobId) {
    try {
      const job = await getScanJob(jobId);
      if (activeScanJobRef.current !== jobId) return;
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
        resetScanProgress();
        await refreshSideData();
        return;
      }
      if (job.status === "failed") {
        setError(job.error || "Scan failed.");
        resetScanProgress();
        return;
      }
      if (job.status === "cancelled") {
        setMessage("Scan cancelled.");
        resetScanProgress();
        return;
      }
      window.setTimeout(() => pollScanJob(jobId), 700);
    } catch (err) {
      if (activeScanJobRef.current !== jobId) return;
      setError(err.message);
      resetScanProgress();
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
      resetScanProgress();
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
      <div className="grid min-h-screen grid-cols-1 bg-ink-950 text-slate-200 lg:h-screen lg:grid-cols-[248px_1fr]">
        <aside className="flex border-b border-ink-700 bg-ink-900 lg:sticky lg:top-0 lg:h-screen lg:flex-col lg:border-b-0 lg:border-r">
          <div className="hidden px-7 py-7 lg:block">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-ink-700 bg-ink-850 text-mint-300">
                <Icon name="broom" />
              </span>
              <div>
                <h1 className="font-display text-lg font-bold tracking-tight text-white">OS Pilot</h1>
                <p className="mono text-[11px] uppercase tracking-[0.14em] text-slate-500">Local-First Utility</p>
              </div>
            </div>
          </div>
          <div className="tick-rule mx-7 hidden lg:block" />

          <nav className="flex w-full gap-1 overflow-x-auto px-3 py-3 lg:mt-2 lg:block lg:space-y-1 lg:px-4 lg:py-5">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`flex min-w-max items-center gap-3 rounded-md border-l-2 px-4 py-2.5 text-left text-sm font-semibold transition lg:w-full lg:min-w-0 ${tab === item.id
                    ? "border-mint-300 bg-mint-300/10 text-mint-200"
                    : "border-transparent text-slate-400 hover:bg-ink-850 hover:text-slate-200"
                  }`}
              >
                <Icon name={item.icon} />
                {item.label}
              </button>
            ))}
          </nav>

          <div className="mt-auto hidden space-y-4 border-t border-ink-700 p-6 lg:block">
            <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              <span className="flex items-center gap-1.5"><span className="channel-dot bg-mint-300" /> Safe</span>
              <span className="flex items-center gap-1.5"><span className="channel-dot" style={{ background: "#eab766" }} /> Caution</span>
              <span className="flex items-center gap-1.5"><span className="channel-dot" style={{ background: "#ff8f83" }} /> Risk</span>
            </div>
            <button type="button" className="btn-primary w-full" onClick={() => setTab("scan")}>
              <Icon name="plus" /> New Scan
            </button>
          </div>
        </aside>

        <main className="min-w-0 lg:h-screen lg:overflow-y-auto">
          <header className="sticky top-0 z-10 border-b border-ink-700 bg-ink-950/95 backdrop-blur">
            <div className="flex min-h-[68px] flex-wrap items-center justify-between gap-4 px-5 py-4 xl:px-8">
              <form className="relative min-w-[260px] flex-1 lg:max-w-xl" onSubmit={handleSearchSubmit}>
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
                  <Icon name="search" />
                </span>
                <input
                  className="field pl-11"
                  placeholder="Search paths, files, or tasks..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
              </form>
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  className="btn-secondary min-h-10 px-3"
                  onClick={() => setTheme((current) => (current === "dark" ? "light" : "dark"))}
                  title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                >
                  <Icon name={theme === "dark" ? "sun" : "moon"} />
                  <span className="hidden sm:inline">{theme === "dark" ? "Light" : "Dark"}</span>
                </button>
                <span className="mono hidden rounded-md border border-ink-700 bg-ink-850 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500 sm:inline-flex">
                  {fallback ? "NODE_01_LOCAL" : "System Active"}
                </span>
                <div className="hidden h-8 border-l border-ink-700 sm:block" />
                <button
                  type="button"
                  className="flex items-center gap-3 text-left"
                  title="Open profile links"
                  onClick={() => setProfileOpen(true)}
                >
                  <div className="hidden text-right sm:block">
                    <p className="text-sm font-bold text-white">{USER_NAME}</p>
                  </div>
                  <div className="grid h-9 w-9 place-items-center rounded-md border border-ink-700 bg-ink-850 text-sm font-bold text-mint-200">
                    {USER_INITIALS}
                  </div>
                </button>
              </div>
            </div>
          </header>

          <div className="px-5 py-6 xl:px-8">
            {message ? (
              <div className="mb-4 rounded-md border border-mint-500/30 bg-mint-500/10 px-4 py-3 text-sm text-mint-100">
                {message}
              </div>
            ) : null}
            {error ? (
              <div className="mb-4 rounded-md border border-[#ff8f83]/30 bg-[#ff8f83]/10 px-4 py-3 text-sm text-[#ffd7d1]">
                {error}
              </div>
            ) : null}

            <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="font-display text-2xl font-bold tracking-tight text-white">{contentTitle}</h2>
                <p className="mt-1 text-sm font-medium text-slate-400">
                  {tab === "overview" ? "Local-first / secure — no cloud uploads." : null}
                  {tab === "scan" ? "Scan a specific folder or your user-owned whole-computer space." : null}
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
                    Scan Whole PC
                  </button>
                </div>
              ) : null}
            </div>
            <div className="tick-rule mb-6" />

            {tab === "overview" ? <Dashboard observation={observation} plan={plan} scanHistory={scanHistory} /> : null}
            {tab === "scan" ? (
              <ScanPanel
                folder={folder}
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
                ignoredFolders={ignoredFolders}
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
                onRefresh={() => refreshSideData().catch(() => { })}
              />
            ) : null}
          </div>
        </main>
      </div>
      {profileOpen ? <ProfileModal onClose={() => setProfileOpen(false)} /> : null}
    </div>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
