from unittest.mock import MagicMock, patch

import cost_explorer


def _fake_service_response():
    return {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2024-01-01", "End": "2024-01-31"},
                "Groups": [
                    {"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "12.34", "Unit": "USD"}}},
                    {"Keys": ["Amazon S3"], "Metrics": {"UnblendedCost": {"Amount": "0.00", "Unit": "USD"}}},
                ],
            }
        ]
    }


def _fake_daily_response():
    return {
        "ResultsByTime": [
            {"TimePeriod": {"Start": "2024-01-01"}, "Total": {"UnblendedCost": {"Amount": "1.20", "Unit": "USD"}}},
            {"TimePeriod": {"Start": "2024-01-02"}, "Total": {"UnblendedCost": {"Amount": "0.95", "Unit": "USD"}}},
        ]
    }


@patch("cost_explorer.boto3.client")
def test_get_cost_breakdown_includes_daily_trend(mock_boto_client):
    # Regression test for the bug where the daily_trend loop was dedented to
    # module level, which made the whole file fail to import (SyntaxError)
    # and took every Lambda action down with it, including ping.
    mock_ce = MagicMock()
    mock_ce.get_cost_and_usage.side_effect = [_fake_service_response(), _fake_daily_response()]
    mock_boto_client.return_value = mock_ce

    result = cost_explorer.get_cost_breakdown(days=30)

    assert result["total_cost"] == 12.34
    assert result["by_service"] == [{"service": "Amazon EC2", "cost": 12.34}]
    assert result["daily_trend"] == [
        {"date": "2024-01-01", "cost": 1.2},
        {"date": "2024-01-02", "cost": 0.95},
    ]


@patch("cost_explorer.boto3.client")
def test_get_monthly_forecast_handles_errors_gracefully(mock_boto_client):
    mock_ce = MagicMock()
    mock_ce.get_cost_forecast.side_effect = Exception("boom")
    mock_boto_client.return_value = mock_ce

    result = cost_explorer.get_monthly_forecast()

    assert result["forecast"] is None
    assert "boom" in result["message"]
