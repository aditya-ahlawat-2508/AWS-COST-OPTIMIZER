"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { api, type AWSAccount, ApiError } from "@/lib/api";
import { StatusBadge } from "@/components/badges";
import { formatDate } from "@/lib/utils";

export default function AccountsPage() {
  const { getToken } = useAuth();
  const [accounts, setAccounts] = useState<AWSAccount[]>([]);
  const [scanning, setScanning] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const token = await getToken();
    if (!token) return;
    setAccounts(await api.listAccounts(token));
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot fetch on mount, not a derived-state loop
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function scan(accountId: string) {
    const token = await getToken();
    if (!token) return;
    setScanning(accountId);
    setMessage(null);
    try {
      const result = await api.scanAccount(token, accountId);
      setMessage(`Scanned ${result.resources_scanned} resources, found ${result.findings_written} findings.`);
      await load();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Scan failed.");
    } finally {
      setScanning(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Accounts</h1>
        <Link href="/dashboard/connect" className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-foreground">
          Connect AWS
        </Link>
      </div>

      {message && <div className="rounded-md border border-border bg-surface p-3 text-sm">{message}</div>}

      <div className="overflow-hidden card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="px-4 py-2 font-medium">Label</th>
              <th className="px-4 py-2 font-medium">AWS Account ID</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Connected</th>
              <th className="px-4 py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {accounts.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-muted">
                  No accounts connected yet.
                </td>
              </tr>
            )}
            {accounts.map((a) => (
              <tr key={a.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3">{a.label ?? "—"}</td>
                <td className="px-4 py-3 font-mono text-xs">{a.aws_account_id}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={a.status} />
                </td>
                <td className="px-4 py-3 text-muted">{formatDate(a.created_at)}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => scan(a.id)}
                    disabled={scanning === a.id}
                    className="rounded-md border border-border px-3 py-1 text-xs hover:bg-surface-2 disabled:opacity-50"
                  >
                    {scanning === a.id ? "Scanning…" : "Scan now"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
