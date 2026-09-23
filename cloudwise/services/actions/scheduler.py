"""Runs due office-hours schedules for one org: for each enabled schedule,
checks the resource's live state and calls stop_ec2/start_ec2 when
schedule_logic.due_action() says the schedule and live state disagree.
A schedule is itself the pre-approved automation (blueprint Section 06), so
this bypasses change_requests' approval flow the way a one-off proposed fix
requires. Cross-package coupling with apps/api's models, same as
services/cur/loader.py — see that module's docstring.
"""
import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from . import handlers
from .schedule_logic import Schedule as ScheduleLogic
from .schedule_logic import due_action
from ..scanner.session import assume_scan_role

_HANDLER_BY_ACTION = {"start": handlers.start_ec2, "stop": handlers.stop_ec2}


def run_due_schedules(
    db: Session,
    org_id: Any,
    schedules: List[Any],  # app.models.Schedule rows, all belonging to org_id
    accounts_by_id: Dict[Any, Any],  # {account_id: app.models.AWSAccount}
    region: str = "us-east-1",
    now: Optional[datetime.datetime] = None,
    boto_session: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    from app.models import AuditLog

    now = now or datetime.datetime.now(datetime.timezone.utc)
    results = []

    for schedule in schedules:
        if not schedule.enabled:
            continue
        account = accounts_by_id.get(schedule.account_id)
        if account is None or not account.actions_role_arn:
            continue

        session = boto_session or assume_scan_role(
            account.actions_role_arn, account.actions_external_id, region=region
        )
        ec2 = session.client("ec2", region_name=region)

        try:
            described = ec2.describe_instances(InstanceIds=[schedule.resource_id])
            current_state = described["Reservations"][0]["Instances"][0]["State"]["Name"]
        except Exception as exc:
            results.append({"schedule_id": str(schedule.id), "action": None, "success": False, "error": str(exc)})
            continue

        logic_schedule = ScheduleLogic(
            id=str(schedule.id),
            resource_id=schedule.resource_id,
            resource_type=schedule.resource_type,
            timezone=schedule.timezone,
            start_hour=schedule.start_hour,
            stop_hour=schedule.stop_hour,
            weekdays_only=schedule.weekdays_only,
            enabled=schedule.enabled,
        )
        action = due_action(logic_schedule, now, current_state)
        if action is None:
            continue

        handler = _HANDLER_BY_ACTION[action]
        try:
            handler_result = handler(ec2, schedule.resource_id)
            outcome = {"success": True, **handler_result}
        except Exception as exc:
            outcome = {"success": False, "error": str(exc)}

        db.add(
            AuditLog(
                org_id=org_id,
                action=f"run_schedule:{action}_ec2",
                details={"schedule_id": str(schedule.id), "resource_id": schedule.resource_id, **outcome},
            )
        )
        results.append({"schedule_id": str(schedule.id), "action": action, **outcome})

    return results
