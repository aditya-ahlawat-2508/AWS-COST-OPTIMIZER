import { MOCK_AUDIT_LOG } from "@/lib/mock-data";
import { formatDate } from "@/lib/utils";

export default function AuditLogPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Audit log</h1>
        <span className="rounded-full bg-warning/15 px-2 py-0.5 text-xs text-warning">Mock data</span>
      </div>
      <p className="text-sm text-muted">
        apps/api/app/models.py has an audit_log table and services/actions writes to it on every
        execution, but there&apos;s no GET endpoint exposing it yet — this is what the screen looks like
        once one exists.
      </p>
      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="px-4 py-2 font-medium">When</th>
              <th className="px-4 py-2 font-medium">Actor</th>
              <th className="px-4 py-2 font-medium">Action</th>
              <th className="px-4 py-2 font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_AUDIT_LOG.map((entry) => (
              <tr key={entry.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 text-muted">{formatDate(entry.timestamp)}</td>
                <td className="px-4 py-3">{entry.actor}</td>
                <td className="px-4 py-3 font-mono text-xs">{entry.action}</td>
                <td className="px-4 py-3 text-muted">{entry.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
