"""Executes one approved change request. Cross-package coupling with
apps/api's models is deliberate, same as services/cur/loader.py — see that
module's docstring.
"""
import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from . import handlers
from ..scanner.session import assume_scan_role

ACTION_DISPATCH = {
    "stop_ec2": ("ec2", handlers.stop_ec2),
    "modify_volume_gp3": ("ec2", handlers.modify_volume_gp3),
    "release_eip": ("ec2", handlers.release_eip),
    "stop_rds": ("rds", handlers.stop_rds),
}


def execute_change_request(
    db: Session,
    change_request: Any,  # app.models.ChangeRequest
    account: Any,  # app.models.AWSAccount
    region: str = "us-east-1",
    boto_session: Optional[Any] = None,
) -> Dict[str, Any]:
    """Must run on a session already scoped to the change request's org.
    Requires the change request to be 'approved' and the account to have
    opted into automation (actions_role_arn set, from
    infra/onboarding/actions-role.yaml) — refuses outright otherwise, before
    ever touching AWS.
    """
    from app.models import AuditLog, Finding

    if change_request.status != "approved":
        raise ValueError(f"Change request {change_request.id} is not approved (status={change_request.status})")
    if not account.actions_role_arn:
        raise ValueError(f"Account {account.id} has not connected an actions role; cannot execute automatically")

    finding = db.get(Finding, change_request.finding_id)
    service_name, handler = ACTION_DISPATCH[change_request.action_type]

    session = boto_session or assume_scan_role(
        account.actions_role_arn, account.actions_external_id, region=region
    )
    client = session.client(service_name, region_name=region)

    try:
        result = handler(client, finding.resource_id)
        change_request.status = "executed"
        change_request.execution_result = result
        change_request.pre_check_snapshot = {"state": result.get("pre_check_state")}
        change_request.executed_at = datetime.datetime.utcnow()
        outcome = {"success": True, **result}
    except Exception as exc:
        change_request.status = "failed"
        change_request.execution_result = {"error": str(exc)}
        outcome = {"success": False, "error": str(exc)}

    db.add(
        AuditLog(
            org_id=change_request.org_id,
            actor_id=change_request.approved_by,
            action=f"execute_change_request:{change_request.action_type}",
            details={
                "change_request_id": str(change_request.id),
                "resource_id": finding.resource_id,
                **outcome,
            },
        )
    )
    return outcome
