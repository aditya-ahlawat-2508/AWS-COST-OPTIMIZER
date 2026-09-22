// MOCK DATA — these screens don't have a backend endpoint yet. Replace with
// real API calls (see lib/api.ts) once the corresponding route exists:
//   - Anomalies: needs an anomaly-detection service (blueprint Section 04's
//     "Anomaly detector" box) — not built.
//   - Audit log: the audit_log table exists (apps/api/app/models.py) and
//     services/actions writes to it, but there's no GET /audit-log route yet.
//   - Budgets: no budgets table/endpoint exists yet.

export const MOCK_ANOMALIES = [
  {
    id: "anomaly-1",
    detected_at: "2026-09-06",
    service: "NAT Gateway",
    delta: 410,
    summary:
      "NAT Gateway data processing rose $410 after Sept 3, when svc-ingest began pulling images from ECR through NAT.",
    suggestion: "Add a VPC endpoint for ECR/S3 — estimated $360/mo saved.",
  },
  {
    id: "anomaly-2",
    detected_at: "2026-08-22",
    service: "Amazon RDS",
    delta: 145,
    summary: "A read replica was added to acme-analytics-db and left running after a load test.",
    suggestion: "Confirm the replica is still needed; delete if not.",
  },
];

export const MOCK_BUDGETS = [
  { team: "Platform", monthly_budget: 8000, spent_so_far: 6420 },
  { team: "Data", monthly_budget: 4000, spent_so_far: 4310 },
  { team: "Growth", monthly_budget: 2000, spent_so_far: 980 },
];

export const MOCK_AUDIT_LOG = [
  {
    id: "audit-1",
    actor: "owner@acmecorp.io",
    action: "execute_change_request:modify_volume_gp3",
    timestamp: "2026-09-18T14:02:00Z",
    details: "vol-0aaa111122223333a: gp2 -> gp3, success",
  },
  {
    id: "audit-2",
    actor: "owner@acmecorp.io",
    action: "approve_change_request",
    timestamp: "2026-09-18T13:58:00Z",
    details: "Approved stop_ec2 for i-0a1b2c3d4e5f60001",
  },
  {
    id: "audit-3",
    actor: "system",
    action: "scan_completed",
    timestamp: "2026-09-17T02:00:00Z",
    details: "acme-prod: 3 new findings, $145/mo",
  },
];
