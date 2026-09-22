"""Idle EC2: avg CPU < threshold and low network over the lookback window.

Blueprint (Section 05): 'Avg CPU < ~5% and low network over 14 days' -> stop /
schedule / downsize. This module only detects and prices; it never touches AWS.
"""
from typing import Any, Dict, Iterable, List

from .base import Finding

RULE_ID = "idle_ec2"
DEFAULT_CPU_THRESHOLD_PERCENT = 5.0
DEFAULT_NETWORK_THRESHOLD_BYTES_PER_DAY = 5 * 1024 * 1024  # 5 MB/day


def detect(
    instances: Iterable[Dict[str, Any]],
    cpu_threshold_percent: float = DEFAULT_CPU_THRESHOLD_PERCENT,
    network_threshold_bytes_per_day: float = DEFAULT_NETWORK_THRESHOLD_BYTES_PER_DAY,
) -> List[Finding]:
    """Each instance dict: id, state, instance_type, monthly_cost,
    avg_cpu_percent (over the lookback window), avg_network_bytes_per_day.
    """
    findings = []
    for inst in instances:
        if inst.get("state") != "running":
            continue
        if inst.get("avg_cpu_percent", 100) >= cpu_threshold_percent:
            continue
        if inst.get("avg_network_bytes_per_day", float("inf")) >= network_threshold_bytes_per_day:
            continue

        monthly_cost = float(inst["monthly_cost"])
        findings.append(
            Finding(
                rule_id=RULE_ID,
                resource_id=inst["id"],
                resource_type="ec2_instance",
                monthly_savings=round(monthly_cost, 2),
                effort="low",
                risk="medium",
                fix="Stop the instance, or schedule it off-hours if it's needed intermittently.",
                evidence={
                    "instance_type": inst.get("instance_type"),
                    "avg_cpu_percent": inst.get("avg_cpu_percent"),
                    "avg_network_bytes_per_day": inst.get("avg_network_bytes_per_day"),
                    "lookback_days": inst.get("lookback_days", 14),
                },
            )
        )
    return findings
