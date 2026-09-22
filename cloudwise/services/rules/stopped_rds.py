"""Stopped RDS: AWS auto-restarts a stopped instance after 7 days, so a
forgotten one silently starts costing compute again. Storage is billed the
whole time it sits stopped either way.
"""
from typing import Any, Dict, Iterable, List

from .base import Finding

RULE_ID = "stopped_rds"
DEFAULT_MIN_DAYS_STOPPED = 5
AWS_AUTO_RESTART_DAYS = 7


def detect(instances: Iterable[Dict[str, Any]], min_days_stopped: int = DEFAULT_MIN_DAYS_STOPPED) -> List[Finding]:
    """Each instance dict: id, state, days_stopped, storage_monthly_cost."""
    findings = []
    for db in instances:
        if db.get("state") != "stopped":
            continue
        if db.get("days_stopped", 0) < min_days_stopped:
            continue

        storage_cost = float(db["storage_monthly_cost"])
        findings.append(
            Finding(
                rule_id=RULE_ID,
                resource_id=db["id"],
                resource_type="rds_instance",
                monthly_savings=round(storage_cost, 2),
                effort="low",
                risk="medium",
                fix=(
                    "Snapshot and delete if no longer needed — AWS auto-restarts a stopped "
                    f"RDS instance after {AWS_AUTO_RESTART_DAYS} days, silently resuming compute charges."
                ),
                evidence={
                    "days_stopped": db["days_stopped"],
                    "auto_restart_after_days": AWS_AUTO_RESTART_DAYS,
                    "storage_monthly_cost": storage_cost,
                },
            )
        )
    return findings
