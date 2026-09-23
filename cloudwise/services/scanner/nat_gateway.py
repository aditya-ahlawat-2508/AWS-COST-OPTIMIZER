"""NAT Gateway collector, shaped for services.rules.idle_nat_gateway."""
import datetime
from typing import Any, Dict, List, Optional

from ..pricing.price_list import PriceListClient

LOOKBACK_DAYS = 14


def collect_nat_gateways(
    session,
    region: str,
    pricing_client: Optional[PriceListClient] = None,
    now: Optional[datetime.datetime] = None,
) -> List[Dict[str, Any]]:
    ec2 = session.client("ec2", region_name=region)
    cloudwatch = session.client("cloudwatch", region_name=region)
    pricing_client = pricing_client or PriceListClient()
    now = now or datetime.datetime.utcnow()
    start = now - datetime.timedelta(days=LOOKBACK_DAYS)

    try:
        hourly_rate = pricing_client.get_nat_gateway_hourly_rate(region)
    except Exception:
        hourly_rate = 0.0

    gateways = []
    for nat in ec2.describe_nat_gateways().get("NatGateways", []):
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/NATGateway",
            MetricName="BytesOutToDestination",
            Dimensions=[{"Name": "NatGatewayId", "Value": nat["NatGatewayId"]}],
            StartTime=start,
            EndTime=now,
            Period=86400,
            Statistics=["Sum"],
        )
        datapoints = response.get("Datapoints", [])
        avg_bytes_out_per_day = (
            sum(dp["Sum"] for dp in datapoints) / len(datapoints) if datapoints else 0.0
        )

        gateways.append(
            {
                "id": nat["NatGatewayId"],
                "state": nat["State"],
                "hourly_rate": hourly_rate,
                "avg_bytes_out_per_day": avg_bytes_out_per_day,
            }
        )
    return gateways
