import Link from "next/link";

export default function SecurityPage() {
  return (
    <div className="flex-1">
      <header className="border-b border-border px-6 py-4">
        <Link href="/" className="text-lg font-semibold">
          CloudWise
        </Link>
      </header>

      <div className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="text-3xl font-bold">Security &amp; permissions</h1>
        <p className="mt-4 text-muted">
          This describes what CloudWise actually does, matching the IAM policies and database
          schema in the open parts of our stack — not aspirational claims.
        </p>

        <h2 className="mt-10 text-xl font-semibold">No long-lived keys, ever</h2>
        <p className="mt-2 text-muted">
          You never paste an access key into CloudWise. Instead, you deploy a CloudFormation
          template that creates an IAM role trusting only CloudWise&apos;s platform account, gated by a
          unique per-tenant ExternalId we generate for you. We assume that role via STS for a
          15-minute session to scan your account; credentials live only in memory for that session
          and are never stored.
        </p>

        <h2 className="mt-10 text-xl font-semibold">Read-only by default</h2>
        <p className="mt-2 text-muted">
          The default role we ask you to deploy grants only Describe/List/Get-style metadata
          permissions — things like <code>ec2:DescribeInstances</code> and{" "}
          <code>cloudwatch:GetMetricStatistics</code>. It explicitly excludes data-plane reads like{" "}
          <code>s3:GetObject</code> or <code>secretsmanager:GetSecretValue</code>, and includes no
          write or delete permissions of any kind.
        </p>

        <h2 className="mt-10 text-xl font-semibold">Automation is opt-in and scoped</h2>
        <p className="mt-2 text-muted">
          If you choose to enable automation, you deploy a second, separate role limited to four
          reversible actions — stopping an EC2 instance, converting a gp2 volume to gp3 in place,
          releasing an unassociated Elastic IP, and stopping an RDS instance — and only on resources
          you&apos;ve tagged <code>cloudwise:managed=true</code>. No delete or terminate permission is
          ever granted. Every action re-checks the resource&apos;s live state immediately before running,
          and every outcome (success or failure) is written to an immutable audit log.
        </p>

        <h2 className="mt-10 text-xl font-semibold">Tenant isolation at the database layer</h2>
        <p className="mt-2 text-muted">
          Every table that holds customer data has Postgres Row-Level Security policies with{" "}
          <code>FORCE ROW LEVEL SECURITY</code> enabled, and the application connects as a
          deliberately unprivileged database role — not a superuser — so isolation holds even if an
          application query ever forgot a <code>WHERE org_id = …</code> clause.
        </p>

        <h2 className="mt-10 text-xl font-semibold">The AI copilot never touches AWS</h2>
        <p className="mt-2 text-muted">
          The copilot&apos;s tools only query CloudWise&apos;s own database, scoped to your organization by
          the server — never by anything the model outputs. It can propose a change for a human to
          approve; it cannot execute one. Every dollar figure and resource ID in its answers is
          checked against the tool results from that conversation before being shown to you.
        </p>
      </div>
    </div>
  );
}
