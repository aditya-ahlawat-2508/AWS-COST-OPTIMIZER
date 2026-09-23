import pathlib
import sys
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.analytics.verified_savings import RESOURCE_TYPE_TO_SERVICE, compute_verified_savings  # noqa: E402


def _series(start, costs):
    return [(start + timedelta(days=i), cost) for i, cost in enumerate(costs)]


def test_computes_positive_savings_when_after_spend_drops():
    before = _series(date(2026, 1, 1), [10.0] * 7)
    after = _series(date(2026, 1, 8), [4.0] * 7)

    result = compute_verified_savings(before, after, "AmazonEC2")

    assert result.before_daily_avg == 10.0
    assert result.after_daily_avg == 4.0
    assert result.verified_monthly_savings == 180.0  # (10-4)*30
    assert result.before_days == 7
    assert result.after_days == 7


def test_zero_savings_when_spend_unchanged():
    before = _series(date(2026, 1, 1), [10.0] * 5)
    after = _series(date(2026, 1, 6), [10.0] * 5)

    result = compute_verified_savings(before, after, "AmazonEC2")
    assert result.verified_monthly_savings == 0.0


def test_negative_savings_when_spend_increased():
    before = _series(date(2026, 1, 1), [10.0] * 5)
    after = _series(date(2026, 1, 6), [15.0] * 5)

    result = compute_verified_savings(before, after, "AmazonEC2")
    assert result.verified_monthly_savings == -150.0


def test_handles_empty_before_or_after_gracefully():
    after = _series(date(2026, 1, 1), [5.0] * 3)
    result = compute_verified_savings([], after, "AmazonEC2")
    assert result.before_daily_avg == 0.0
    assert result.before_days == 0


def test_resource_type_to_service_mapping_covers_all_action_types():
    for resource_type in ("ec2_instance", "ebs_volume", "elastic_ip", "nat_gateway", "rds_instance"):
        assert resource_type in RESOURCE_TYPE_TO_SERVICE
