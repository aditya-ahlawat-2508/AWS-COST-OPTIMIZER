from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from services.scanner.rds import collect_rds_instances


@mock_aws
def test_collect_rds_instances_returns_expected_shape():
    session = boto3.Session(region_name="us-east-1")
    rds = session.client("rds")
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=100,
    )

    fake_pricing = MagicMock()
    fake_pricing.get_rds_storage_price_per_gb_month.return_value = 0.115

    instances = collect_rds_instances(session, "us-east-1", pricing_client=fake_pricing)

    assert len(instances) == 1
    inst = instances[0]
    assert inst["id"] == "test-db"
    assert inst["state"] == "available"
    assert inst["days_stopped"] == 0
    assert inst["storage_monthly_cost"] == round(100 * 0.115, 2)


@mock_aws
def test_days_stopped_only_set_for_stopped_instances():
    session = boto3.Session(region_name="us-east-1")
    rds = session.client("rds")
    rds.create_db_instance(
        DBInstanceIdentifier="test-db-2",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=20,
    )
    rds.stop_db_instance(DBInstanceIdentifier="test-db-2")

    fake_pricing = MagicMock()
    fake_pricing.get_rds_storage_price_per_gb_month.return_value = 0.115

    instances = collect_rds_instances(session, "us-east-1", pricing_client=fake_pricing)

    assert instances[0]["state"] == "stopped"
    assert instances[0]["days_stopped"] >= 0


@mock_aws
def test_pricing_failure_does_not_crash_rds_scan():
    session = boto3.Session(region_name="us-east-1")
    rds = session.client("rds")
    rds.create_db_instance(
        DBInstanceIdentifier="test-db-3",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=20,
    )

    fake_pricing = MagicMock()
    fake_pricing.get_rds_storage_price_per_gb_month.side_effect = LookupError("no price")

    instances = collect_rds_instances(session, "us-east-1", pricing_client=fake_pricing)

    assert len(instances) == 1
    assert instances[0]["storage_monthly_cost"] == 0.0
