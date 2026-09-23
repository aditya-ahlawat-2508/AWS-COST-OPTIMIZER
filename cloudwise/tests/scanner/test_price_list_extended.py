import json
from unittest.mock import MagicMock

from services.pricing.price_list import PriceListClient


def _price_item(rate: str):
    return json.dumps(
        {
            "terms": {
                "OnDemand": {
                    "X.Y": {"priceDimensions": {"X.Y.Z": {"unit": "GB-Mo", "pricePerUnit": {"USD": rate}}}}
                }
            }
        }
    )


def test_get_ebs_price_per_gb_month():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_price_item("0.0800000000")]}
    client = PriceListClient(client=mock_client)

    price = client.get_ebs_price_per_gb_month("gp3", "us-east-1")

    assert price == 0.08
    filters = mock_client.get_products.call_args.kwargs["Filters"]
    assert {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": "gp3"} in filters


def test_get_eip_hourly_rate():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_price_item("0.0050000000")]}
    client = PriceListClient(client=mock_client)

    assert client.get_eip_hourly_rate("us-east-1") == 0.005


def test_get_nat_gateway_hourly_rate():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_price_item("0.0450000000")]}
    client = PriceListClient(client=mock_client)

    assert client.get_nat_gateway_hourly_rate("us-east-1") == 0.045


def test_get_rds_storage_price_per_gb_month():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_price_item("0.1150000000")]}
    client = PriceListClient(client=mock_client)

    price = client.get_rds_storage_price_per_gb_month("PostgreSQL", "us-east-1")

    assert price == 0.115
    filters = mock_client.get_products.call_args.kwargs["Filters"]
    assert {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": "PostgreSQL"} in filters


def test_pricing_caches_across_all_new_methods():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_price_item("0.0450000000")]}
    client = PriceListClient(client=mock_client)

    client.get_nat_gateway_hourly_rate("us-east-1")
    client.get_nat_gateway_hourly_rate("us-east-1")

    assert mock_client.get_products.call_count == 1
