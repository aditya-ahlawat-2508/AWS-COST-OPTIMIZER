"""gp2 volumes: modify to gp3 in place (low risk, no downtime, no data loss)."""
from typing import Any, Dict, Iterable, List

from .base import Finding

RULE_ID = "gp2_to_gp3"


def detect(volumes: Iterable[Dict[str, Any]]) -> List[Finding]:
    """Each volume dict: id, volume_type, size_gb, gp2_price_per_gb_month,
    gp3_price_per_gb_month.
    """
    findings = []
    for vol in volumes:
        if vol.get("volume_type") != "gp2":
            continue

        size_gb = float(vol["size_gb"])
        savings_per_gb = float(vol["gp2_price_per_gb_month"]) - float(vol["gp3_price_per_gb_month"])
        if savings_per_gb <= 0:
            continue

        findings.append(
            Finding(
                rule_id=RULE_ID,
                resource_id=vol["id"],
                resource_type="ebs_volume",
                monthly_savings=round(size_gb * savings_per_gb, 2),
                effort="low",
                risk="low",
                fix="Modify the volume type to gp3 in place (no downtime).",
                evidence={
                    "size_gb": size_gb,
                    "gp2_price_per_gb_month": vol["gp2_price_per_gb_month"],
                    "gp3_price_per_gb_month": vol["gp3_price_per_gb_month"],
                },
            )
        )
    return findings
