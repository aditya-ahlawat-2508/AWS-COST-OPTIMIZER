"""Elastic IP collector, shaped for services.rules.unused_eip."""
from typing import Any, Dict, List, Optional

from ..pricing.price_list import PriceListClient


def collect_elastic_ips(
    session, region: str, pricing_client: Optional[PriceListClient] = None
) -> List[Dict[str, Any]]:
    ec2 = session.client("ec2", region_name=region)
    pricing_client = pricing_client or PriceListClient()

    try:
        hourly_rate = pricing_client.get_eip_hourly_rate(region)
    except Exception:
        hourly_rate = 0.0

    addresses = []
    for addr in ec2.describe_addresses().get("Addresses", []):
        addresses.append(
            {
                "allocation_id": addr.get("AllocationId", addr.get("PublicIp")),
                "associated": bool(addr.get("AssociationId")),
                "hourly_rate": hourly_rate,
            }
        )
    return addresses
