"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, type Finding } from "@/lib/api";
import { FindingsTable } from "@/components/findings-table";
import { cn } from "@/lib/utils";

const TABS: { key: Finding["status"] | "all"; label: string }[] = [
  { key: "open", label: "Open" },
  { key: "approved", label: "Approved" },
  { key: "done", label: "Done" },
  { key: "dismissed", label: "Dismissed" },
];

export default function FindingsPage() {
  const { getToken } = useAuth();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [tab, setTab] = useState<Finding["status"] | "all">("open");
  const [riskFilter, setRiskFilter] = useState<string>("all");

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (!token) return;
      setFindings(await api.listFindings(token));
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = findings.filter((f) => {
    if (tab !== "all" && f.status !== tab) return false;
    if (riskFilter !== "all" && f.risk !== riskFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Recommendations</h1>

      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg border border-border bg-surface p-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm",
                tab === t.key ? "bg-accent text-accent-foreground" : "text-muted hover:text-foreground"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm"
        >
          <option value="all">All risk</option>
          <option value="low">Low risk</option>
          <option value="medium">Medium risk</option>
          <option value="high">High risk</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <FindingsTable findings={filtered} detailHref={(f) => `/dashboard/findings/${f.id}`} />
      </div>
    </div>
  );
}
