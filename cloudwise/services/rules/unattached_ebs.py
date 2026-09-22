"""Unattached EBS volume: state 'available' for N days -> snapshot then delete."""
from typing import Any, Dict, Iterable, List

from .base import Finding

RULE_ID = "unattached_ebs"
DEFAULT_MIN_DAYS_AVAILABLE = 7


def detect(volumes: Iterable[Dict[str, Any]], min_days_available: int = DEFAULT_MIN_DAYS_AVAILABLE) -> List[Finding]:
    """Each volume dict: id, state, size_gb, volume_type, price_per_gb_month,
    days_available (how long it's been in the 'available' / unattached state).
    """
    findings = []
    for vol in volumes:
        if vol.get("state") != "available":
            continue
        if vol.get("days_available", 0) < min_days_available:
            continue

        monthly_savings = float(vol["size_gb"]) * float(vol["price_per_gb_month"])
        findings.append(
            Finding(
                rule_id=RULE_ID,
                resource_id=vol["id"],
                resource_type="ebs_volume",
                monthly_savings=round(monthly_savings, 2),
                effort="low",
                risk="low",
                fix="Snapshot the volume, then delete it.",
                evidence={
                    "size_gb": vol["size_gb"],
                    "volume_type": vol.get("volume_type"),
                    "days_available": vol.get("days_available"),
                    "price_per_gb_month": vol["price_per_gb_month"],
                },
            )
        )
    return findings
