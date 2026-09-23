import datetime
from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from services.scanner.ebs import collect_ebs_volumes


@mock_aws
def test_collect_ebs_volumes_returns_expected_shape():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    volume_id = ec2.create_volume(AvailabilityZone="us-east-1a", Size=100, VolumeType="gp2")["VolumeId"]

    fake_pricing = MagicMock()
    fake_pricing.get_ebs_price_per_gb_month.side_effect = lambda vt, region: {"gp2": 0.10, "gp3": 0.08}[vt]

    volumes = collect_ebs_volumes(session, "us-east-1", pricing_client=fake_pricing)

    assert len(volumes) == 1
    vol = volumes[0]
    assert vol["id"] == volume_id
    assert vol["volume_type"] == "gp2"
    assert vol["size_gb"] == 100
    assert vol["price_per_gb_month"] == 0.10
    assert vol["gp2_price_per_gb_month"] == 0.10
    assert vol["gp3_price_per_gb_month"] == 0.08


@mock_aws
def test_days_available_only_set_for_available_volumes():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]
    volume_id = ec2.create_volume(AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3")["VolumeId"]
    ec2.attach_volume(VolumeId=volume_id, InstanceId=instance_id, Device="/dev/sdf")

    fake_pricing = MagicMock()
    fake_pricing.get_ebs_price_per_gb_month.return_value = 0.08

    volumes = collect_ebs_volumes(
        session, "us-east-1", pricing_client=fake_pricing, now=datetime.datetime.utcnow()
    )

    attached = next(v for v in volumes if v["id"] == volume_id)
    assert attached["days_available"] == 0


@mock_aws
def test_pricing_failure_does_not_crash_ebs_scan():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3")

    fake_pricing = MagicMock()
    fake_pricing.get_ebs_price_per_gb_month.side_effect = LookupError("no price")

    volumes = collect_ebs_volumes(session, "us-east-1", pricing_client=fake_pricing)

    assert len(volumes) == 1
    assert volumes[0]["price_per_gb_month"] == 0.0
