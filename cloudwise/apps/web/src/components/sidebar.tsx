"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  LineChart,
  ListChecks,
  AlertTriangle,
  Wallet,
  Zap,
  Server,
  ScrollText,
  Settings,
  Cloud,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/cost-explorer", label: "Cost explorer", icon: LineChart },
  { href: "/dashboard/findings", label: "Recommendations", icon: ListChecks },
  { href: "/dashboard/anomalies", label: "Anomalies", icon: AlertTriangle },
  { href: "/dashboard/anomalies#budgets", label: "Budgets", icon: Wallet },
  { href: "/dashboard/automation", label: "Automation", icon: Zap },
  { href: "/dashboard/accounts", label: "Accounts", icon: Server },
  { href: "/dashboard/audit-log", label: "Audit log", icon: ScrollText },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ orgLabel, footer }: { orgLabel?: string; footer?: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
      <div className="border-b border-border px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-accent-foreground">
            <Cloud size={14} />
          </div>
          <span className="text-base font-semibold">CloudWise</span>
        </div>
        {orgLabel && <div className="mt-1.5 truncate text-xs text-muted">{orgLabel}</div>}
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href.split("#")[0];
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent/15 text-accent"
                  : "text-muted hover:bg-surface-2 hover:text-foreground"
              )}
            >
              <Icon size={16} className={isActive ? "text-accent" : "text-muted"} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      {footer && <div className="border-t border-border p-3">{footer}</div>}
    </aside>
  );
}
