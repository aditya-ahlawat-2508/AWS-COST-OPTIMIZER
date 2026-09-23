"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { api, type Finding, type SpendSummary } from "@/lib/api";
import { formatMoney } from "@/lib/utils";
import { KpiCard } from "@/components/kpi-card";
import { SpendChart } from "@/components/spend-chart";
import { FindingsTable } from "@/components/findings-table";
import { CopilotPanel } from "@/components/copilot-panel";

export default function OverviewPage() {
  const { getToken } = useAuth();
  const [spend, setSpend] = useState<SpendSummary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await getToken();
      if (!token) return;
      try {
        const [spendData, findingsData] = await Promise.all([
          api.getSpend(token, { group_by: "service" }),
          api.listFindings(token),
        ]);
        if (!cancelled) {
          setSpend(spendData);
          setFindings(findingsData);
        }
      } catch {
        if (!cancelled) setError("Couldn't load your data. Have you connected an AWS account yet?");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [getToken]);

  const openFindings = findings.filter((f) => f.status === "open");
  const savingsFound = openFindings.reduce((sum, f) => sum + f.monthly_savings, 0);
  const realizedFindings = findings.filter((f) => f.status === "done");
  const realizedSavings = realizedFindings.reduce((sum, f) => sum + f.monthly_savings, 0);
  const topFindings = [...openFindings].sort((a, b) => b.monthly_savings - a.monthly_savings).slice(0, 5);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Overview</h1>
          <p className="text-sm text-muted">Last 30 days</p>
        </div>

        {loading && <div className="text-sm text-muted">Loading…</div>}
        {error && (
          <div className="card p-4 text-sm text-muted">
            {error}{" "}
            <Link href="/dashboard/connect" className="text-accent hover:underline">
              Connect an account
            </Link>
            .
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <KpiCard label="Spend (30d)" value={spend ? formatMoney(spend.total_cost) : "—"} />
          <KpiCard label="Savings found" value={formatMoney(savingsFound)} hint={`${openFindings.length} findings`} />
          <KpiCard
            label="Realized"
            value={formatMoney(realizedSavings)}
            hint={`${realizedFindings.length} fixes`}
            hintTone="success"
          />
          <KpiCard label="Open findings" value={String(openFindings.length)} />
        </div>

        <div className="card p-4">
          <div className="mb-2 text-sm font-medium">Spend by service</div>
          <SpendChart data={spend?.breakdown ?? []} />
        </div>

        <div className="card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="text-sm font-medium">Top recommendations</div>
            <Link href="/dashboard/findings" className="text-xs text-accent hover:underline">
              View all
            </Link>
          </div>
          <FindingsTable
            findings={topFindings}
            detailHref={(f) => `/dashboard/findings/${f.id}`}
          />
        </div>
      </div>

      <div className="h-[560px] lg:h-auto">
        <CopilotPanel getToken={getToken} />
      </div>
    </div>
  );
}
