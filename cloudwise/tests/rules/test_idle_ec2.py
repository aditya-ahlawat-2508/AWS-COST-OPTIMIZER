from services.rules import idle_ec2


def test_flags_idle_running_instance():
    instances = [
        {"id": "i-1", "state": "running", "instance_type": "t3.medium", "monthly_cost": 30.4,
         "avg_cpu_percent": 1.2, "avg_network_bytes_per_day": 1024},
    ]
    findings = idle_ec2.detect(instances)
    assert len(findings) == 1
    assert findings[0].monthly_savings == 30.4
    assert findings[0].rule_id == "idle_ec2"


def test_ignores_busy_instance():
    instances = [
        {"id": "i-2", "state": "running", "instance_type": "t3.medium", "monthly_cost": 30.4,
         "avg_cpu_percent": 45.0, "avg_network_bytes_per_day": 1024},
    ]
    assert idle_ec2.detect(instances) == []


def test_ignores_stopped_instance():
    instances = [
        {"id": "i-3", "state": "stopped", "instance_type": "t3.medium", "monthly_cost": 30.4,
         "avg_cpu_percent": 0.0, "avg_network_bytes_per_day": 0},
    ]
    assert idle_ec2.detect(instances) == []


def test_ignores_low_cpu_but_high_network():
    # Low CPU alone isn't enough — e.g. a NAT-heavy proxy box with idle CPU.
    instances = [
        {"id": "i-4", "state": "running", "instance_type": "t3.medium", "monthly_cost": 30.4,
         "avg_cpu_percent": 1.0, "avg_network_bytes_per_day": 50 * 1024 * 1024},
    ]
    assert idle_ec2.detect(instances) == []
