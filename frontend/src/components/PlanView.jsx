import { Fragment, useEffect, useMemo, useState } from "react";
import { formatBytes, riskClass } from "../utils";

function riskLabel(action) {
  if (action.risk_level === "Low") return "SAFE";
  if (action.risk_level === "Medium") return "MED";
  if (action.risk_level === "High") return "HIGH";
  return action.risk_level || "REVIEW";
}

function scenarioTone(index) {
  return [
    "border-mint-300 shadow-[0_0_0_1px_rgba(63,214,187,0.3)]",
    "border-sky-300 shadow-[0_0_0_1px_rgba(125,211,252,0.3)]",
    "border-[#ff8f83] shadow-[0_0_0_1px_rgba(255,143,131,0.3)]",
  ][index] || "border-ink-700";
}

function scenarioId(value) {
  return String(value || "").toLowerCase();
}

function actionActivityDays(action) {
  if (typeof action.days_since_opened === "number") return action.days_since_opened;
  if (typeof action.dormant_days === "number") return action.dormant_days;
  return null;
}

function actionActivityLabel(action) {
  const days = actionActivityDays(action);
  if (days === null) return "Unknown";
  if (days === 0) return "Today";
  if (days === 1) return "1 day";
  return `${days} days`;
}

export default function PlanView({ plan, onQuarantine, onAutopilotQuarantine, loading }) {
  const [selected, setSelected] = useState(new Set());
  const [expanded, setExpanded] = useState(new Set());
  const [query, setQuery] = useState("");
  const [scenarioFilter, setScenarioFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [sortKey, setSortKey] = useState("priority");
  const [visibleCount, setVisibleCount] = useState(10);

  const cleanupActions = plan?.cleanup_actions || [];
  const advisoryActions = plan?.performance_recommendations || [];
  const blockedActions = plan?.blocked_actions || [];
  const allActions = [...cleanupActions, ...advisoryActions, ...blockedActions];
  const lowActions = cleanupActions.filter((action) => action.risk_level === "Low");
  const balancedActions = cleanupActions.filter((action) => ["Low", "Medium"].includes(action.risk_level));
  const fallbackScenarios = [
    {
      scenario_id: "conservative",
      name: "Conservative",
      description: "Safe Mode",
      estimated_recoverable_bytes: lowActions.reduce((sum, action) => sum + (action.size_bytes || 0), 0),
      item_count: lowActions.length,
      confidence: lowActions.length ? Math.round(lowActions.reduce((sum, action) => sum + (action.confidence || 0), 0) / lowActions.length) : 0,
      risk: "Low",
      action_ids: lowActions.map((action) => action.action_id),
    },
    {
      scenario_id: "balanced",
      name: "Balanced",
      description: "Recommended",
      estimated_recoverable_bytes: balancedActions.reduce((sum, action) => sum + (action.size_bytes || 0), 0),
      item_count: balancedActions.length,
      confidence: balancedActions.length ? Math.round(balancedActions.reduce((sum, action) => sum + (action.confidence || 0), 0) / balancedActions.length) : 0,
      risk: "Medium",
      action_ids: balancedActions.map((action) => action.action_id),
    },
    {
      scenario_id: "deep",
      name: "Deep Review",
      description: "Manual Required",
      estimated_recoverable_bytes: cleanupActions.reduce((sum, action) => sum + (action.size_bytes || 0), 0),
      item_count: cleanupActions.length,
      confidence: cleanupActions.length ? Math.round(cleanupActions.reduce((sum, action) => sum + (action.confidence || 0), 0) / cleanupActions.length) : 0,
      risk: cleanupActions.some((action) => action.risk_level === "High") ? "High" : "Medium",
      action_ids: cleanupActions.map((action) => action.action_id),
    },
  ];
  const scenarios = plan?.cleanup_scenarios?.length ? plan.cleanup_scenarios : fallbackScenarios;
  const scenarioActionIds = useMemo(() => {
    const map = new Map();
    scenarios.forEach((scenario) => {
      map.set(scenarioId(scenario.scenario_id || scenario.name), new Set(scenario.action_ids || []));
    });
    return map;
  }, [scenarios]);
  const filteredCleanup = useMemo(() => {
    const q = query.trim().toLowerCase();
    const scenarioIds = scenarioActionIds.get(scenarioFilter);
    const riskOrder = { Low: 1, Medium: 2, High: 3, "Needs Review": 4, Blocked: 5 };
    return [...cleanupActions]
      .filter((action) => {
        if (scenarioIds && !scenarioIds.has(action.action_id)) return false;
        if (riskFilter !== "all" && action.risk_level !== riskFilter) return false;
        if (!q) return true;
        return [action.path, action.reason, action.risk_level, action.recovery_recipe, action.project_type, action.rebuildability]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(q));
      })
      .sort((a, b) => {
        if (sortKey === "size_desc") return (b.size_bytes || 0) - (a.size_bytes || 0);
        if (sortKey === "size_asc") return (a.size_bytes || 0) - (b.size_bytes || 0);
        if (sortKey === "last_used_desc") return (actionActivityDays(b) ?? -1) - (actionActivityDays(a) ?? -1);
        if (sortKey === "last_used_asc") return (actionActivityDays(a) ?? Number.MAX_SAFE_INTEGER) - (actionActivityDays(b) ?? Number.MAX_SAFE_INTEGER);
        if (sortKey === "risk") return (riskOrder[b.risk_level] || 0) - (riskOrder[a.risk_level] || 0);
        return (b.priority_score || 0) - (a.priority_score || 0);
      });
  }, [cleanupActions, query, riskFilter, scenarioActionIds, scenarioFilter, sortKey]);
  const visibleCleanup = filteredCleanup.slice(0, visibleCount);
  const hasMoreRows = visibleCount < filteredCleanup.length;

  useEffect(() => {
    setVisibleCount(10);
  }, [query, riskFilter, scenarioFilter, sortKey]);

  function toggle(actionId) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(actionId)) next.delete(actionId);
      else next.add(actionId);
      return next;
    });
  }

  function toggleExpanded(actionId) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(actionId)) next.delete(actionId);
      else next.add(actionId);
      return next;
    });
  }

  function selectAllVisible() {
    setSelected(new Set(filteredCleanup.map((action) => action.action_id)));
  }

  function clearSelection() {
    setSelected(new Set());
  }

  function applyScenario(scenario) {
    if (scenario.action_ids?.length) {
      setSelected(new Set(scenario.action_ids));
    }
    setScenarioFilter(scenarioId(scenario.scenario_id || scenario.name));
    setVisibleCount(10);
  }

  if (!plan) {
    return (
      <section className="panel p-8 text-center">
        <p className="text-slate-400">Scan a folder to generate diagnosis and maintenance plan.</p>
      </section>
    );
  }

  const autopilotCount = cleanupActions.filter((action) => action.automation_eligible).length;

  return (
    <section className="space-y-6">
      <div className="panel rounded-md border-[#5b4228] bg-[#221c14] p-5">
        <div className="flex gap-4">
          <span className="channel-dot mt-1.5 shrink-0" style={{ background: "#eab766" }} />
          <div>
            <h3 className="font-display text-lg font-bold text-[#f6cf98]">Simulation Mode Active</h3>
            <p className="max-w-4xl text-sm font-medium leading-relaxed text-slate-400">
              The following items are projected cleanup targets. No files will be moved or deleted until you explicitly approve them and trigger the quarantine process.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {scenarios.slice(0, 3).map((scenario, index) => {
          const confidence = scenario.confidence ?? 0;
          const risk = scenario.risk || (index === 0 ? "Low" : index === 1 ? "Medium" : "High");
          return (
            <button
              key={scenario.scenario_id || scenario.name}
              type="button"
              className={`panel min-h-56 border p-5 text-left transition hover:bg-ink-850 ${scenarioTone(index)}`}
              onClick={() => applyScenario(scenario)}
            >
              <div className="mb-7 flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-xl font-bold text-white">{scenario.name}</h3>
                  <p className={`mt-2 text-xs font-bold uppercase tracking-wide ${index === 2 ? "text-[#ffbcb2]" : index === 1 ? "text-sky-300" : "text-mint-300"}`}>
                    {scenario.description || (index === 1 ? "Recommended" : "Safe Mode")}
                  </p>
                </div>
                <span className="mono rounded bg-ink-700 px-3 py-1 font-bold text-mint-300">
                  {formatBytes(scenario.estimated_recoverable_bytes || 0)}
                </span>
              </div>
              <dl className="space-y-3 text-sm font-medium">
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Item Count</dt>
                  <dd className="text-white">{scenario.item_count || 0} files</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Risk Level</dt>
                  <dd className={risk === "High" ? "text-[#ffbcb2]" : risk === "Medium" ? "text-[#f6cf98]" : "text-mint-300"}>{risk}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate-500">Confidence</dt>
                  <dd className="text-white">{confidence}%</dd>
                </div>
              </dl>
              <div className="mt-7 h-1.5 rounded-full bg-ink-700">
                <div className={`h-full rounded-full ${index === 2 ? "bg-[#ff8f83]" : index === 1 ? "bg-sky-300" : "bg-mint-300"}`} style={{ width: `${confidence}%` }} />
              </div>
            </button>
          );
        })}
      </div>

      <div className="panel rounded-md border-sky-300/25 bg-sky-500/10 p-4">
        <p className="text-sm font-medium leading-relaxed text-slate-300">
          Scenario cards are alternatives, not additive totals. Choose Conservative, Balanced, or Deep Review as a package; do not add the three numbers together. The scan's potential gain is the backend's overall recoverable estimate for the latest plan.
        </p>
      </div>

      <div className="panel flex flex-wrap items-center justify-between gap-4 p-5">
        <div className="flex flex-1 flex-wrap items-center gap-3">
          <span className="mr-2 text-sm font-bold text-slate-300">{selected.size} items selected</span>
          <button type="button" className="text-sm font-bold text-mint-300" onClick={selectAllVisible}>
            Select All
          </button>
          <button type="button" className="text-sm font-bold text-[#ffbcb2] disabled:text-slate-600" disabled={selected.size === 0} onClick={clearSelection}>
            Clear selection
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" disabled={loading || autopilotCount === 0} onClick={onAutopilotQuarantine}>
            Safe Autopilot {autopilotCount ? `(${autopilotCount})` : ""}
          </button>
          <button type="button" className="btn-primary" disabled={loading || selected.size === 0} onClick={() => onQuarantine([...selected])}>
            {loading ? "Quarantining..." : "Quarantine Selected"}
          </button>
        </div>
      </div>

      <div className="table-shell overflow-x-auto">
        <table className="w-full min-w-[1180px] table-fixed text-left">
          <colgroup>
            <col className="w-14" />
            <col className="w-[38%]" />
            <col className="w-[8%]" />
            <col className="w-[8%]" />
            <col className="w-[10%]" />
            <col className="w-[8%]" />
            <col className="w-[25%]" />
            <col className="w-[3%]" />
          </colgroup>
          <thead className="bg-ink-850 text-xs uppercase text-slate-500">
            <tr>
              <th className="w-14 px-5 py-4">
                <span className="sr-only">Selected</span>
              </th>
              <th className="px-5 py-4">Path</th>
              <th className="px-5 py-4">Size</th>
              <th className="px-5 py-4">Risk</th>
              <th className="px-5 py-4">Last Used</th>
              <th className="px-5 py-4">Confidence</th>
              <th className="px-5 py-4">Reason</th>
              <th className="px-5 py-4">Status</th>
            </tr>
            <tr className="border-t border-ink-700 bg-ink-900 normal-case">
              <th className="px-5 py-3" />
              <th className="px-5 py-3" colSpan="2">
                <input
                  className="field h-10 text-sm"
                  placeholder="Search paths, evidence, or reasons..."
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </th>
              <th className="px-5 py-3">
                <select className="field h-10 min-w-[130px] text-sm" value={riskFilter} onChange={(event) => setRiskFilter(event.target.value)}>
                  <option value="all">All risks</option>
                  <option value="Low">Low risk</option>
                  <option value="Medium">Medium risk</option>
                  <option value="High">High risk</option>
                </select>
              </th>
              <th className="px-5 py-3" colSpan="2">
                <select className="field h-10 min-w-[180px] text-sm" value={sortKey} onChange={(event) => setSortKey(event.target.value)}>
                  <option value="priority">Sort by priority</option>
                  <option value="size_desc">Largest first</option>
                  <option value="size_asc">Smallest first</option>
                  <option value="last_used_desc">Least recently used</option>
                  <option value="last_used_asc">Most recently used</option>
                  <option value="risk">Highest risk first</option>
                </select>
              </th>
              <th className="px-5 py-3" colSpan="2">
                <select className="field h-10 min-w-[180px] text-sm" value={scenarioFilter} onChange={(event) => setScenarioFilter(event.target.value)}>
                  <option value="all">All scenarios</option>
                  {scenarios.map((scenario) => (
                    <option key={scenario.scenario_id || scenario.name} value={scenarioId(scenario.scenario_id || scenario.name)}>
                      {scenario.name}
                    </option>
                  ))}
                </select>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredCleanup.length ? (
              visibleCleanup.map((action) => {
                const checked = selected.has(action.action_id);
                const isExpanded = expanded.has(action.action_id);
                return (
                  <Fragment key={action.action_id}>
                    <tr
                      className="cursor-pointer border-t border-ink-700 align-middle transition hover:bg-ink-850/60"
                      onClick={() => toggleExpanded(action.action_id)}
                    >
                      <td className="px-5 py-3" onClick={(event) => event.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggle(action.action_id)}
                          className="h-5 w-5 accent-mint-300"
                        />
                      </td>
                      <td className="px-5 py-3" title={action.path}>
                        <p className="mono truncate text-sm font-bold text-white">{action.path}</p>
                      </td>
                      <td className="mono px-5 py-3 text-base font-bold text-white">{formatBytes(action.size_bytes || 0)}</td>
                      <td className="px-5 py-3">
                        <span className={`status-pill ${riskClass(action.risk_level)}`}>{riskLabel(action)}</span>
                      </td>
                      <td className="mono px-5 py-3 text-sm font-bold text-slate-300">{actionActivityLabel(action)}</td>
                      <td className="mono px-5 py-3 text-base font-bold text-white">{action.confidence || "--"}%</td>
                      <td className="px-5 py-3" title={action.reason}>
                        <p className="truncate text-sm font-medium text-slate-400">{action.reason}</p>
                      </td>
                      <td className="px-5 py-3 text-center">
                        <span className={`channel-dot ${action.linked_processes?.length ? "" : "bg-mint-300"}`} style={action.linked_processes?.length ? { background: "#ff8f83" } : undefined} />
                      </td>
                    </tr>
                    {isExpanded ? (
                      <tr className="border-t border-ink-700 bg-ink-950/60">
                        <td colSpan="8" className="px-5 py-4">
                          <div className="grid gap-4 text-sm lg:grid-cols-[1.2fr_1fr]">
                            <div className="rounded-md border border-ink-700 bg-ink-900 p-4">
                              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Full Path</p>
                              <p className="mono break-all font-bold leading-relaxed text-white">{action.path || "No path recorded."}</p>
                            </div>
                            <div className="rounded-md border border-ink-700 bg-ink-900 p-4">
                              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Full Reason</p>
                              <p className="leading-relaxed text-slate-300">{action.reason || "No reason recorded."}</p>
                            </div>
                            <div className="rounded-md border border-ink-700 bg-ink-900 p-4">
                              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Evidence</p>
                              <p className="leading-relaxed text-slate-300">{action.evidence?.length ? action.evidence.join(", ") : "No evidence markers recorded."}</p>
                            </div>
                            <div className="rounded-md border border-ink-700 bg-ink-900 p-4">
                              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Recovery Recipe</p>
                              <p className="mono break-all leading-relaxed text-slate-300">{action.recovery_recipe || "Review manually before removing."}</p>
                            </div>
                          </div>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })
            ) : (
              <tr>
                <td colSpan="8" className="px-5 py-10 text-center text-slate-500">
                  No reversible cleanup actions match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {hasMoreRows ? (
          <div className="border-t border-ink-700 bg-ink-900 px-5 py-4 text-center">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setVisibleCount((current) => current + 10)}
            >
              Show more ({filteredCleanup.length - visibleCount} remaining)
            </button>
          </div>
        ) : filteredCleanup.length > 10 ? (
          <div className="border-t border-ink-700 bg-ink-900 px-5 py-4 text-center text-sm font-medium text-slate-500">
            Showing all {filteredCleanup.length} matching items
          </div>
        ) : null}
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <div className="panel p-5">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="font-display text-xl font-bold text-white">Workspace Intelligence</h3>
            {plan.diagnosis_result?.urgency_level && (
              <span className={`status-pill ${plan.diagnosis_result.urgency_level === 'high' ? 'bg-[#ff8f83] text-black' : plan.diagnosis_result.urgency_level === 'low' ? 'bg-mint-300 text-black' : 'bg-sky-300 text-black'}`}>
                {plan.diagnosis_result.urgency_level.toUpperCase()} URGENCY
              </span>
            )}
          </div>
          <p className="text-sm leading-relaxed text-slate-400">
            {plan.diagnosis_result?.summary || plan.workspace_profile?.summary || plan.diagnosis_summary}
          </p>
          {plan.scan_delta?.summary && (
            <p className="mt-3 text-sm font-medium leading-relaxed text-sky-300">
              ↳ {plan.scan_delta.summary}
            </p>
          )}
          {plan.diagnosis_result?.top_risks?.length > 0 && (
            <ul className="mt-4 space-y-2">
              {plan.diagnosis_result.top_risks.map((risk, i) => (
                <li key={i} className="flex gap-2 text-sm font-medium text-[#ffbcb2]">
                  <span className="channel-dot mt-1.5 shrink-0" style={{ background: "#ff8f83" }} /> <span>{risk}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-5 flex flex-wrap gap-2">
            {(plan.workspace_profile?.markers || []).slice(0, 14).map((marker) => (
              <span key={marker} className="status-pill border border-ink-700 bg-ink-850 text-slate-400">{marker}</span>
            ))}
          </div>
        </div>
        <div className="panel p-5">
          <h3 className="mb-3 font-display text-xl font-bold text-white">Manual Review</h3>
          <p className="mb-3 text-sm text-slate-500">{advisoryActions.length} advisory items and {blockedActions.length} blocked/protected items.</p>
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {[...advisoryActions, ...blockedActions].slice(0, 8).map((action) => (
              <div key={action.action_id} className="rounded-md border border-ink-700 bg-ink-850 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="mono max-w-md break-all text-sm font-bold text-white">{action.path || action.reason}</p>
                  <span className={`status-pill ${riskClass(action.risk_level)}`}>{riskLabel(action)}</span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{action.reason}</p>
              </div>
            ))}
            {!allActions.length ? <p className="text-sm text-slate-500">Run a scan to populate review details.</p> : null}
          </div>
        </div>
      </div>
    </section>
  );
}
