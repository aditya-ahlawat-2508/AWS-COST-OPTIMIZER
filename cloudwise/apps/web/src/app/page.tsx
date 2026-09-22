import Link from "next/link";

const TIERS = [
  {
    name: "Free",
    price: "$0",
    features: ["1 AWS account", "Weekly scan", "Top 10 findings", "Read-only"],
  },
  {
    name: "Starter",
    price: "$29–49/mo",
    features: ["3 accounts", "Daily scans", "All findings", "AI copilot", "Slack digest", "Budgets & alerts"],
    highlighted: true,
  },
  {
    name: "Growth",
    price: "$149–299/mo",
    features: ["Unlimited accounts", "AWS Organizations", "Automation (schedules, approved fixes)", "Tag showback", "SSO"],
  },
];

export default function LandingPage() {
  return (
    <div className="flex-1">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="text-lg font-semibold">CloudWise</div>
        <nav className="flex items-center gap-6 text-sm text-muted">
          <Link href="/security" className="hover:text-foreground">
            Security
          </Link>
          <Link href="/demo" className="hover:text-foreground">
            Live demo
          </Link>
          <Link href="/sign-in" className="hover:text-foreground">
            Sign in
          </Link>
          <Link
            href="/sign-up"
            className="rounded-md bg-accent px-3 py-1.5 text-accent-foreground hover:opacity-90"
          >
            Get started
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-3xl px-6 py-24 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Find your AWS waste in 2 minutes. Read-only.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-muted">
          CloudWise is an AI FinOps engineer for teams without a FinOps person: connect read-only,
          get findings with dollar amounts, and fix them safely — dry-run first, snapshot before delete,
          fully audited.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/demo" className="rounded-md border border-border px-5 py-2.5 hover:bg-surface-2">
            Explore live demo
          </Link>
          <Link
            href="/sign-up"
            className="rounded-md bg-accent px-5 py-2.5 text-accent-foreground hover:opacity-90"
          >
            Connect your AWS (read-only)
          </Link>
        </div>
      </section>

      <section className="border-t border-border bg-surface px-6 py-16">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-center text-2xl font-semibold">Pricing</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`rounded-lg border p-6 ${
                  tier.highlighted ? "border-accent bg-accent/5" : "border-border bg-background"
                }`}
              >
                <div className="text-sm text-muted">{tier.name}</div>
                <div className="mt-1 text-2xl font-semibold tabular-nums">{tier.price}</div>
                <ul className="mt-4 space-y-2 text-sm text-muted">
                  {tier.features.map((f) => (
                    <li key={f}>· {f}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border px-6 py-8 text-center text-sm text-muted">
        <Link href="/security" className="hover:text-foreground">
          Security &amp; permissions
        </Link>
      </footer>
    </div>
  );
}
