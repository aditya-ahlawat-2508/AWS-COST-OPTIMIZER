import { cn } from "@/lib/utils";

const RISK_STYLES: Record<string, string> = {
  low: "bg-success/15 text-success",
  medium: "bg-warning/15 text-warning",
  high: "bg-danger/15 text-danger",
};

const STATUS_STYLES: Record<string, string> = {
  open: "bg-accent/15 text-accent",
  approved: "bg-warning/15 text-warning",
  done: "bg-success/15 text-success",
  dismissed: "bg-surface-2 text-muted",
  pending: "bg-warning/15 text-warning",
  executed: "bg-success/15 text-success",
  failed: "bg-danger/15 text-danger",
  rejected: "bg-surface-2 text-muted",
};

function Badge({ text, className }: { text: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize", className)}>
      {text}
    </span>
  );
}

export function RiskBadge({ risk }: { risk: string }) {
  return <Badge text={risk} className={RISK_STYLES[risk] ?? "bg-surface-2 text-muted"} />;
}

export function EffortBadge({ effort }: { effort: string }) {
  return <Badge text={effort} className="bg-surface-2 text-muted" />;
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge text={status} className={STATUS_STYLES[status] ?? "bg-surface-2 text-muted"} />;
}
