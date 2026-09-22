"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, type SpendSummary } from "@/lib/api";
import { SpendChart } from "@/components/spend-chart";
import { formatMoney, cn } from "@/lib/utils";

const GROUP_OPTIONS = [
  { key: "service", label: "Service" },
  { key: "account", label: "Account" },
  { key: "day", label: "Day" },
] as const;

export default function CostExplorerPage() {
  const { getToken } = useAuth();
  const [groupBy, setGroupBy] = useState<(typeof GROUP_OPTIONS)[number]["key"]>("service");
  const [view, setView] = useState<"unblended" | "amortized">("unblended");
  const [spend, setSpend] = useState<SpendSummary | null>(null);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (!token) return;
      setSpend(await api.getSpend(token, { group_by: groupBy, view }));
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupBy, view]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Cost explorer</h1>
        <div className="flex items-center gap-2 text-sm">
          <div className="flex gap-1 rounded-lg border border-border bg-surface p-1">
            {(["unblended", "amortized"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={cn(
                  "rounded-md px-3 py-1 capitalize",
                  view === v ? "bg-accent text-accent-foreground" : "text-muted"
                )}
              >
                {v}
              </button>
            ))}
          </div>
          <select
            value={groupBy}
            onChange={(e) => setGroupBy(e.target.value as typeof groupBy)}
            className="rounded-md border border-border bg-surface px-3 py-1.5"
          >
            {GROUP_OPTIONS.map((o) => (
              <option key={o.key} value={o.key}>
                Group by {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-surface p-4">
        <div className="text-sm text-muted">Total ({view})</div>
        <div className="text-2xl font-semibold tabular-nums">{spend ? formatMoney(spend.total_cost) : "—"}</div>
        <div className="mt-4">
          <SpendChart data={spend?.breakdown ?? []} />
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="px-4 py-2 font-medium capitalize">{groupBy}</th>
              <th className="px-4 py-2 font-medium">Cost</th>
            </tr>
          </thead>
          <tbody>
            {(spend?.breakdown ?? []).map((row) => (
              <tr key={row.key} className="border-b border-border last:border-0">
                <td className="px-4 py-3">{row.key}</td>
                <td className="px-4 py-3 tabular-nums">{formatMoney(row.cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
