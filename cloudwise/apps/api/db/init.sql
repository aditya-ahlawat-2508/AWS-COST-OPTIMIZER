-- CloudWise schema with Postgres Row-Level Security as the tenant-isolation
-- backstop: even if an application query forgets a WHERE org_id = ... clause,
-- the database itself refuses to return or touch another org's rows.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE organizations (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Clerk Organization id (e.g. "org_2abc..."). Clerk is the system of
    -- record for identity; this column is how we map its org to our RLS-scoped
    -- internal UUID. Auto-provisioned on first authenticated request from a
    -- member of a Clerk org CloudWise hasn't seen before — see app/provisioning.py.
    clerk_org_id   TEXT UNIQUE,
    name           TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    -- Clerk user id (e.g. "user_2abc..."). No password_hash here: Clerk owns
    -- credentials entirely, CloudWise never sees or stores a password.
    clerk_user_id   TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    role            TEXT NOT NULL DEFAULT 'owner' CHECK (role IN ('owner', 'admin', 'approver', 'viewer')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE aws_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    aws_account_id  TEXT NOT NULL,
    role_arn        TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    -- Opt-in only (infra/onboarding/actions-role.yaml). NULL means this
    -- account has not enabled automation; services/actions refuses to run
    -- anything against it until both are set.
    actions_role_arn    TEXT,
    actions_external_id TEXT,
    label           TEXT,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'connected', 'error')),
    last_scanned_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, aws_account_id)
);

CREATE TABLE findings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id        UUID NOT NULL REFERENCES aws_accounts(id) ON DELETE CASCADE,
    rule_id           TEXT NOT NULL,
    resource_id       TEXT NOT NULL,
    resource_type     TEXT NOT NULL,
    evidence          JSONB NOT NULL DEFAULT '{}'::jsonb,
    monthly_savings   NUMERIC(12, 2) NOT NULL,
    currency          TEXT NOT NULL DEFAULT 'USD',
    effort            TEXT NOT NULL CHECK (effort IN ('low', 'medium', 'high')),
    risk              TEXT NOT NULL CHECK (risk IN ('low', 'medium', 'high')),
    status            TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'approved', 'done', 'dismissed')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Lets re-scans upsert (update evidence/$/risk) instead of duplicating,
    -- while leaving a user's approve/dismiss decision on status untouched.
    UNIQUE (org_id, account_id, rule_id, resource_id)
);

CREATE TABLE change_requests (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    finding_id        UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    action_type       TEXT NOT NULL CHECK (action_type IN ('stop_ec2', 'modify_volume_gp3', 'release_eip', 'stop_rds')),
    requested_by      UUID NOT NULL REFERENCES users(id),
    approved_by       UUID REFERENCES users(id),
    status            TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'executed', 'failed')),
    rollback_plan     TEXT,
    pre_check_snapshot JSONB,
    execution_result  JSONB,
    executed_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per org. No row at all means "free tier" — see
-- app/billing.py:get_entitlement, which treats a missing subscription the
-- same as an explicit free-tier one rather than erroring.
CREATE TABLE subscriptions (
    org_id                   UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    tier                     TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'growth')),
    status                   TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'trialing', 'past_due', 'canceled')),
    -- Which of the two providers billed this org last. USD customers use
    -- Stripe, INR customers use Razorpay (blueprint Section 03) — an org
    -- only ever has one active provider at a time, not both.
    provider                 TEXT NOT NULL DEFAULT 'stripe' CHECK (provider IN ('stripe', 'razorpay')),
    stripe_customer_id       TEXT UNIQUE,
    stripe_subscription_id   TEXT UNIQUE,
    razorpay_subscription_id TEXT UNIQUE,
    current_period_end       TIMESTAMPTZ,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Normalized daily spend, aggregated from CUR/Data Exports by
-- services/cur/loader.py. One row per (org, account, day, service).
CREATE TABLE spend_daily (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id       UUID NOT NULL REFERENCES aws_accounts(id) ON DELETE CASCADE,
    usage_date       DATE NOT NULL,
    service          TEXT NOT NULL,
    unblended_cost   NUMERIC(14, 4) NOT NULL,
    amortized_cost   NUMERIC(14, 4) NOT NULL,
    currency         TEXT NOT NULL DEFAULT 'USD',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, account_id, usage_date, service)
);

