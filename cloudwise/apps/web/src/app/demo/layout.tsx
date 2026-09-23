"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Cloud, LayoutDashboard, LineChart, ListChecks, Server } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/demo", label: "Overview", icon: LayoutDashboard },
  { href: "/demo/cost-explorer", label: "Cost explorer", icon: LineChart },
  { href: "/demo/findings", label: "Recommendations", icon: ListChecks },
  { href: "/demo/accounts", label: "Accounts", icon: Server },
];

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-warning/30 bg-warning/10 px-6 py-2 text-sm">
        <span>
          <strong>Demo mode</strong> — synthetic &quot;Acme Demo&quot; data, made up numbers. Nothing
          here is a real AWS account, and no write action actually runs anything.
        </span>
        <Link href="/sign-up" className="rounded-md bg-accent px-3 py-1 text-xs text-accent-foreground">
          Connect your own AWS
        </Link>
      </div>
      <div className="flex flex-1">
        <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-surface">
          <div className="border-b border-border px-4 py-4">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-accent-foreground">
                <Cloud size={14} />
              </div>
              <span className="text-base font-semibold">CloudWise</span>
            </Link>
            <div className="mt-1.5 truncate text-xs text-muted">Acme Demo</div>
          </div>
          <nav className="flex-1 space-y-0.5 p-2">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive ? "bg-accent/15 text-accent" : "text-muted hover:bg-surface-2 hover:text-foreground"
                  )}
                >
                  <Icon size={16} className={isActive ? "text-accent" : "text-muted"} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
