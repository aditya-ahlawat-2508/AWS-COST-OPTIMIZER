"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, type AuditLogEntry } from "@/lib/api";
import { formatDate } from "@/lib/utils";

export default function AuditLogPage() {
  const { getToken } = useAuth();
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (!token) return;
      setEntries(await api.listAuditLog(token));
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Audit log</h1>
      <p className="text-sm text-muted">
        Every automated action (services/actions/executor.py) and its outcome, success or failure.
      </p>
      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="px-4 py-2 font-medium">When</th>
              <th className="px-4 py-2 font-medium">Action</th>
              <th className="px-4 py-2 font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted">
                  No audit entries yet — they&apos;re written whenever an automated action runs.
                </td>
              </tr>
            )}
            {entries.map((entry) => (
              <tr key={entry.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 text-muted">{formatDate(entry.created_at)}</td>
                <td className="px-4 py-3 font-mono text-xs">{entry.action}</td>
                <td className="px-4 py-3 text-muted">
                  <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(entry.details)}</pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
