"""RDS collector, shaped for services.rules.stopped_rds.

Same limitation as services/scanner/ebs.py's days_available: DescribeDBInstances
has no "stopped since" timestamp, so InstanceCreateTime is used as a
conservative proxy for days_stopped when the instance is currently stopped.
"""
import datetime
from typing import Any, Dict, List, Optional

from ..pricing.price_list import PriceListClient


def collect_rds_instances(
    session,
    region: str,
    pricing_client: Optional[PriceListClient] = None,
    now: Optional[datetime.datetime] = None,
) -> List[Dict[str, Any]]:
    rds = session.client("rds", region_name=region)
    pricing_client = pricing_client or PriceListClient()
    now = now or datetime.datetime.utcnow()

    instances = []
    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page.get("DBInstances", []):
            status = db["DBInstanceStatus"]
            create_time = db.get("InstanceCreateTime")
            days_since_create = (now - create_time.replace(tzinfo=None)).days if create_time else 0

            try:
                storage_price_per_gb = pricing_client.get_rds_storage_price_per_gb_month(db["Engine"], region)
            except Exception:
                storage_price_per_gb = 0.0

            instances.append(
                {
                    "id": db["DBInstanceIdentifier"],
                    "state": status,
                    "days_stopped": days_since_create if status == "stopped" else 0,
                    "storage_monthly_cost": round(db.get("AllocatedStorage", 0) * storage_price_per_gb, 2),
                }
            )
    return instances
