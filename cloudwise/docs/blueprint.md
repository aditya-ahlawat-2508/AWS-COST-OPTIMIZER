# CloudWise — SaaS Blueprint (condensed)

Source: `CloudWise_AWS_Cost_Optimizer_SaaS_Blueprint.pdf`, prepared September 2026.
Full detail lives in the PDF; this file is the working reference for whoever
(human or Claude Code) is building against it session to session.

## Product thesis
Startups spending ~$500–$50k/month on AWS rarely have a FinOps person.
CloudWise is their AI FinOps engineer: connect read-only in 2 minutes, find
concrete waste with dollar amounts, explain it in plain language, and fix
approved items safely (scheduled, dry-run first, snapshot before delete,
fully audited).

## What has to change vs. the original portfolio app
| Dimension | Before | Target |
|---|---|---|
| Tenancy | Single AWS account (Lambda's own role) | Many orgs → many AWS accounts via cross-account IAM roles + ExternalId |
| Security | Public API, no auth, CORS *, can terminate/delete | Authenticated users, RBAC, read-only by default, separate opt-in action role |
| Cost data | Cost Explorer API on every page load | CUR 2.0 / Data Exports into a warehouse; Cost Explorer only for light, cached queries |
| Pricing | Hard-coded 5-instance table, $20 fallback | AWS Price List API + actual billed rates from CUR |
| Findings | LLM reads inventories and guesses | Deterministic rules engine + CloudWatch utilization → $ findings; LLM explains/prioritizes |
| UI | Streamlit | Next.js dashboard, recommendations inbox, AI copilot panel, demo org |
| Revenue | None | Tiered subscription (+ optional % of realized savings) |

## Non-negotiables (carried into `cloudwise/CLAUDE.md`)
- Never store customer AWS keys. Only role ARN + ExternalId; STS AssumeRole, short-lived, in-memory only.
- Every query is org-scoped (Postgres RLS). Add a test for each new endpoint.
- $ figures are computed in `services/rules`, never by the LLM.
- Copilot tools are read-only, scoped server-side to the caller's org. Actions only via approved change requests.
- Destructive actions: dry-run, re-check the resource still matches the finding, snapshot, audit. No exceptions.
- Tests use moto/LocalStack; never real AWS accounts in CI.

## Architecture (Section 04)
Multi-tenant, read-only-first, event-driven.
- Customer account: `CloudWiseReadOnly` role (trust: platform account + per-tenant ExternalId), optional opt-in `CloudWiseActions` role, Data Exports (CUR 2.0) → S3.
- Platform: Scheduler → Scanner workers (STS AssumeRole) → Rules engine → Postgres (RLS per org) + warehouse ← CUR ingester + Pricing service. FastAPI serves the dashboard; AI copilot has read-only tools over the DB only. Action executor runs approved change requests only, fully audited.
- No long-lived customer keys ever. Two data paths: CUR/Data Exports for accurate line-item history, direct API scans for current state + utilization.

## Detection engine (Section 05)
Deterministic rules first (reproducible, testable $), LLM ranks/explains on top.
Each rule yields: resource ID, evidence (metrics/timestamps), monthly $ estimate, effort, risk, fix. Starter set: idle EC2, over-provisioned EC2/RDS, previous-gen/x86 instance, unattached EBS volume, gp2 volumes, orphaned snapshots, unused EIP, idle/heavy-NAT gateway, idle load balancer, non-prod always-on, stopped RDS, S3 without lifecycle, CloudWatch Logs no retention, Lambda memory/arch, commitment coverage.
**Savings math rule**: every $ figure is computed in code from (hours × rate) or CUR line items, never by the LLM.

## Safe automation (Section 06)
Opt-in scoped action role, limited to specific actions/tagged resources. Every fix becomes a change request (what/why/$ impact/risk/rollback) needing approval; high-risk needs two approvals. Dry-run first, re-check right before executing. Snapshot before delete, stop before terminate, 7-day undo window for schedules. Immutable audit log. Verified savings computed from the next billing period in CUR vs. baseline.

## AI copilot (Section 07)
Tools are read-only queries (`get_spend`, `list_findings`, `get_resource`, `explain_change`, `propose_change`), scoped to the caller's org by the server, never by the prompt. AWS resource names/tags are untrusted, customer-controlled strings — keep them out of system prompts, never let tool output trigger actions. Grounding check after generation: verify every resource ID and $ figure exists in tool results.

## Execution plan (Section 11) — 12 weeks, one developer
0 hotfix → 1-2 foundation (FastAPI+Postgres+RLS+auth, onboarding, AssumeRole) → 3-5 scanners+rules+pricing+CUR → 6-7 Next.js dashboard → 8-9 copilot+anomalies+budgets+Slack → 10-11 change requests/approvals/schedules/audit/billing → 12 security page/landing/legal/launch.

## Repository layout (Section 12, target)
```
cloudwise/
  apps/web/          Next.js dashboard + marketing site
  apps/api/          FastAPI: auth, RBAC, orgs, findings, change requests
  services/scanner/  AssumeRole + per-service collectors
  services/rules/    one module per rule: detect() -> Finding, savings() -> Money
  services/pricing/  Price List API client + cache
  services/cur/      Data Exports ingestion -> Parquet/DuckDB
  services/actions/  executor with dry-run, pre-checks, rollback, audit
  services/copilot/  LangGraph agent with read-only DB tools
  infra/terraform/   platform infra
  infra/onboarding/  CloudFormation templates customers deploy
  demo/              seed script for the synthetic demo org
  tests/ evals/ docs/
```

## Decisions still open (need the founder / a design partner, not code)
- Product name / domain / trademark check ("CloudWise" is a working name only).
- Auth provider: Clerk vs Auth0 vs Supabase Auth vs a first-party JWT (this build ships a first-party JWT scaffold so Phase 1 doesn't block on a vendor account; swap later).
- Hosting for Postgres/API/web, and the platform AWS account itself.
- LLM provider/model for the copilot, and its budget.
- Billing provider (Stripe vs Razorpay) and final pricing.
- A real AWS sandbox account seeded with deliberately wasteful resources for end-to-end rule validation.
