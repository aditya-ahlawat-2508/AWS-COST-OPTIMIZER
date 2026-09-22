"""EC2 collector: current state + CloudWatch utilization, shaped to feed
straight into services.rules.idle_ec2 / non_prod_schedule. Pricing comes from
services.pricing.price_list, not a hard-coded table.
"""
import datetime
from typing import Any, Dict, List, Optional

from ..pricing.price_list import PriceListClient

CPU_LOOKBACK_DAYS = 14
METRIC_PERIOD_SECONDS = 86400  # 1 day


def collect_ec2_instances(
    session,
    region: str,
    pricing_client: Optional[PriceListClient] = None,
    now: Optional[datetime.datetime] = None,
) -> List[Dict[str, Any]]:
    ec2 = session.client("ec2", region_name=region)
    cloudwatch = session.client("cloudwatch", region_name=region)
    pricing_client = pricing_client or PriceListClient()

    now = now or datetime.datetime.utcnow()
    start = now - datetime.timedelta(days=CPU_LOOKBACK_DAYS)

    instances = []
    for reservation in ec2.describe_instances().get("Reservations", []):
        for inst in reservation.get("Instances", []):
            instance_id = inst["InstanceId"]
            instance_type = inst["InstanceType"]
            state = inst["State"]["Name"]
            tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}

            avg_cpu = _metric_over_window(
                cloudwatch, "AWS/EC2", "CPUUtilization", instance_id, start, now, "Average"
            )
            avg_network_per_day = _metric_over_window(
                cloudwatch, "AWS/EC2", "NetworkOut", instance_id, start, now, "Sum"
            )

            monthly_cost = 0.0
            if state == "running":
                try:
                    monthly_cost = pricing_client.get_ec2_monthly_cost(instance_type, region)
                except Exception:
                    # A pricing miss shouldn't take the whole scan down — this
                    # instance just won't be priced, matching the graceful
                    # per-service degradation the original inventory code did.
                    monthly_cost = 0.0

            instances.append(
                {
                    "id": instance_id,
                    "state": state,
                    "instance_type": instance_type,
                    "monthly_cost": monthly_cost,
                    # No CloudWatch history yet (brand-new instance) defaults to
                    # "assume busy" so we never flag it idle on a false negative.
                    "avg_cpu_percent": avg_cpu if avg_cpu is not None else 100.0,
                    "avg_network_bytes_per_day": avg_network_per_day if avg_network_per_day is not None else 0.0,
                    "env_tag": tags.get("env") or tags.get("Environment"),
                    "lookback_days": CPU_LOOKBACK_DAYS,
                }
            )
    return instances


def _metric_over_window(cloudwatch, namespace: str, metric_name: str, instance_id: str, start, end, statistic: str):
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=start,
        EndTime=end,
        Period=METRIC_PERIOD_SECONDS,
        Statistics=[statistic],
    )
    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return None
    values = [dp[statistic] for dp in datapoints]
    return sum(values) / len(values)
