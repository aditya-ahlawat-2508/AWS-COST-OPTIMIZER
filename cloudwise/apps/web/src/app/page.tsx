import Link from "next/link";
import { ArrowRight, Check, Cloud, ShieldCheck, Sparkles } from "lucide-react";

const TIERS = [
  {
    name: "Free",
    price: "$0",
    period: "",
    features: ["1 AWS account", "Weekly scan", "Top 10 findings", "Read-only"],
  },
  {
    name: "Starter",
    price: "$29",
    period: "–49/mo",
    features: ["3 accounts", "Daily scans", "All findings", "AI copilot", "Slack digest", "Budgets & alerts"],
    highlighted: true,
  },
  {
    name: "Growth",
    price: "$149",
    period: "–299/mo",
    features: ["Unlimited accounts", "AWS Organizations", "Automation & schedules", "Tag showback", "SSO"],
  },
];

const FEATURES = [
  {
    icon: Cloud,
    title: "Connect read-only in 2 minutes",
    body: "A CloudFormation stack, an ExternalId, no long-lived keys — ever. Nothing writes to your account until you say so.",
  },
  {
    icon: Sparkles,
    title: "An AI copilot that shows its work",
    body: "Every dollar figure it says is checked against real data before you see it. It proposes fixes; a human approves them.",
  },
  {
    icon: ShieldCheck,
    title: "Safe by construction",
    body: "Dry-run first, re-check right before acting, full audit log. No delete or terminate permission exists in the automation role.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex-1">
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent text-accent-foreground">
              <Cloud size={16} />
            </div>
            <span className="text-lg font-semibold">CloudWise</span>
          </div>
          <nav className="flex items-center gap-6 text-sm text-muted">
            <Link href="/security" className="hidden hover:text-foreground sm:inline">
              Security
            </Link>
            <Link href="/demo" className="hidden hover:text-foreground sm:inline">
              Live demo
            </Link>
            <Link href="/sign-in" className="hover:text-foreground">
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="flex items-center gap-1 rounded-md bg-accent px-3 py-1.5 text-accent-foreground shadow-sm hover:opacity-90"
            >
              Get started
              <ArrowRight size={14} />
            </Link>
          </nav>
        </div>
      </header>

      <section className="bg-grid border-b border-border">
        <div className="mx-auto max-w-3xl px-6 py-28 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted">
            <Sparkles size={12} className="text-accent" />
            AI FinOps for teams without a FinOps person
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight sm:text-6xl">
            Find your AWS waste in{" "}
            <span className="bg-gradient-to-r from-accent to-indigo-300 bg-clip-text text-transparent">
              2 minutes
            </span>
            . Read-only.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-lg text-muted">
            Connect read-only, get findings with real dollar amounts, and fix them safely —
            dry-run first, snapshot before delete, fully audited.
          </p>
          <div className="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              href="/sign-up"
              className="flex items-center justify-center gap-1.5 rounded-md bg-accent px-6 py-3 font-medium text-accent-foreground shadow-md shadow-accent/20 hover:opacity-90"
            >
              Connect your AWS (read-only)
              <ArrowRight size={16} />
            </Link>
            <Link
              href="/demo"
              className="rounded-md border border-border bg-surface px-6 py-3 font-medium hover:bg-surface-2"
            >
              Explore live demo
            </Link>
          </div>
          <p className="mt-4 text-xs text-muted">No credit card. No write access until you opt in.</p>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid gap-6 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="card p-6">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
                <f.icon size={18} />
              </div>
              <h3 className="mt-4 font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-border bg-surface px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight">Simple, transparent pricing</h2>
            <p className="mt-2 text-muted">Start free. Upgrade when you&apos;re finding real savings.</p>
          </div>
          <div className="mt-10 grid gap-6 sm:grid-cols-3">
            {TIERS.map((tier) => (
              <div
                key={tier.name}
                className={`card relative p-6 ${tier.highlighted ? "border-accent ring-1 ring-accent" : ""}`}
              >
                {tier.highlighted && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-accent px-3 py-0.5 text-xs font-medium text-accent-foreground">
                    Most popular
                  </span>
                )}
                <div className="text-sm text-muted">{tier.name}</div>
                <div className="mt-1 tabular-nums">
                  <span className="text-3xl font-bold">{tier.price}</span>
                  <span className="text-muted">{tier.period}</span>
                </div>
                <ul className="mt-5 space-y-2.5 text-sm">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-muted">
                      <Check size={15} className="mt-0.5 shrink-0 text-success" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border px-6 py-10 text-center text-sm text-muted">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 sm:flex-row">
          <span>© 2026 CloudWise</span>
          <Link href="/security" className="hover:text-foreground">
            Security &amp; permissions
          </Link>
        </div>
      </footer>
    </div>
  );
}
