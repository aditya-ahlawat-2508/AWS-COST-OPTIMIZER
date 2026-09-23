"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, type AWSAccount, type ChangeRequest, type Schedule, ApiError } from "@/lib/api";
import { StatusBadge } from "@/components/badges";
import { formatDate } from "@/lib/utils";

export default function AutomationPage() {
  const { getToken } = useAuth();
  const [requests, setRequests] = useState<ChangeRequest[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [accounts, setAccounts] = useState<AWSAccount[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<string | null>(null);

  const [newResourceId, setNewResourceId] = useState("");
  const [newAccountId, setNewAccountId] = useState("");
  const [newStartHour, setNewStartHour] = useState("9");
  const [newStopHour, setNewStopHour] = useState("18");

  async function load() {
    const token = await getToken();
    if (!token) return;
    const [cr, sch, acc] = await Promise.all([
      api.listChangeRequests(token),
      api.listSchedules(token),
      api.listAccounts(token),
    ]);
    setRequests(cr);
    setSchedules(sch);
    setAccounts(acc);
    if (acc.length > 0 && !newAccountId) setNewAccountId(acc[0].id);
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

  async function createSchedule() {
    if (!newAccountId || !newResourceId) return;
    setError(null);
    try {
      const token = await getToken();
      if (!token) return;
      await api.createSchedule(token, {
        account_id: newAccountId,
        resource_id: newResourceId,
        start_hour: parseInt(newStartHour, 10),
        stop_hour: parseInt(newStopHour, 10),
      });
      setNewResourceId("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create schedule.");
    }
  }

  async function deleteSchedule(id: string) {
    const token = await getToken();
    if (!token) return;
    await api.deleteSchedule(token, id);
    await load();
  }

  async function runSchedulesNow() {
    const token = await getToken();
    if (!token) return;
    const result = await api.runSchedulesNow(token);
    setRunResult(`Evaluated ${result.evaluated} schedule(s), took ${result.actions_taken} action(s).`);
  }

  return (
    <div className="space-y-8">
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

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Schedules</h2>
          <button
            onClick={runSchedulesNow}
            className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-surface-2"
          >
            Run schedules now
          </button>
        </div>
        {runResult && <p className="mb-3 text-sm text-muted">{runResult}</p>}
        <p className="mb-3 text-sm text-muted">
          Office-hours start/stop for tagged non-prod instances (requires the account to have
          connected the opt-in actions role).
        </p>

        {accounts.length > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <select
              value={newAccountId}
              onChange={(e) => setNewAccountId(e.target.value)}
              className="rounded-md border border-border bg-surface px-2 py-1.5 text-sm"
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.label ?? a.aws_account_id}
                </option>
              ))}
            </select>
            <input
              value={newResourceId}
              onChange={(e) => setNewResourceId(e.target.value)}
              placeholder="i-0123456789abcdef0"
              className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
            />
            <input
              type="number"
              value={newStartHour}
              onChange={(e) => setNewStartHour(e.target.value)}
              className="w-16 rounded-md border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <span className="text-xs text-muted">to</span>
            <input
              type="number"
              value={newStopHour}
              onChange={(e) => setNewStopHour(e.target.value)}
              className="w-16 rounded-md border border-border bg-surface px-2 py-1.5 text-sm"
            />
            <button
              onClick={createSchedule}
              className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-foreground"
            >
              Add schedule
            </button>
          </div>
        )}

        <div className="overflow-hidden rounded-lg border border-border bg-surface">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted">
                <th className="px-4 py-2 font-medium">Resource</th>
                <th className="px-4 py-2 font-medium">Hours</th>
                <th className="px-4 py-2 font-medium">Weekdays only</th>
                <th className="px-4 py-2 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {schedules.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-muted">
                    No schedules yet.
                  </td>
                </tr>
              )}
              {schedules.map((s) => (
                <tr key={s.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-mono text-xs">{s.resource_id}</td>
                  <td className="px-4 py-3 tabular-nums">
                    {s.start_hour}:00–{s.stop_hour}:00 {s.timezone}
                  </td>
                  <td className="px-4 py-3">{s.weekdays_only ? "Yes" : "No"}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => deleteSchedule(s.id)}
                      className="rounded-md border border-border px-3 py-1 text-xs hover:bg-surface-2"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
