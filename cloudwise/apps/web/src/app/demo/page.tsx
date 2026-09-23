"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Finding, type SpendSummary } from "@/lib/api";
import { formatMoney } from "@/lib/utils";
import { KpiCard } from "@/components/kpi-card";
import { SpendChart } from "@/components/spend-chart";
import { FindingsTable } from "@/components/findings-table";

export default function DemoOverviewPage() {
  const [spend, setSpend] = useState<SpendSummary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);

  useEffect(() => {
    (async () => {
      const [spendData, findingsData] = await Promise.all([
        api.demoSpend({ group_by: "service" }),
        api.demoFindings(),
      ]);
      setSpend(spendData);
      setFindings(findingsData);
    })();
  }, []);

  const openFindings = findings.filter((f) => f.status === "open");
  const savingsFound = openFindings.reduce((sum, f) => sum + f.monthly_savings, 0);
  const realized = findings.filter((f) => f.status === "done");
  const realizedSavings = realized.reduce((sum, f) => sum + f.monthly_savings, 0);
  const topFindings = [...openFindings].sort((a, b) => b.monthly_savings - a.monthly_savings).slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Overview</h1>
        <p className="text-sm text-muted">Last 30 days · Acme Demo</p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard label="Spend (30d)" value={spend ? formatMoney(spend.total_cost) : "—"} />
        <KpiCard label="Savings found" value={formatMoney(savingsFound)} hint={`${openFindings.length} findings`} />
        <KpiCard
          label="Realized"
          value={formatMoney(realizedSavings)}
          hint={`${realized.length} fixes`}
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
          <Link href="/demo/findings" className="text-xs text-accent hover:underline">
            View all
          </Link>
        </div>
        <FindingsTable findings={topFindings} />
      </div>
    </div>
  );
}
