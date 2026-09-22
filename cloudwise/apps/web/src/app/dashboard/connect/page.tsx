"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

// Placeholder — a real deployment generates this per-tenant, pointed at
// infra/onboarding/readonly-role.yaml with ExternalId pre-filled as a
// CloudFormation parameter default.
const CFN_QUICK_CREATE_URL =
  "https://console.aws.amazon.com/cloudformation/home#/stacks/quickcreate?templateURL=REPLACE_WITH_S3_URL&stackName=CloudWiseReadOnly";

export default function ConnectAwsPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [awsAccountId, setAwsAccountId] = useState("");
  const [roleArn, setRoleArn] = useState("");
  const [externalId] = useState(() => crypto.randomUUID());
  const [label, setLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function connect() {
    setError(null);
    setSubmitting(true);
    try {
      const token = await getToken();
      if (!token) throw new Error("Not signed in");
      const account = await api.createAccount(token, {
        aws_account_id: awsAccountId,
        role_arn: roleArn,
        external_id: externalId,
        label: label || undefined,
      });
      setStep(3);
      const result = await api.scanAccount(token, account.id);
      setScanResult(`Found ${result.findings_written} findings across ${result.resources_scanned} resources.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong connecting your account.");
      setStep(2);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-xl font-semibold">Connect AWS</h1>

      <ol className="flex gap-4 text-sm text-muted">
        <li className={step >= 1 ? "text-accent" : ""}>1. Deploy the role</li>
        <li className={step >= 2 ? "text-accent" : ""}>2. Confirm</li>
        <li className={step >= 3 ? "text-accent" : ""}>3. First scan</li>
      </ol>

      {step === 1 && (
        <div className="space-y-4 rounded-lg border border-border bg-surface p-6">
          <p className="text-sm text-muted">
            This deploys a read-only IAM role (see{" "}
            <a href="/security" className="text-accent hover:underline">
              what it grants
            </a>
            ) trusting only CloudWise, gated by the ExternalId below.
          </p>
          <div>
            <label className="text-xs text-muted">Your unique ExternalId (generated)</label>
            <input readOnly value={externalId} className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs" />
          </div>
          <a
            href={`${CFN_QUICK_CREATE_URL}&param_ExternalId=${externalId}`}
            target="_blank"
            rel="noreferrer"
            className="inline-block rounded-md bg-accent px-4 py-2 text-sm text-accent-foreground"
          >
            Open CloudFormation quick-create
          </a>
          <button
            onClick={() => setStep(2)}
            className="block text-sm text-accent hover:underline"
          >
            I&apos;ve deployed it — continue
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4 rounded-lg border border-border bg-surface p-6">
          <div>
            <label className="text-xs text-muted">AWS Account ID (12 digits)</label>
            <input
              value={awsAccountId}
              onChange={(e) => setAwsAccountId(e.target.value)}
              placeholder="111111111111"
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted">Role ARN (from the CloudFormation stack&apos;s Outputs)</label>
            <input
              value={roleArn}
              onChange={(e) => setRoleArn(e.target.value)}
              placeholder="arn:aws:iam::111111111111:role/CloudWiseReadOnlyRole"
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted">Label (optional)</label>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="acme-prod"
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>
          {error && <div className="text-sm text-danger">{error}</div>}
          <button
            onClick={connect}
            disabled={submitting || !awsAccountId || !roleArn}
            className="rounded-md bg-accent px-4 py-2 text-sm text-accent-foreground disabled:opacity-50"
          >
            {submitting ? "Connecting…" : "Connect and scan"}
          </button>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4 rounded-lg border border-border bg-surface p-6 text-center">
          <div className="text-2xl">✓</div>
          <p className="text-sm">{scanResult ?? "Scanning…"}</p>
          <button
            onClick={() => router.push("/dashboard")}
            className="rounded-md bg-accent px-4 py-2 text-sm text-accent-foreground"
          >
            Go to dashboard
          </button>
        </div>
      )}
    </div>
  );
}
