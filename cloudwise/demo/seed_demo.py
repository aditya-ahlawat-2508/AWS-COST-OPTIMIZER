#!/usr/bin/env python3
"""Seeds (or re-seeds, idempotently) the synthetic 'Acme Demo' org: this is
what powers the "Explore live demo" flow on the marketing site (Section 12
of the blueprint) — visitors browse this org read-only via
apps/api/app/routers/demo.py without connecting any real AWS account or
creating a Clerk session at all.

Run from cloudwise/ with both apps/api/ and cloudwise/ on PYTHONPATH:
    python demo/seed_demo.py
"""
import datetime
import pathlib
import random
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]  # cloudwise/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from sqlalchemy import select, text  # noqa: E402

from app.database import SessionLocal, org_scoped_session  # noqa: E402
from app.models import AWSAccount, ChangeRequest, Finding, Organization, SpendDaily, Subscription, User  # noqa: E402

DEMO_CLERK_ORG_ID = "demo_org_fixed"  # sentinel, never a real Clerk org id
DEMO_ORG_NAME = "Acme Demo"
LOOKBACK_DAYS = 90
NAT_ANOMALY_START_DAY = 73  # ~17 days before "today", matches the blueprint's "since 3 Oct" mockup

random.seed(20260923)  # reproducible seed data


def get_or_create_demo_org() -> uuid.UUID:
    session = SessionLocal()
    try:
        org = session.execute(select(Organization).where(Organization.clerk_org_id == DEMO_CLERK_ORG_ID)).scalar_one_or_none()
        if org is None:
            org = Organization(clerk_org_id=DEMO_CLERK_ORG_ID, name=DEMO_ORG_NAME)
            session.add(org)
            session.flush()
        org_id = org.id
        session.commit()
        return org_id
    finally:
        session.close()


def clear_demo_data(org_id: uuid.UUID) -> None:
    with org_scoped_session(org_id=str(org_id)) as session:
        session.execute(text("DELETE FROM change_requests WHERE org_id = :org_id"), {"org_id": str(org_id)})
        session.execute(text("DELETE FROM findings WHERE org_id = :org_id"), {"org_id": str(org_id)})
        session.execute(text("DELETE FROM spend_daily WHERE org_id = :org_id"), {"org_id": str(org_id)})
        session.execute(text("DELETE FROM aws_accounts WHERE org_id = :org_id"), {"org_id": str(org_id)})
        session.execute(text("DELETE FROM subscriptions WHERE org_id = :org_id"), {"org_id": str(org_id)})
        session.execute(text("DELETE FROM users WHERE org_id = :org_id"), {"org_id": str(org_id)})


ACCOUNTS = [
    {"aws_account_id": "100000000001", "label": "acme-prod"},
    {"aws_account_id": "100000000002", "label": "acme-staging"},
    {"aws_account_id": "100000000003", "label": "acme-data"},
]

SERVICES_BASE_DAILY_COST = {
    "AmazonEC2": 220.0,
    "AmazonRDS": 95.0,
    "AmazonS3": 18.0,
    "AmazonEC2-NatGateway": 12.0,
    "AWSLambda": 6.0,
}

FINDINGS = [
    ("idle_ec2", "ec2_instance", "i-0a1b2c3d4e5f60001", 212.0, "low", "medium",
     "Stop the instance, or schedule it off-hours if it's needed intermittently."),
    ("idle_ec2", "ec2_instance", "i-0a1b2c3d4e5f60002", 88.0, "low", "medium",
     "Stop the instance, or schedule it off-hours if it's needed intermittently."),
    ("unattached_ebs", "ebs_volume", "vol-0aaa111122223333a", 41.0, "low", "low", "Snapshot the volume, then delete it."),
    ("unattached_ebs", "ebs_volume", "vol-0aaa111122223333b", 27.0, "low", "low", "Snapshot the volume, then delete it."),
    ("unattached_ebs", "ebs_volume", "vol-0aaa111122223333c", 118.0, "low", "low", "Snapshot the volume, then delete it."),
    ("gp2_to_gp3", "ebs_volume", "vol-0bbb444455556666a", 31.0, "low", "low", "Modify the volume type to gp3 in place (no downtime)."),
    ("gp2_to_gp3", "ebs_volume", "vol-0bbb444455556666b", 66.0, "low", "low", "Modify the volume type to gp3 in place (no downtime)."),
    ("unused_eip", "elastic_ip", "eipalloc-0ccc7777888899990", 3.6, "low", "low", "Release the unassociated Elastic IP."),
    ("unused_eip", "elastic_ip", "eipalloc-0ccc7777888899991", 3.6, "low", "low", "Release the unassociated Elastic IP."),
    ("idle_nat_gateway", "nat_gateway", "nat-0ddd0000111122223", 32.85, "medium", "medium",
     "Delete the NAT Gateway, or add a VPC gateway endpoint for S3/DynamoDB if that's most of its traffic."),
    ("stopped_rds", "rds_instance", "acme-analytics-db-2", 45.0, "low", "medium",
     "Snapshot and delete if no longer needed — AWS auto-restarts a stopped RDS instance after 7 days."),
    ("non_prod_schedule", "ec2_instance", "i-0staging0001", 340.0, "medium", "low",
     "Schedule this instance to run office-hours only (12h, weekdays)."),
    ("non_prod_schedule", "ec2_instance", "i-0staging0002", 190.0, "medium", "low",
     "Schedule this instance to run office-hours only (12h, weekdays)."),
]

