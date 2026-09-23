import pathlib
import sys
from datetime import date, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.analytics.anomalies import detect_spend_anomalies  # noqa: E402


def _series(start: date, daily_costs):
    return [(start + timedelta(days=i), cost) for i, cost in enumerate(daily_costs)]


def test_flags_a_clear_spike():
    start = date(2026, 1, 1)
    # 14 baseline days at ~$10/day, then 7 recent days at ~$20/day
    costs = [10.0] * 14 + [20.0] * 7
    daily_by_service = {"NAT Gateway": _series(start, costs)}

    anomalies = detect_spend_anomalies(daily_by_service)

    assert len(anomalies) == 1
    assert anomalies[0].service == "NAT Gateway"
    assert anomalies[0].baseline_daily_avg == 10.0
    assert anomalies[0].recent_daily_avg == 20.0
    assert anomalies[0].delta_monthly == 300.0  # $10/day * 30


def test_ignores_stable_spend():
    start = date(2026, 1, 1)
    costs = [10.0] * 21
    daily_by_service = {"AmazonEC2": _series(start, costs)}

    assert detect_spend_anomalies(daily_by_service) == []


def test_ignores_small_relative_increase_below_threshold():
    start = date(2026, 1, 1)
    costs = [10.0] * 14 + [11.0] * 7  # +10%, below the 30% default threshold
    daily_by_service = {"AmazonS3": _series(start, costs)}

    assert detect_spend_anomalies(daily_by_service) == []


def test_ignores_tiny_absolute_delta_even_if_relative_is_huge():
    start = date(2026, 1, 1)
    costs = [0.01] * 14 + [0.05] * 7  # 5x relative increase, but pennies
    daily_by_service = {"AWSLambda": _series(start, costs)}

    assert detect_spend_anomalies(daily_by_service) == []


def test_skips_services_with_insufficient_history():
    start = date(2026, 1, 1)
    daily_by_service = {"AmazonRDS": _series(start, [100.0] * 5)}

    assert detect_spend_anomalies(daily_by_service) == []


def test_sorts_by_monthly_delta_descending():
    start = date(2026, 1, 1)
    small_spike = _series(start, [10.0] * 14 + [15.0] * 7)
    big_spike = _series(start, [10.0] * 14 + [50.0] * 7)
    daily_by_service = {"Small": small_spike, "Big": big_spike}

    anomalies = detect_spend_anomalies(daily_by_service)

    assert [a.service for a in anomalies] == ["Big", "Small"]


def test_handles_zero_baseline_as_new_service_appearing():
    start = date(2026, 1, 1)
    costs = [0.0] * 14 + [10.0] * 7
    daily_by_service = {"AmazonBedrock": _series(start, costs)}

    anomalies = detect_spend_anomalies(daily_by_service)

    assert len(anomalies) == 1
    assert anomalies[0].baseline_daily_avg == 0.0
