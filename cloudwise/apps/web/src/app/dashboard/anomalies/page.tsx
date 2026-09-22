import { MOCK_ANOMALIES, MOCK_BUDGETS } from "@/lib/mock-data";
import { formatMoney, formatDate } from "@/lib/utils";

export default function AnomaliesPage() {
  return (
    <div className="space-y-8">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h1 className="text-xl font-semibold">Anomalies</h1>
          <span className="rounded-full bg-warning/15 px-2 py-0.5 text-xs text-warning">Mock data</span>
        </div>
        <p className="mb-4 text-sm text-muted">
          No anomaly-detection service is built yet (blueprint: a daily spend model). This is what the
          screen looks like once one exists.
        </p>
        <div className="space-y-3">
          {MOCK_ANOMALIES.map((a) => (
            <div key={a.id} className="rounded-lg border border-border bg-surface p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{a.service}</span>
                <span className="text-sm font-semibold text-danger tabular-nums">+{formatMoney(a.delta)}</span>
              </div>
              <p className="mt-1 text-xs text-muted">{formatDate(a.detected_at)}</p>
              <p className="mt-2 text-sm">{a.summary}</p>
              <p className="mt-1 text-sm text-accent">{a.suggestion}</p>
            </div>
          ))}
        </div>
      </div>

      <div id="budgets">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Budgets</h2>
          <span className="rounded-full bg-warning/15 px-2 py-0.5 text-xs text-warning">Mock data</span>
        </div>
        <div className="space-y-3">
          {MOCK_BUDGETS.map((b) => {
            const pct = Math.min(100, Math.round((b.spent_so_far / b.monthly_budget) * 100));
            return (
              <div key={b.team} className="rounded-lg border border-border bg-surface p-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{b.team}</span>
                  <span className="tabular-nums text-muted">
                    {formatMoney(b.spent_so_far)} / {formatMoney(b.monthly_budget)}
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
