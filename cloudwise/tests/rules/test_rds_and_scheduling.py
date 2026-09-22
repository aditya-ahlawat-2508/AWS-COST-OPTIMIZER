from services.rules import non_prod_schedule, stopped_rds


def test_stopped_rds_flags_forgotten_instance():
    instances = [{"id": "db-1", "state": "stopped", "days_stopped": 6, "storage_monthly_cost": 12.5}]
    findings = stopped_rds.detect(instances)
    assert len(findings) == 1
    assert findings[0].monthly_savings == 12.5


def test_stopped_rds_ignores_recently_stopped():
    instances = [{"id": "db-2", "state": "stopped", "days_stopped": 1, "storage_monthly_cost": 12.5}]
    assert stopped_rds.detect(instances) == []


def test_non_prod_schedule_flags_staging_instance():
    instances = [{"id": "i-1", "state": "running", "env_tag": "staging", "monthly_cost": 100.0}]
    findings = non_prod_schedule.detect(instances)
    assert len(findings) == 1
    # 60/168 hours kept -> 108/168 saved
    assert findings[0].monthly_savings == round(100.0 * (1 - 60 / 168), 2)


def test_non_prod_schedule_ignores_prod_instance():
    instances = [{"id": "i-2", "state": "running", "env_tag": "prod", "monthly_cost": 100.0}]
    assert non_prod_schedule.detect(instances) == []
