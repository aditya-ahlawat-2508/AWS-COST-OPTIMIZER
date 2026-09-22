"""Unused Elastic IP / public IPv4: unassociated addresses are billed hourly."""
from typing import Any, Dict, Iterable, List

from .base import HOURS_PER_MONTH, Finding

RULE_ID = "unused_eip"


def detect(addresses: Iterable[Dict[str, Any]]) -> List[Finding]:
    """Each address dict: allocation_id, associated (bool), hourly_rate."""
    findings = []
    for addr in addresses:
        if addr.get("associated", False):
            continue

        hourly_rate = float(addr["hourly_rate"])
        findings.append(
            Finding(
                rule_id=RULE_ID,
                resource_id=addr["allocation_id"],
                resource_type="elastic_ip",
                monthly_savings=round(hourly_rate * HOURS_PER_MONTH, 2),
                effort="low",
                risk="low",
                fix="Release the unassociated Elastic IP.",
                evidence={"hourly_rate": hourly_rate},
            )
        )
    return findings
