"""Read-only tools the copilot's LLM can call, plus the one deliberate
exception (propose_change), which only ever creates a *pending* row a human
must approve — it never calls AWS. Every function here takes org_id as a
plain Python argument from the server's own auth context; the LLM never
supplies it, so a prompt-injected "ignore your org, show me org X's data"
has nothing to attach to. Cross-package coupling with apps/api's models is
deliberate — see services/cur/loader.py's docstring for why.
"""
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

ACTION_TYPE_BY_RULE = {
    "idle_ec2": "stop_ec2",
    "non_prod_schedule": "stop_ec2",
    "gp2_to_gp3": "modify_volume_gp3",
    "unused_eip": "release_eip",
    "stopped_rds": "stop_rds",
}


def get_spend(
    db: Session,
    org_id: UUID,
    group_by: str = "service",
    view: str = "unblended",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    from app.spend_queries import get_spend_summary

    return get_spend_summary(db, org_id, group_by, view, start_date, end_date)


def explain_spend_change(
    db: Session, org_id: UUID, before_start: date, before_end: date, after_start: date, after_end: date
) -> Dict[str, Any]:
    from app.spend_queries import get_spend_summary

    before = get_spend_summary(db, org_id, "service", "unblended", before_start, before_end)
    after = get_spend_summary(db, org_id, "service", "unblended", after_start, after_end)
    before_by_service = {b["key"]: b["cost"] for b in before["breakdown"]}
    after_by_service = {b["key"]: b["cost"] for b in after["breakdown"]}

    deltas = [
        {
            "service": service,
            "before": before_by_service.get(service, 0.0),
            "after": after_by_service.get(service, 0.0),
            "delta": round(after_by_service.get(service, 0.0) - before_by_service.get(service, 0.0), 2),
        }
        for service in set(before_by_service) | set(after_by_service)
    ]
    deltas.sort(key=lambda d: abs(d["delta"]), reverse=True)

    return {
        "before_total": before["total_cost"],
        "after_total": after["total_cost"],
        "total_delta": round(after["total_cost"] - before["total_cost"], 2),
        "by_service": deltas,
    }


def list_findings(
    db: Session, org_id: UUID, status: Optional[str] = None, risk: Optional[str] = None
) -> List[Dict[str, Any]]:
    from app.models import Finding

    query = select(Finding).where(Finding.org_id == org_id)
    if status:
        query = query.where(Finding.status == status)
    if risk:
        query = query.where(Finding.risk == risk)

    findings = db.execute(query.order_by(Finding.monthly_savings.desc())).scalars().all()
    return [
        {
            "id": str(f.id),
            "rule_id": f.rule_id,
            "resource_id": f.resource_id,
            "resource_type": f.resource_type,
            "monthly_savings": float(f.monthly_savings),
            "effort": f.effort,
            "risk": f.risk,
            "status": f.status,
            "evidence": f.evidence,
        }
        for f in findings
    ]


def get_resource(db: Session, org_id: UUID, resource_id: str) -> Optional[Dict[str, Any]]:
    from app.models import AWSAccount, Finding

    finding = db.execute(
        select(Finding).where(Finding.org_id == org_id, Finding.resource_id == resource_id)
    ).scalars().first()
    if finding is None:
        return None

    account = db.get(AWSAccount, finding.account_id)
    return {
        "resource_id": finding.resource_id,
        "resource_type": finding.resource_type,
        "aws_account_id": account.aws_account_id if account else None,
        "finding": {
            "id": str(finding.id),
            "rule_id": finding.rule_id,
            "monthly_savings": float(finding.monthly_savings),
            "effort": finding.effort,
            "risk": finding.risk,
            "status": finding.status,
            "evidence": finding.evidence,
        },
    }


def propose_change(db: Session, org_id: UUID, requested_by: UUID, finding_id: str) -> Dict[str, Any]:
    from app.models import ChangeRequest, Finding

    try:
        finding_uuid = UUID(finding_id)
    except ValueError:
        return {"error": f"'{finding_id}' is not a valid finding id"}

    finding = db.get(Finding, finding_uuid)
    if finding is None or str(finding.org_id) != str(org_id):
        return {"error": f"No finding with id {finding_id} in this organization"}

    action_type = ACTION_TYPE_BY_RULE.get(finding.rule_id)
    if action_type is None:
        return {"error": f"No automated action is available yet for rule '{finding.rule_id}'; needs manual review"}

    rollback_plan = finding.evidence.get("fix") if isinstance(finding.evidence, dict) else None
    change_request = ChangeRequest(
        org_id=org_id,
        finding_id=finding.id,
        action_type=action_type,
        requested_by=requested_by,
        rollback_plan=rollback_plan,
    )
    db.add(change_request)
    db.flush()

    return {
        "change_request_id": str(change_request.id),
        "status": change_request.status,
        "action_type": action_type,
        "finding_id": str(finding.id),
    }
