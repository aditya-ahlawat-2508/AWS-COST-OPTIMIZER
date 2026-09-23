"""AWS Price List API client, replacing the portfolio version's hard-coded
5-instance table + $20 fallback (services_inventory.py). The comment in that
file claiming the Pricing API needs an AWS Organization is wrong — any
account can call it; it's just only served out of us-east-1 / ap-south-1.
"""
import json
import time
from typing import Dict, List, Optional, Tuple

import boto3

HOURS_PER_MONTH = 730
CACHE_TTL_SECONDS = 24 * 60 * 60

# The Price List Query API (GetProducts) is only available in these two
# regions regardless of which region's prices you're asking about.
PRICE_LIST_API_REGION = "us-east-1"

REGION_TO_LOCATION = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
}


class PriceListClient:
    def __init__(self, client: Optional[object] = None):
        self._client = client or boto3.client("pricing", region_name=PRICE_LIST_API_REGION)
        self._cache: Dict[str, Tuple[float, float]] = {}

    def _location(self, region: str) -> str:
        location = REGION_TO_LOCATION.get(region)
        if location is None:
            raise ValueError(f"Unsupported region for pricing lookup: {region}")
        return location

    def _cached_price(self, cache_key: str, service_code: str, filters: List[Dict[str, str]]) -> float:
        cached = self._cache.get(cache_key)
        if cached is not None and (time.time() - cached[1]) < CACHE_TTL_SECONDS:
            return cached[0]

        response = self._client.get_products(ServiceCode=service_code, Filters=filters, MaxResults=1)
        price_list = response.get("PriceList", [])
        if not price_list:
            raise LookupError(f"No On-Demand price found for {cache_key}")

        rate = _extract_on_demand_hourly_rate(price_list[0])
        self._cache[cache_key] = (rate, time.time())
        return rate

    def get_ec2_hourly_rate(self, instance_type: str, region: str, operating_system: str = "Linux") -> float:
        location = self._location(region)
        return self._cached_price(
            f"ec2:{instance_type}:{region}:{operating_system}",
            "AmazonEC2",
            [
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": operating_system},
                {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
            ],
        )

    def get_ec2_monthly_cost(self, instance_type: str, region: str, operating_system: str = "Linux") -> float:
        return round(self.get_ec2_hourly_rate(instance_type, region, operating_system) * HOURS_PER_MONTH, 2)

    def get_ebs_price_per_gb_month(self, volume_type: str, region: str) -> float:
        location = self._location(region)
        volume_api_name = {"gp2": "gp2", "gp3": "gp3", "io1": "io1", "io2": "io2", "st1": "st1", "sc1": "sc1"}[
            volume_type
        ]
        return self._cached_price(
            f"ebs:{volume_type}:{region}",
            "AmazonEC2",
            [
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
                {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": volume_api_name},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
            ],
        )

    def get_eip_hourly_rate(self, region: str) -> float:
        location = self._location(region)
        return self._cached_price(
            f"eip:{region}",
            "AmazonVPC",
            [
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "IP Address"},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "group", "Value": "VPCPublicIPv4Address"},
            ],
        )

    def get_nat_gateway_hourly_rate(self, region: str) -> float:
        location = self._location(region)
        return self._cached_price(
            f"nat:{region}",
            "AmazonVPC",
            [
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "NAT Gateway"},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
            ],
        )

    def get_rds_storage_price_per_gb_month(self, engine: str, region: str, storage_type: str = "General Purpose") -> float:
        location = self._location(region)
        return self._cached_price(
            f"rds-storage:{engine}:{region}",
            "AmazonRDS",
            [
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Database Storage"},
                {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": engine},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "volumeType", "Value": storage_type},
                {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Single-AZ"},
            ],
        )


def _extract_on_demand_hourly_rate(price_list_json_item: str) -> float:
    product = json.loads(price_list_json_item)
    on_demand_terms = product["terms"]["OnDemand"]
    first_term = next(iter(on_demand_terms.values()))
    first_dimension = next(iter(first_term["priceDimensions"].values()))
    return float(first_dimension["pricePerUnit"]["USD"])
