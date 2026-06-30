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
            <p className="text-sm font-semibold text-slate-300">Safe storage for flagged files awaiting review.</p>
          </div>
          <span className="text-sm font-bold text-mint-300">{activeRecords.length} active</span>
        </div>

        <div className="table-shell overflow-x-auto">
          <table className="w-full min-w-[900px] text-left">
            <thead className="bg-[#202222] text-sm uppercase text-slate-400">
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
                      <tr className={`border-t border-[#303a39] ${isDeleted ? "opacity-50" : ""}`}>
                        <td className="px-5 py-5">
                          <p className={`font-bold text-white ${isDeleted ? "line-through" : ""}`}>{fileName(record.original_path)}</p>
                          <p className="max-w-[420px] truncate text-sm font-semibold text-slate-500">{record.original_path}</p>
                        </td>
                        <td className="px-5 py-5 font-semibold text-slate-300">{record.flagged_at || record.created_at || "Recent"}</td>
                        <td className="px-5 py-5 font-bold text-slate-300">{formatBytes(record.size_bytes || 0)}</td>
                        <td className="px-5 py-5">
                          <span className={`status-pill ${/duplicate/i.test(record.reason) ? "bg-[#ffb454] text-[#3b2608]" : "bg-[#cf1020] text-white"}`}>
                            {record.reason}
                          </span>
                        </td>
                        <td className="px-5 py-5 text-right">
                          {isDeleted ? (
                            <span className="text-sm font-bold text-rose-300">Deleted</span>
                          ) : isRestored ? (
                            <span className="text-sm font-bold text-mint-300">Restored</span>
                          ) : (
                            <div className="flex justify-end gap-3">
                              <button
                                type="button"
                                className="font-bold text-mint-300 disabled:opacity-50"
                                disabled={isRestoring || isDeleting}
                                onClick={() => onRestore(record.id)}
                              >
                                {isRestoring ? "Restoring..." : "Restore"}
                              </button>
                              <button
                                type="button"
                                className="font-bold text-[#ffaea8] disabled:opacity-50"
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
                          <td colSpan="5" className="border-t border-rose-500/30 bg-rose-500/10 px-5 py-4">
                            <div className="flex flex-wrap items-center gap-3">
                              <p className="flex-1 text-sm text-rose-100">
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
                  <td colSpan="5" className="border-t border-[#303a39] px-5 py-8 text-center text-sm text-slate-500">
                    No quarantined items yet. Approved real scan items will appear here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="border-t border-[#303a39] pt-8">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-bold text-white">Cleaning Reports</h2>
            <p className="text-sm font-semibold text-slate-300">Quarantine storage metrics from real approved items.</p>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          <div className="panel p-6">
            <p className="text-sm font-bold uppercase text-slate-400">Quarantined Space</p>
            <p className="mt-4 font-display text-5xl font-bold text-mint-300">{formatBytes(recoveredBytes)}</p>
            <p className="mt-4 font-bold text-mint-300">{records?.length || 0} total item(s)</p>
          </div>
          <div className="panel p-6">
            <p className="text-sm font-bold uppercase text-slate-400">Active Items</p>
            <p className="mt-4 font-display text-5xl font-bold text-sky-300">{activeRecords.length}</p>
            <p className="mt-4 text-sm font-semibold text-slate-300">Restore or delete each item individually.</p>
          </div>
          <div className="panel p-6">
            <p className="text-sm font-bold uppercase text-slate-400">Safety Status</p>
            <div className="mt-6 flex items-center gap-5">
              <div className="grid h-16 w-16 place-items-center rounded-full border-4 border-mint-300 font-bold text-white">OK</div>
              <p className="font-semibold text-slate-300">Items remain reversible until you choose permanent delete.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
