import json
from unittest.mock import MagicMock

from services.pricing.price_list import PriceListClient


def _fake_price_list_item(hourly_rate: str) -> str:
    # A trimmed but structurally real AWS Price List API response item.
    return json.dumps(
        {
            "product": {"attributes": {"instanceType": "t3.micro"}},
            "terms": {
                "OnDemand": {
                    "ABCDEF.JRTCKXETXF": {
                        "priceDimensions": {
                            "ABCDEF.JRTCKXETXF.6YS6EN2CT7": {
                                "unit": "Hrs",
                                "pricePerUnit": {"USD": hourly_rate},
                            }
                        }
                    }
                }
            },
        }
    )


def test_get_ec2_hourly_rate_parses_price_list_response():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_fake_price_list_item("0.0104000000")]}

    client = PriceListClient(client=mock_client)
    rate = client.get_ec2_hourly_rate("t3.micro", "us-east-1")

    assert rate == 0.0104
    mock_client.get_products.assert_called_once()
    filters = mock_client.get_products.call_args.kwargs["Filters"]
    assert {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "t3.micro"} in filters


def test_get_ec2_hourly_rate_caches_result():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_fake_price_list_item("0.0104000000")]}
    client = PriceListClient(client=mock_client)

    client.get_ec2_hourly_rate("t3.micro", "us-east-1")
    client.get_ec2_hourly_rate("t3.micro", "us-east-1")

    assert mock_client.get_products.call_count == 1


def test_get_ec2_monthly_cost_multiplies_by_hours_per_month():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": [_fake_price_list_item("0.0100000000")]}
    client = PriceListClient(client=mock_client)

    assert client.get_ec2_monthly_cost("t3.micro", "us-east-1") == round(0.01 * 730, 2)


def test_raises_lookup_error_when_no_price_found():
    mock_client = MagicMock()
    mock_client.get_products.return_value = {"PriceList": []}
    client = PriceListClient(client=mock_client)

    try:
        client.get_ec2_hourly_rate("made.up.type", "us-east-1")
        assert False, "expected LookupError"
    except LookupError:
        pass


def test_rejects_unsupported_region():
    client = PriceListClient(client=MagicMock())
    try:
        client.get_ec2_hourly_rate("t3.micro", "mars-central-1")
        assert False, "expected ValueError"
    except ValueError:
        pass
