"use client";

import { use, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { api, type Finding, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/utils";
import { EffortBadge, RiskBadge, StatusBadge } from "@/components/badges";

export default function FindingDetailPage({ params }: PageProps<"/dashboard/findings/[id]">) {
  const { id } = use(params);
  const { getToken } = useAuth();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [proposeResult, setProposeResult] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const token = await getToken();
      if (!token) return;
      // No single-finding GET route yet — the list is small enough per org
      // that filtering client-side is simpler than adding one right now.
      const all = await api.listFindings(token);
      const match = all.find((f) => f.id === id);
      if (!match) setNotFound(true);
      else setFinding(match);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function proposeFix() {
    if (!finding) return;
    setProposing(true);
    setProposeResult(null);
    try {
      const token = await getToken();
      if (!token) return;
      const response = await api.copilotChat(token, `Propose a fix for finding ${finding.id}.`);
      setProposeResult(response.text);
    } catch (err) {
      setProposeResult(
        err instanceof ApiError && err.status === 503
          ? "The copilot isn't configured yet — an admin can approve this manually instead."
          : "Couldn't create a change request."
      );
    } finally {
      setProposing(false);
    }
  }

  if (notFound) {
    return <div className="text-sm text-muted">Finding not found.</div>;
  }
  if (!finding) {
    return <div className="text-sm text-muted">Loading…</div>;
  }

  const fix = typeof finding.evidence?.fix === "string" ? finding.evidence.fix : null;

  return (
    <div className="max-w-2xl space-y-6">
      <Link href="/dashboard/findings" className="text-sm text-accent hover:underline">
        ← Back to recommendations
      </Link>

      <div>
        <h1 className="font-mono text-lg">{finding.resource_id}</h1>
        <p className="text-sm capitalize text-muted">{finding.rule_id.replace(/_/g, " ")} · {finding.resource_type}</p>
      </div>

      <div className="flex gap-2">
        <EffortBadge effort={finding.effort} />
        <RiskBadge risk={finding.risk} />
        <StatusBadge status={finding.status} />
      </div>

      <div className="rounded-lg border border-border bg-surface p-4">
        <div className="text-sm text-muted">Monthly savings</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">{formatMoney(finding.monthly_savings)}</div>
        <p className="mt-1 text-xs text-muted">
          Computed in services/rules from the resource&apos;s own metered usage — never estimated by an LLM.
        </p>
      </div>

      {fix && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-sm font-medium">Suggested fix</div>
          <p className="mt-1 text-sm text-muted">{fix}</p>
        </div>
      )}

      <div className="rounded-lg border border-border bg-surface p-4">
        <div className="text-sm font-medium">Evidence</div>
        <pre className="mt-2 overflow-x-auto rounded-md bg-background p-3 text-xs text-muted">
          {JSON.stringify(finding.evidence, null, 2)}
        </pre>
      </div>

      {finding.status === "open" && (
        <div className="space-y-2">
          <button
            onClick={proposeFix}
            disabled={proposing}
            className="rounded-md bg-accent px-4 py-2 text-sm text-accent-foreground disabled:opacity-50"
          >
            {proposing ? "Asking the copilot…" : "Create change request"}
          </button>
          {proposeResult && <p className="text-sm text-muted">{proposeResult}</p>}
        </div>
      )}
    </div>
  );
}
