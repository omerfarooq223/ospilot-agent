import { useMemo, useState } from "react";
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

export default function PlanView({ plan, onQuarantine, onAutopilotQuarantine, loading }) {
  const [selected, setSelected] = useState(new Set());
  const [query, setQuery] = useState("");

  const cleanupActions = plan?.cleanup_actions || [];
  const advisoryActions = plan?.performance_recommendations || [];
  const blockedActions = plan?.blocked_actions || [];
  const allActions = [...cleanupActions, ...advisoryActions, ...blockedActions];
  const lowActions = cleanupActions.filter((action) => action.risk_level === "Low");
  const balancedActions = cleanupActions.filter((action) => ["Low", "Medium"].includes(action.risk_level));
  const filteredCleanup = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return cleanupActions;
    return cleanupActions.filter((action) =>
      [action.path, action.reason, action.risk_level, action.recovery_recipe, action.project_type]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(q)),
    );
  }, [cleanupActions, query]);

  function toggle(actionId) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(actionId)) next.delete(actionId);
      else next.add(actionId);
      return next;
    });
  }

  function selectAllVisible() {
    setSelected(new Set(filteredCleanup.map((action) => action.action_id)));
  }

  if (!plan) {
    return (
      <section className="panel p-8 text-center">
        <p className="text-slate-400">Scan a folder to generate diagnosis and maintenance plan.</p>
      </section>
    );
  }

  const scenarios = plan.cleanup_scenarios?.length
    ? plan.cleanup_scenarios
    : [
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
              onClick={() => scenario.action_ids?.length && setSelected(new Set(scenario.action_ids))}
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
        <div className="flex flex-wrap items-center gap-5">
          <span className="text-sm font-bold text-slate-300">{selected.size} items selected</span>
          <button type="button" className="text-sm font-bold text-mint-300" onClick={selectAllVisible}>
            Select all visible
          </button>
          <input
            className="field min-w-[260px] max-w-md"
            placeholder="Search paths, evidence, or reasons..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
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
        <table className="w-full min-w-[980px] text-left">
          <thead className="bg-ink-850 text-xs uppercase text-slate-500">
            <tr>
              <th className="w-14 px-5 py-4">
                <span className="sr-only">Selected</span>
              </th>
              <th className="px-5 py-4">Path</th>
              <th className="px-5 py-4">Size</th>
              <th className="px-5 py-4">Risk</th>
              <th className="px-5 py-4">Confidence</th>
              <th className="px-5 py-4">Reason</th>
              <th className="px-5 py-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredCleanup.length ? (
              filteredCleanup.map((action) => {
                const checked = selected.has(action.action_id);
                return (
                  <tr key={action.action_id} className="border-t border-ink-700 align-middle">
                    <td className="px-5 py-5">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(action.action_id)}
                        className="h-5 w-5 accent-mint-300"
                      />
                    </td>
                    <td className="mono min-w-[420px] max-w-[640px] break-all px-5 py-5 text-sm font-bold leading-relaxed text-white" title={action.path}>
                      {action.path}
                    </td>
                    <td className="mono px-5 py-5 text-lg font-bold text-white">{formatBytes(action.size_bytes || 0)}</td>
                    <td className="px-5 py-5">
                      <span className={`status-pill ${riskClass(action.risk_level)}`}>{riskLabel(action)}</span>
                    </td>
                    <td className="mono px-5 py-5 text-lg font-bold text-white">{action.confidence || "--"}%</td>
                    <td className="max-w-[260px] px-5 py-5 text-sm font-medium text-slate-400">{action.reason}</td>
                    <td className="px-5 py-5">
                      <span className={`channel-dot ${action.linked_processes?.length ? "" : "bg-mint-300"}`} style={action.linked_processes?.length ? { background: "#ff8f83" } : undefined} />
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="7" className="px-5 py-10 text-center text-slate-500">
                  No reversible cleanup actions are currently available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
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