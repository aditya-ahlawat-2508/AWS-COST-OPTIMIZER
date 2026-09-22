from services.rules import gp2_to_gp3, unattached_ebs


def test_unattached_ebs_flags_long_available_volume():
    volumes = [{"id": "vol-1", "state": "available", "size_gb": 100, "volume_type": "gp3",
                "price_per_gb_month": 0.08, "days_available": 10}]
    findings = unattached_ebs.detect(volumes)
    assert len(findings) == 1
    assert findings[0].monthly_savings == 8.0


def test_unattached_ebs_ignores_recently_detached():
    volumes = [{"id": "vol-2", "state": "available", "size_gb": 100, "volume_type": "gp3",
                "price_per_gb_month": 0.08, "days_available": 1}]
    assert unattached_ebs.detect(volumes) == []


def test_unattached_ebs_ignores_attached_volume():
    volumes = [{"id": "vol-3", "state": "in-use", "size_gb": 100, "volume_type": "gp3",
                "price_per_gb_month": 0.08, "days_available": 30}]
    assert unattached_ebs.detect(volumes) == []


def test_gp2_to_gp3_computes_price_delta():
    volumes = [{"id": "vol-4", "volume_type": "gp2", "size_gb": 500,
                "gp2_price_per_gb_month": 0.10, "gp3_price_per_gb_month": 0.08}]
    findings = gp2_to_gp3.detect(volumes)
    assert len(findings) == 1
    assert findings[0].monthly_savings == 10.0  # 500 * (0.10 - 0.08)


def test_gp2_to_gp3_ignores_non_gp2_volumes():
    volumes = [{"id": "vol-5", "volume_type": "gp3", "size_gb": 500,
                "gp2_price_per_gb_month": 0.10, "gp3_price_per_gb_month": 0.08}]
    assert gp2_to_gp3.detect(volumes) == []
