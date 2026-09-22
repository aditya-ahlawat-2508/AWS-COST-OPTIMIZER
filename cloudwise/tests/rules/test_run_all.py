from services.rules import run_all


def test_run_all_aggregates_across_resource_types():
    context = {
        "ec2_instances": [
            {"id": "i-1", "state": "running", "instance_type": "t3.medium", "monthly_cost": 30.4,
             "avg_cpu_percent": 1.0, "avg_network_bytes_per_day": 0},
        ],
        "ebs_volumes": [
            {"id": "vol-1", "state": "available", "size_gb": 100, "volume_type": "gp3",
             "price_per_gb_month": 0.08, "days_available": 30},
        ],
    }
    findings = run_all(context)
    rule_ids = {f.rule_id for f in findings}
    assert "idle_ec2" in rule_ids
    assert "unattached_ebs" in rule_ids


def test_run_all_tolerates_missing_context_keys():
    assert run_all({}) == []
