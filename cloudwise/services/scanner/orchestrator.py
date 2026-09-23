"""Ties the scanner, rules engine, and pricing service together and persists
the result. Cross-package coupling with apps/api's models, same as
services/cur/loader.py — see that module's docstring for why.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..pricing.price_list import PriceListClient
from ..rules import run_all
from .ebs import collect_ebs_volumes
from .ec2 import collect_ec2_instances
from .eip import collect_elastic_ips
from .nat_gateway import collect_nat_gateways
from .rds import collect_rds_instances
from .session import assume_scan_role

DEFAULT_SCAN_REGION = "us-east-1"


def discover_regions(session: Any) -> List[str]:
    """Every region this account has opted into, not just the one the role
    was assumed in — EC2's DescribeRegions is itself a global-ish call that
    works from any region and returns every enabled region.
    """
    ec2 = session.client("ec2", region_name=DEFAULT_SCAN_REGION)
    return [r["RegionName"] for r in ec2.describe_regions().get("Regions", [])]


def _scan_one_region(
    session: Any, region: str, pricing_client: Optional[PriceListClient]
) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "ec2_instances": collect_ec2_instances(session, region, pricing_client=pricing_client),
        "ebs_volumes": collect_ebs_volumes(session, region, pricing_client=pricing_client),
        "elastic_ips": collect_elastic_ips(session, region, pricing_client=pricing_client),
        "nat_gateways": collect_nat_gateways(session, region, pricing_client=pricing_client),
        "rds_instances": collect_rds_instances(session, region, pricing_client=pricing_client),
    }


def run_scan_for_account(
    db: Session,
    org_id: UUID,
    account: Any,  # app.models.AWSAccount; see the local import below for why
    regions: Optional[List[str]] = None,
    pricing_client: Optional[PriceListClient] = None,
    boto_session: Optional[Any] = None,
) -> Dict[str, Any]:
    """Must be called on a session already scoped to org_id. boto_session lets
    tests/a real worker inject a pre-assumed session; production code leaves
    it None and this does the AssumeRole call itself. regions=None scans
    every region the account has opted into (see discover_regions) rather
    than a single hardcoded one — a real account's resources are rarely all
    in us-east-1.
    """
    from app.models import Finding  # local import: apps/api is a separate deployable

    session = boto_session or assume_scan_role(account.role_arn, account.external_id, region=DEFAULT_SCAN_REGION)
    regions = regions if regions is not None else discover_regions(session)

    context: Dict[str, List[Dict[str, Any]]] = {
        "ec2_instances": [],
        "ebs_volumes": [],
        "elastic_ips": [],
        "nat_gateways": [],
        "rds_instances": [],
    }
    for region in regions:
        region_context = _scan_one_region(session, region, pricing_client)
        for key, items in region_context.items():
            context[key].extend(items)

    resources_scanned = sum(len(v) for v in context.values())
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

    return {"resources_scanned": resources_scanned, "findings_written": len(findings), "regions_scanned": regions}