# Pad out toward the blueprint's "~30 findings" with small varied ones.
_EXTRA_TEMPLATES = [
    ("unattached_ebs", "ebs_volume", 15.0, "low", "low", "Snapshot the volume, then delete it."),
    ("gp2_to_gp3", "ebs_volume", 22.0, "low", "low", "Modify the volume type to gp3 in place (no downtime)."),
    ("idle_ec2", "ec2_instance", 55.0, "low", "medium", "Stop the instance, or schedule it off-hours."),
]
for i in range(17):
    rule_id, resource_type, base_cost, effort, risk, fix = _EXTRA_TEMPLATES[i % len(_EXTRA_TEMPLATES)]
    resource_id = f"{'vol' if 'ebs' in resource_type else 'i'}-0extra{i:04d}"
    FINDINGS.append((rule_id, resource_type, resource_id, round(base_cost * random.uniform(0.5, 1.8), 2), effort, risk, fix))

# A handful of "already fixed" findings with a completed, executed change
# request — this is what makes the Overview KPI's "Realized $X/mo, N fixes".
REALIZED_FINDING_INDICES = [0, 3, 5, 7, 9, 11, 13, 15, 17]


def seed() -> None:
    org_id = get_or_create_demo_org()
    clear_demo_data(org_id)

    with org_scoped_session(org_id=str(org_id)) as session:
        session.add(Subscription(org_id=org_id, tier="growth", status="active"))

        demo_user = User(org_id=org_id, clerk_user_id="demo_user_readonly", email="demo@cloudwise.invalid", role="viewer")
        session.add(demo_user)
        session.flush()

        account_rows = []
        for acct in ACCOUNTS:
            row = AWSAccount(
                org_id=org_id,
                aws_account_id=acct["aws_account_id"],
                role_arn=f"arn:aws:iam::{acct['aws_account_id']}:role/CloudWiseReadOnly-DEMO",
                external_id="demo-external-id",
                label=acct["label"],
                status="connected",
                last_scanned_at=datetime.datetime.utcnow(),
            )
            session.add(row)
            session.flush()
            account_rows.append(row)

        # --- 90 days of spend, split across accounts/services, with a NAT anomaly ---
        today = datetime.date.today()
        for day_offset in range(LOOKBACK_DAYS, -1, -1):
            usage_date = today - datetime.timedelta(days=day_offset)
            for account in account_rows:
                for service, base_cost in SERVICES_BASE_DAILY_COST.items():
                    daily_cost = base_cost * random.uniform(0.85, 1.15) / len(account_rows)
                    if service == "AmazonEC2-NatGateway" and day_offset <= NAT_ANOMALY_START_DAY:
                        daily_cost += 410.0 / 30 / len(account_rows)  # spread ~$410/mo bump across accounts
                    session.add(
                        SpendDaily(
                            org_id=org_id,
                            account_id=account.id,
                            usage_date=usage_date,
                            service=service,
                            unblended_cost=round(daily_cost, 4),
                            amortized_cost=round(daily_cost * 0.92, 4),  # demo Savings-Plan-ish discount
                            currency="USD",
                        )
                    )

        # --- findings ---
        finding_rows = []
        for idx, (rule_id, resource_type, resource_id, savings, effort, risk, fix) in enumerate(FINDINGS):
            account = account_rows[idx % len(account_rows)]
            status = "dismissed" if idx == 2 else "open"
            row = Finding(
                org_id=org_id,
                account_id=account.id,
                rule_id=rule_id,
                resource_id=resource_id,
                resource_type=resource_type,
                evidence={"fix": fix, "demo": True},
                monthly_savings=savings,
                effort=effort,
                risk=risk,
                status=status,
            )
            session.add(row)
            session.flush()
            finding_rows.append(row)

        # --- a handful of already-executed change requests ("realized savings") ---
        for idx in REALIZED_FINDING_INDICES:
            finding = finding_rows[idx]
            finding.status = "done"
            session.add(
                ChangeRequest(
                    org_id=org_id,
                    finding_id=finding.id,
                    action_type="stop_ec2" if finding.resource_type == "ec2_instance" else "modify_volume_gp3",
                    requested_by=demo_user.id,
                    approved_by=demo_user.id,
                    status="executed",
                    execution_result={"success": True, "demo": True},
                    executed_at=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 20)),
                )
            )

    total_open_savings = sum(f[3] for i, f in enumerate(FINDINGS) if i != 2)
    realized_savings = sum(FINDINGS[i][3] for i in REALIZED_FINDING_INDICES)
    print(f"Seeded demo org {org_id} ({DEMO_ORG_NAME})")
    print(f"  accounts: {len(ACCOUNTS)}, findings: {len(FINDINGS)}, spend rows: ~{LOOKBACK_DAYS * len(ACCOUNTS) * len(SERVICES_BASE_DAILY_COST)}")
    print(f"  open savings found: ~${total_open_savings:,.0f}/mo, realized: ~${realized_savings:,.0f}/mo across {len(REALIZED_FINDING_INDICES)} fixes")


if __name__ == "__main__":
    seed()
