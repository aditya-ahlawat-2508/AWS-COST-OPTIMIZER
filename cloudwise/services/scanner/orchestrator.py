"""Ties the scanner, rules engine, and pricing service together and persists
the result. Cross-package coupling with apps/api's models, same as
services/cur/loader.py — see that module's docstring for why.

Only EC2 is wired up end-to-end so far (services/scanner/ec2.py); the other
resource types services/rules already has detectors for (EBS, EIP, NAT, RDS)
are the natural next collectors to add here, same pattern.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..pricing.price_list import PriceListClient
from ..rules import run_all
from .ec2 import collect_ec2_instances
from .session import assume_scan_role

DEFAULT_SCAN_REGION = "us-east-1"


def run_scan_for_account(
    db: Session,
    org_id: UUID,
    account: Any,  # app.models.AWSAccount; see the local import below for why
    region: str = DEFAULT_SCAN_REGION,
    pricing_client: Optional[PriceListClient] = None,
    boto_session: Optional[Any] = None,
) -> Dict[str, Any]:
    """Must be called on a session already scoped to org_id. boto_session lets
    tests/a real worker inject a pre-assumed session; production code leaves
    it None and this does the AssumeRole call itself.
    """
    from app.models import Finding  # local import: apps/api is a separate deployable

    session = boto_session or assume_scan_role(account.role_arn, account.external_id, region=region)
    ec2_instances = collect_ec2_instances(session, region, pricing_client=pricing_client)
    context = {"ec2_instances": ec2_instances}
    findings = run_all(context)

    for finding in findings:
        evidence = dict(finding.evidence)
        evidence["fix"] = finding.fix
        stmt = pg_insert(Finding).values(
            org_id=org_id,
            account_id=account.id,
            rule_id=finding.rule_id,
            resource_id=finding.resource_id,
            resource_type=finding.resource_type,
            evidence=evidence,
            monthly_savings=finding.monthly_savings,
            currency=finding.currency,
            effort=finding.effort,
            risk=finding.risk,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["org_id", "account_id", "rule_id", "resource_id"],
            set_={
                "evidence": stmt.excluded.evidence,
                "monthly_savings": stmt.excluded.monthly_savings,
                "effort": stmt.excluded.effort,
                "risk": stmt.excluded.risk,
                # status is deliberately left alone: a user's approve/dismiss
                # decision on a finding must survive the next re-scan.
            },
        )
        db.execute(stmt)

    return {"resources_scanned": len(ec2_instances), "findings_written": len(findings)}
