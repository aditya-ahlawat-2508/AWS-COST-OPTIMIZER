"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, type Anomaly, type Budget, ApiError } from "@/lib/api";
import { formatMoney, formatDate } from "@/lib/utils";

export default function AnomaliesPage() {
  const { getToken } = useAuth();
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [newBudgetName, setNewBudgetName] = useState("");
  const [newBudgetLimit, setNewBudgetLimit] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const token = await getToken();
    if (!token) return;
    const [a, b] = await Promise.all([api.listAnomalies(token), api.listBudgets(token)]);
    setAnomalies(a);
    setBudgets(b);
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot fetch on mount, not a derived-state loop
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createBudget() {
    const limit = parseFloat(newBudgetLimit);
    if (!newBudgetName || !limit) return;
    setError(null);
    try {
      const token = await getToken();
      if (!token) return;
      await api.createBudget(token, { name: newBudgetName, monthly_limit_usd: limit });
      setNewBudgetName("");
      setNewBudgetLimit("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create budget.");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="mb-1 text-xl font-semibold">Anomalies</h1>
        <p className="mb-4 text-sm text-muted">
          Each service&apos;s last 7 days vs. its prior 14-day baseline — a plain daily-spend
          comparison, not a model (see services/analytics/anomalies.py).
        </p>
        {anomalies.length === 0 ? (
          <div className="rounded-lg border border-border bg-surface p-4 text-sm text-muted">
            No anomalies detected. Needs at least 21 days of spend history per service to compare
            against.
          </div>
        ) : (
          <div className="space-y-3">
            {anomalies.map((a) => (
              <div key={a.service} className="rounded-lg border border-border bg-surface p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{a.service}</span>
                  <span className="text-sm font-semibold text-danger tabular-nums">
                    +{formatMoney(a.delta_monthly)}/mo
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted">Since {formatDate(a.since)}</p>
                <p className="mt-2 text-sm">
                  Averaging {formatMoney(a.recent_daily_avg)}/day, up from a{" "}
                  {formatMoney(a.baseline_daily_avg)}/day baseline.
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div id="budgets">
        <h2 className="mb-3 text-lg font-semibold">Budgets</h2>
        {error && <div className="mb-3 text-sm text-danger">{error}</div>}
        <div className="mb-4 flex gap-2">
          <input
            value={newBudgetName}
            onChange={(e) => setNewBudgetName(e.target.value)}
            placeholder="Budget name"
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
          />
          <input
            value={newBudgetLimit}
            onChange={(e) => setNewBudgetLimit(e.target.value)}
            placeholder="Monthly limit ($)"
            type="number"
            className="w-40 rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
          />
          <button
            onClick={createBudget}
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-foreground"
          >
            Add budget
          </button>
        </div>
        <div className="space-y-3">
          {budgets.length === 0 && <div className="text-sm text-muted">No budgets set yet.</div>}
          {budgets.map((b) => {
            const pct = Math.min(100, Math.round((b.spent_this_month / b.monthly_limit_usd) * 100));
            return (
              <div key={b.id} className="rounded-lg border border-border bg-surface p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{b.name}</span>
                  <span className="tabular-nums text-muted">
                    {formatMoney(b.spent_this_month)} / {formatMoney(b.monthly_limit_usd)}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className={pct >= 100 ? "h-full bg-danger" : "h-full bg-accent"}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
