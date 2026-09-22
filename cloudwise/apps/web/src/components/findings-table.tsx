"use client";

import { useRouter } from "next/navigation";
import type { Finding } from "@/lib/api";
import { formatMoney, cn } from "@/lib/utils";
import { EffortBadge, RiskBadge, StatusBadge } from "@/components/badges";

export function FindingsTable({
  findings,
  detailHref,
}: {
  findings: Finding[];
  detailHref?: (finding: Finding) => string;
}) {
  const router = useRouter();

  if (findings.length === 0) {
    return <div className="p-6 text-sm text-muted">No findings here.</div>;
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-border text-left text-xs text-muted">
          <th className="px-4 py-2 font-medium">Resource</th>
          <th className="px-4 py-2 font-medium">Rule</th>
          <th className="px-4 py-2 font-medium">Monthly savings</th>
          <th className="px-4 py-2 font-medium">Effort</th>
          <th className="px-4 py-2 font-medium">Risk</th>
          <th className="px-4 py-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {findings.map((f) => (
          <tr
            key={f.id}
            onClick={detailHref ? () => router.push(detailHref(f)) : undefined}
            className={cn(
              "border-b border-border last:border-0 hover:bg-surface-2",
              detailHref && "cursor-pointer"
            )}
          >
            <td className="px-4 py-3 font-mono text-xs">{f.resource_id}</td>
            <td className="px-4 py-3 capitalize">{f.rule_id.replace(/_/g, " ")}</td>
            <td className="px-4 py-3 tabular-nums">{formatMoney(f.monthly_savings)}/mo</td>
            <td className="px-4 py-3">
              <EffortBadge effort={f.effort} />
            </td>
            <td className="px-4 py-3">
              <RiskBadge risk={f.risk} />
            </td>
            <td className="px-4 py-3">
              <StatusBadge status={f.status} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
