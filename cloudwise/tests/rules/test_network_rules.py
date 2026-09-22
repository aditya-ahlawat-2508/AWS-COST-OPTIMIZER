from services.rules import idle_nat_gateway, unused_eip
from services.rules.base import HOURS_PER_MONTH


def test_unused_eip_flags_unassociated_address():
    addresses = [{"allocation_id": "eipalloc-1", "associated": False, "hourly_rate": 0.005}]
    findings = unused_eip.detect(addresses)
    assert len(findings) == 1
    assert findings[0].monthly_savings == round(0.005 * HOURS_PER_MONTH, 2)


def test_unused_eip_ignores_associated_address():
    addresses = [{"allocation_id": "eipalloc-2", "associated": True, "hourly_rate": 0.005}]
    assert unused_eip.detect(addresses) == []


def test_idle_nat_gateway_flags_low_traffic():
    nats = [{"id": "nat-1", "state": "available", "hourly_rate": 0.045, "avg_bytes_out_per_day": 1024}]
    findings = idle_nat_gateway.detect(nats)
    assert len(findings) == 1
    assert findings[0].monthly_savings == round(0.045 * HOURS_PER_MONTH, 2)


def test_idle_nat_gateway_ignores_busy_gateway():
    nats = [{"id": "nat-2", "state": "available", "hourly_rate": 0.045, "avg_bytes_out_per_day": 5 * 1024 ** 3}]
    assert idle_nat_gateway.detect(nats) == []
