"use client";

import { useEffect, useState } from "react";
import { api, type AWSAccount } from "@/lib/api";
import { StatusBadge } from "@/components/badges";
import { formatDate } from "@/lib/utils";

export default function DemoAccountsPage() {
  const [accounts, setAccounts] = useState<AWSAccount[]>([]);

  useEffect(() => {
    api.demoAccounts().then(setAccounts);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Accounts</h1>
      <div className="overflow-hidden card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="px-4 py-2 font-medium">Label</th>
              <th className="px-4 py-2 font-medium">AWS Account ID</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Connected</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((a) => (
              <tr key={a.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3">{a.label ?? "—"}</td>
                <td className="px-4 py-3 font-mono text-xs">{a.aws_account_id}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={a.status} />
                </td>
                <td className="px-4 py-3 text-muted">{formatDate(a.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
