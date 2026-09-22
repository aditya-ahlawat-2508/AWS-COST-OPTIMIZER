"""Non-prod always-on: env=dev/staging running 24x7 -> office-hours schedule.

Assumes a 12h/weekday schedule (60 of 168 hours/week) against a 24x7 baseline,
which is the blueprint's 'large share of hours saved' case.
"""
from typing import Any, Dict, Iterable, List

from .base import Finding

RULE_ID = "non_prod_schedule"
NON_PROD_ENVS = {"dev", "staging", "test", "qa"}
OFFICE_HOURS_FRACTION_OF_WEEK = 60 / 168  # 12h x 5 weekdays out of 168h/week
SAVINGS_FRACTION = 1 - OFFICE_HOURS_FRACTION_OF_WEEK


def detect(instances: Iterable[Dict[str, Any]]) -> List[Finding]:
    """Each instance dict: id, state, env_tag, monthly_cost."""
    findings = []
    for inst in instances:
        if inst.get("state") != "running":
            continue
        env = (inst.get("env_tag") or "").lower()
        if env not in NON_PROD_ENVS:
            continue

        monthly_cost = float(inst["monthly_cost"])
        findings.append(
            Finding(
                rule_id=RULE_ID,
                resource_id=inst["id"],
                resource_type="ec2_instance",
                monthly_savings=round(monthly_cost * SAVINGS_FRACTION, 2),
                effort="medium",
                risk="low",
                fix="Schedule this instance to run office-hours only (12h, weekdays).",
                evidence={"env_tag": env, "monthly_cost": monthly_cost, "assumed_schedule": "12h x 5 weekdays"},
            )
        )
    return findings
