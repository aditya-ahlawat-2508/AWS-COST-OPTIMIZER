import Link from "next/link";

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-warning/30 bg-warning/10 px-6 py-2 text-sm">
        <span>
          <strong>Demo mode</strong> — synthetic &quot;Acme Demo&quot; data. Nothing here is a real AWS
          account, and no write action actually runs anything.
        </span>
        <Link href="/sign-up" className="rounded-md bg-accent px-3 py-1 text-xs text-accent-foreground">
          Connect your own AWS
        </Link>
      </div>
      <div className="flex flex-1">
        <aside className="w-60 shrink-0 border-r border-border bg-surface p-4">
          <Link href="/" className="text-lg font-semibold">
            CloudWise
          </Link>
          <div className="mt-1 text-xs text-muted">Acme Demo</div>
          <nav className="mt-6 space-y-1 text-sm">
            <Link href="/demo" className="block rounded-md bg-accent/15 px-3 py-2 text-accent">
              Overview
            </Link>
            <Link href="/demo/findings" className="block rounded-md px-3 py-2 text-muted hover:bg-surface-2">
              Recommendations
            </Link>
          </nav>
        </aside>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
