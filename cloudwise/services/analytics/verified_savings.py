"""Compares an account's service-level spend before and after an executed
change request (blueprint: "compare the next billing period in CUR against
the baseline and mark savings realized" — this is meant to be the product's
best marketing/retention number, so it's worth getting the arithmetic right
even if the granularity is limited).

Stated limitation, not hidden: services/cur/parser.py aggregates CUR by
account+day+service, not by individual resource (that needs CUR's
line_item_resource_id, which isn't parsed today). So this compares the
whole service's spend for the account the resource lives in, not that one
resource in isolation — directionally right, not a precise per-resource
number.
"""
from dataclasses import dataclass
from datetime import date
from typing import List, Tuple

RESOURCE_TYPE_TO_SERVICE = {
    "ec2_instance": "AmazonEC2",
    "ebs_volume": "AmazonEC2",  # EBS is billed under AmazonEC2 in CUR
    "elastic_ip": "AmazonEC2",
    "nat_gateway": "AmazonEC2-NatGateway",
    "rds_instance": "AmazonRDS",
}


@dataclass(frozen=True)
class VerifiedSavings:
    service: str
    before_daily_avg: float
    after_daily_avg: float
    verified_monthly_savings: float
    before_days: int
    after_days: int


def compute_verified_savings(
    before_costs: List[Tuple[date, float]], after_costs: List[Tuple[date, float]], service: str
) -> VerifiedSavings:
    before_avg = sum(cost for _, cost in before_costs) / len(before_costs) if before_costs else 0.0
    after_avg = sum(cost for _, cost in after_costs) / len(after_costs) if after_costs else 0.0
    return VerifiedSavings(
        service=service,
        before_daily_avg=round(before_avg, 2),
        after_daily_avg=round(after_avg, 2),
        verified_monthly_savings=round((before_avg - after_avg) * 30, 2),
        before_days=len(before_costs),
        after_days=len(after_costs),
    )
