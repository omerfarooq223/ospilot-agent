import { Fragment, useState } from "react";
import { formatBytes } from "../utils";

function fileName(path) {
  return path?.split("/").filter(Boolean).pop() || path || "item";
}

export default function QuarantineView({ records, onRestore, loadingId, onPermanentDelete, deleteLoadingId }) {
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const activeRecords = records?.filter((record) => !record.permanently_deleted && !record.restored) || [];
  const recoveredBytes = records?.reduce((sum, record) => sum + (record.size_bytes || 0), 0) || 0;

  return (
    <section className="space-y-8">
      <div>
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-bold text-white">Quarantined Items</h2>
            <p className="text-sm font-medium text-slate-400">Safe storage for flagged files awaiting review.</p>
          </div>
          <span className="mono text-sm font-bold text-mint-300">{activeRecords.length} active</span>
        </div>

        <div className="table-shell overflow-x-auto">
          <table className="w-full min-w-[900px] text-left">
            <thead className="bg-ink-850 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Item Name / Path</th>
                <th className="px-5 py-3">Date Flagged</th>
                <th className="px-5 py-3">Size</th>
                <th className="px-5 py-3">Reason</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {records?.length ? (
                records.map((record) => {
                  const isDeleted = record.permanently_deleted;
                  const isRestored = record.restored;
                  const isConfirming = confirmDeleteId === record.id;
                  const isDeleting = deleteLoadingId === record.id;
                  const isRestoring = loadingId === record.id;
                  return (
                    <Fragment key={record.id}>
                      <tr className={`border-t border-ink-700 ${isDeleted ? "opacity-50" : ""}`}>
                        <td className="px-5 py-5">
                          <p className={`font-bold text-white ${isDeleted ? "line-through" : ""}`}>{fileName(record.original_path)}</p>
                          <p className="max-w-[420px] truncate text-sm font-medium text-slate-500">{record.original_path}</p>
                        </td>
                        <td className="px-5 py-5 font-medium text-slate-400">{record.flagged_at || record.created_at || "Recent"}</td>
                        <td className="mono px-5 py-5 font-bold text-slate-300">{formatBytes(record.size_bytes || 0)}</td>
                        <td className="px-5 py-5">
                          <span className={`status-pill ${/duplicate/i.test(record.reason) ? "bg-[#eab766]/20 text-[#3b2608]" : "bg-[#ef6a5c] text-white"}`}>
                            {record.reason}
                          </span>
                        </td>
                        <td className="px-5 py-5 text-right">
                          {isDeleted ? (
                            <span className="text-sm font-bold text-[#ffbcb2]">Deleted</span>
                          ) : isRestored ? (
                            <span className="text-sm font-bold text-mint-300">Restored</span>
                          ) : (
                            <div className="flex justify-end gap-3">
                              <button
                                type="button"
                                className="text-sm font-bold text-mint-300 disabled:opacity-50"
                                disabled={isRestoring || isDeleting}
                                onClick={() => onRestore(record.id)}
                              >
                                {isRestoring ? "Restoring..." : "Restore"}
                              </button>
                              <button
                                type="button"
                                className="text-sm font-bold text-[#ffbcb2] disabled:opacity-50"
                                disabled={isDeleting || isRestoring}
                                onClick={() => setConfirmDeleteId(record.id)}
                              >
                                {isDeleting ? "Deleting..." : "Delete"}
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                      {isConfirming ? (
                        <tr>
                          <td colSpan="5" className="border-t border-[#ff8f83]/25 bg-[#ff8f83]/10 px-5 py-4">
                            <div className="flex flex-wrap items-center gap-3">
                              <p className="flex-1 text-sm text-[#ffe4e0]">
                                Permanently delete <span className="font-bold">{fileName(record.original_path)}</span> from disk?
                              </p>
                              <button type="button" className="btn-danger" onClick={() => { setConfirmDeleteId(null); onPermanentDelete(record.id); }}>
                                Yes, Delete
                              </button>
                              <button type="button" className="btn-secondary" onClick={() => setConfirmDeleteId(null)}>
                                Cancel
                              </button>
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="5" className="border-t border-ink-700 px-5 py-8 text-center text-sm text-slate-500">
                    No quarantined items yet. Approved real scan items will appear here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="border-t border-ink-700 pt-8">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-bold text-white">Cleaning Reports</h2>
            <p className="text-sm font-medium text-slate-400">Quarantine storage metrics from real approved items.</p>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <div className="panel p-6">
            <p className="text-xs font-bold uppercase text-slate-500">Quarantined Space</p>
            <p className="mono mt-4 font-display text-5xl font-bold text-mint-300">{formatBytes(recoveredBytes)}</p>
            <p className="mt-4 text-sm font-bold text-mint-300">{records?.length || 0} total item(s)</p>
          </div>
          <div className="panel p-6">
            <p className="text-xs font-bold uppercase text-slate-500">Active Items</p>
            <p className="mono mt-4 font-display text-5xl font-bold text-sky-300">{activeRecords.length}</p>
            <p className="mt-4 text-sm font-medium text-slate-400">Restore or delete each item individually.</p>
          </div>
          <div className="panel p-6">
            <p className="text-xs font-bold uppercase text-slate-500">Safety Status</p>
            <div className="mt-6 flex items-center gap-5">
              <div className="grid h-16 w-16 place-items-center rounded-full border-2 border-mint-300 font-bold text-white">OK</div>
              <p className="text-sm font-medium text-slate-400">Items remain reversible until you choose permanent delete.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}