"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, type ChangeRequest, ApiError } from "@/lib/api";
import { StatusBadge } from "@/components/badges";
import { formatDate } from "@/lib/utils";

export default function AutomationPage() {
  const { getToken } = useAuth();
  const [requests, setRequests] = useState<ChangeRequest[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = await getToken();
    if (!token) return;
    setRequests(await api.listChangeRequests(token));
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot fetch on mount, not a derived-state loop
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function approve(id: string) {
    const token = await getToken();
    if (!token) return;
    setBusy(id);
    setError(null);
    try {
      await api.approveChangeRequest(token, id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't approve this change request.");
    } finally {
      setBusy(null);
    }
  }

  async function execute(id: string) {
    const token = await getToken();
    if (!token) return;
    setBusy(id);
    setError(null);
    try {
      await api.executeChangeRequest(token, id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't execute this change request.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Automation</h1>
        <p className="text-sm text-muted">
          Change requests proposed by the copilot (or a teammate). Every action is dry-run and
          re-checked immediately before it runs — see services/actions/handlers.py.
        </p>
      </div>

      {error && <div className="rounded-md border border-border bg-surface p-3 text-sm text-danger">{error}</div>}

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="px-4 py-2 font-medium">Action</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Requested</th>
              <th className="px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {requests.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  No change requests yet. Ask the copilot to propose one from a finding.
                </td>
              </tr>
            )}
            {requests.map((r) => (
              <tr key={r.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 capitalize">{r.action_type.replace(/_/g, " ")}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={r.status} />
                </td>
                <td className="px-4 py-3 text-muted">{formatDate(r.created_at)}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  {r.status === "pending" && (
                    <button
                      onClick={() => approve(r.id)}
                      disabled={busy === r.id}
                      className="rounded-md border border-border px-3 py-1 text-xs hover:bg-surface-2 disabled:opacity-50"
                    >
                      Approve
                    </button>
                  )}
                  {r.status === "approved" && (
                    <button
                      onClick={() => execute(r.id)}
                      disabled={busy === r.id}
                      className="rounded-md bg-accent px-3 py-1 text-xs text-accent-foreground disabled:opacity-50"
                    >
                      Execute
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
