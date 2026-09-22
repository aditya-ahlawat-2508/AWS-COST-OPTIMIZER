"""Idle NAT Gateway: low BytesOut over the lookback window -> delete or
consolidate (e.g. behind a VPC gateway endpoint for S3/DynamoDB traffic).

Only the NAT Gateway's fixed hourly charge is counted here — data processing
charges come from CUR line items (services/pricing), not this rule, since
they aren't observable from CloudWatch alone.
"""
from typing import Any, Dict, Iterable, List

from .base import HOURS_PER_MONTH, Finding

RULE_ID = "idle_nat_gateway"
DEFAULT_BYTES_OUT_THRESHOLD_PER_DAY = 10 * 1024 * 1024  # 10 MB/day


def detect(
    nat_gateways: Iterable[Dict[str, Any]],
    bytes_out_threshold_per_day: float = DEFAULT_BYTES_OUT_THRESHOLD_PER_DAY,
) -> List[Finding]:
    """Each gateway dict: id, state, hourly_rate, avg_bytes_out_per_day."""
    findings = []
    for nat in nat_gateways:
        if nat.get("state") != "available":
            continue
        if nat.get("avg_bytes_out_per_day", float("inf")) >= bytes_out_threshold_per_day:
            continue

        hourly_rate = float(nat["hourly_rate"])
        findings.append(
            Finding(
                rule_id=RULE_ID,
                resource_id=nat["id"],
                resource_type="nat_gateway",
                monthly_savings=round(hourly_rate * HOURS_PER_MONTH, 2),
                effort="medium",
                risk="medium",
                fix="Delete the NAT Gateway, or add a VPC gateway endpoint for S3/DynamoDB if that's most of its traffic.",
                evidence={
                    "avg_bytes_out_per_day": nat.get("avg_bytes_out_per_day"),
                    "hourly_rate": hourly_rate,
                },
            )
        )
    return findings
