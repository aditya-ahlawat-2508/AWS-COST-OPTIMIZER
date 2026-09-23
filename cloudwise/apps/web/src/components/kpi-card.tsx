import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  hint,
  hintTone = "muted",
}: {
  label: string;
  value: string;
  hint?: string;
  hintTone?: "muted" | "success" | "danger";
}) {
  return (
    <div className="card p-4 transition-shadow hover:shadow-md">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && (
        <div
          className={cn(
            "mt-1 text-xs",
            hintTone === "success" && "text-success",
            hintTone === "danger" && "text-danger",
            hintTone === "muted" && "text-muted"
          )}
        >
          {hint}
        </div>
      )}
    </div>
  );
}