-- Office-hours automation (blueprint Section 06). Evaluated by
-- services/actions/scheduler.py against services/actions/schedule_logic.py's
-- pure due_action() — a schedule is itself the pre-approved automation, so
-- running it doesn't go through change_requests' approval flow the way a
-- one-off proposed fix does.
CREATE TABLE schedules (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id     UUID NOT NULL REFERENCES aws_accounts(id) ON DELETE CASCADE,
    resource_id    TEXT NOT NULL,
    resource_type  TEXT NOT NULL DEFAULT 'ec2_instance' CHECK (resource_type IN ('ec2_instance')),
    timezone       TEXT NOT NULL DEFAULT 'UTC',
    start_hour     INTEGER NOT NULL CHECK (start_hour >= 0 AND start_hour < 24),
    stop_hour      INTEGER NOT NULL CHECK (stop_hour > 0 AND stop_hour <= 24),
    weekdays_only  BOOLEAN NOT NULL DEFAULT true,
    enabled        BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (start_hour < stop_hour)
);

-- Named spend limits. Scoped to one account, or org-wide when account_id is
-- NULL. Not scoped by team/tag — that needs tag data in spend_daily, which
-- CUR ingestion doesn't capture yet (see services/cur/parser.py).
CREATE TABLE budgets (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id        UUID REFERENCES aws_accounts(id) ON DELETE CASCADE,
    name              TEXT NOT NULL,
    monthly_limit_usd NUMERIC(12, 2) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id    UUID REFERENCES users(id),
    action      TEXT NOT NULL,
    details     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Row-Level Security: every org-scoped table is readable/writable only when
-- app.current_org_id (set per-request by the API, see app/database.py) matches
-- the row's org_id. FORCE ROW LEVEL SECURITY means even the table owner is
-- bound by this — there is no privileged connection that bypasses it.
ALTER TABLE users           ENABLE ROW LEVEL SECURITY;
ALTER TABLE users           FORCE ROW LEVEL SECURITY;
ALTER TABLE aws_accounts    ENABLE ROW LEVEL SECURITY;
ALTER TABLE aws_accounts    FORCE ROW LEVEL SECURITY;
ALTER TABLE findings        ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings        FORCE ROW LEVEL SECURITY;
ALTER TABLE change_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE change_requests FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_log       ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log       FORCE ROW LEVEL SECURITY;
ALTER TABLE spend_daily     ENABLE ROW LEVEL SECURITY;
ALTER TABLE spend_daily     FORCE ROW LEVEL SECURITY;
ALTER TABLE subscriptions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions   FORCE ROW LEVEL SECURITY;
ALTER TABLE budgets         ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets         FORCE ROW LEVEL SECURITY;
ALTER TABLE schedules       ENABLE ROW LEVEL SECURITY;
ALTER TABLE schedules       FORCE ROW LEVEL SECURITY;

CREATE POLICY org_isolation_users ON users
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_aws_accounts ON aws_accounts
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_findings ON findings
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_change_requests ON change_requests
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_audit_log ON audit_log
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_spend_daily ON spend_daily
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_subscriptions ON subscriptions
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_budgets ON budgets
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

CREATE POLICY org_isolation_schedules ON schedules
    USING (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid)
    WITH CHECK (org_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid);

-- Stripe webhooks reference a stripe_customer_id, not an org_id, so
-- resolving a subscription-lifecycle event has the same bootstrap problem
-- as login: look it up before the org context is known. Only app/billing.py
-- sets this flag, and only for that one lookup.
CREATE POLICY allow_billing_lookup ON subscriptions
    FOR SELECT
    USING (current_setting('app.allow_billing_lookup', true) = 'true');

-- The one deliberate bypass: provisioning has to look a user up by
-- clerk_user_id before it knows their org_id (that's the whole point of
-- Clerk-token-to-org resolution on first sight of a user). This policy
-- allows that one SELECT with no org context, but only from
-- app/provisioning.py, and never for any other table.
CREATE POLICY allow_provisioning_lookup ON users
    FOR SELECT
    USING (current_setting('app.allow_provisioning_lookup', true) = 'true');

-- FORCE ROW LEVEL SECURITY only binds the table owner — Postgres superusers
-- (and anyone with BYPASSRLS) ignore RLS entirely no matter what. So the app
-- must never connect as the migration/admin role that ran this script; it
-- connects as this separate, deliberately unprivileged role instead.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cloudwise_app') THEN
        CREATE ROLE cloudwise_app LOGIN PASSWORD 'cloudwise_app_dev_password' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO cloudwise_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cloudwise_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cloudwise_app;
