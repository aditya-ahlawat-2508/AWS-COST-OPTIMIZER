"""EBS collector: current state + pricing, shaped for services.rules.unattached_ebs
and gp2_to_gp3.

Known limitation: EC2 doesn't expose a "when did this volume become
unattached" timestamp anywhere in DescribeVolumes, and CloudTrail lookups
add real complexity (limited retention, needs cloudtrail:LookupEvents which
isn't in the read-only role) for a v1. We use volume age (time since
creation) as a conservative proxy for days_available — a volume created
recently won't be flagged even if it's never been attached, which is the
safe direction to be wrong in. Replacing this with real CloudTrail-based
detach tracking is the natural next step.
"""
import datetime
from typing import Any, Dict, List, Optional

from ..pricing.price_list import PriceListClient


def collect_ebs_volumes(
    session,
    region: str,
    pricing_client: Optional[PriceListClient] = None,
    now: Optional[datetime.datetime] = None,
) -> List[Dict[str, Any]]:
    ec2 = session.client("ec2", region_name=region)
    pricing_client = pricing_client or PriceListClient()
    now = now or datetime.datetime.utcnow()

    volumes = []
    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate():
        for vol in page.get("Volumes", []):
            volume_type = vol["VolumeType"]
            create_time = vol.get("CreateTime")
            days_since_create = (now - create_time.replace(tzinfo=None)).days if create_time else 0

            try:
                price_per_gb = pricing_client.get_ebs_price_per_gb_month(volume_type, region)
            except Exception:
                price_per_gb = 0.0

            entry: Dict[str, Any] = {
                "id": vol["VolumeId"],
                "state": vol["State"],
                "size_gb": vol["Size"],
                "volume_type": volume_type,
                "price_per_gb_month": price_per_gb,
                "days_available": days_since_create if vol["State"] == "available" else 0,
            }

            if volume_type == "gp2":
                try:
                    entry["gp2_price_per_gb_month"] = price_per_gb
                    entry["gp3_price_per_gb_month"] = pricing_client.get_ebs_price_per_gb_month("gp3", region)
                except Exception:
                    entry["gp2_price_per_gb_month"] = 0.0
                    entry["gp3_price_per_gb_month"] = 0.0

            volumes.append(entry)
    return volumes
