from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from services.scanner.eip import collect_elastic_ips


@mock_aws
def test_collect_elastic_ips_reports_association_status():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]

    associated = ec2.allocate_address(Domain="vpc")
    ec2.associate_address(InstanceId=instance_id, AllocationId=associated["AllocationId"])
    unassociated = ec2.allocate_address(Domain="vpc")

    fake_pricing = MagicMock()
    fake_pricing.get_eip_hourly_rate.return_value = 0.005

    addresses = collect_elastic_ips(session, "us-east-1", pricing_client=fake_pricing)

    by_id = {a["allocation_id"]: a for a in addresses}
    assert by_id[associated["AllocationId"]]["associated"] is True
    assert by_id[unassociated["AllocationId"]]["associated"] is False
    assert by_id[unassociated["AllocationId"]]["hourly_rate"] == 0.005


@mock_aws
def test_pricing_failure_does_not_crash_eip_scan():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    ec2.allocate_address(Domain="vpc")

    fake_pricing = MagicMock()
    fake_pricing.get_eip_hourly_rate.side_effect = LookupError("no price")

    addresses = collect_elastic_ips(session, "us-east-1", pricing_client=fake_pricing)

    assert len(addresses) == 1
    assert addresses[0]["hourly_rate"] == 0.0
