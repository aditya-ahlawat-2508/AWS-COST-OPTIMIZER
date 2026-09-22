import datetime
from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from services.scanner.ec2 import collect_ec2_instances


def _launch_instance(ec2_client, tags=None):
    kwargs = {}
    if tags:
        kwargs["TagSpecifications"] = [{"ResourceType": "instance", "Tags": tags}]
    resp = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t3.micro",
        **kwargs,
    )
    return resp["Instances"][0]["InstanceId"]


@mock_aws
def test_collect_ec2_instances_returns_expected_shape():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    instance_id = _launch_instance(ec2, tags=[{"Key": "env", "Value": "staging"}])

    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.return_value = 7.6

    instances = collect_ec2_instances(session, "us-east-1", pricing_client=fake_pricing)

    assert len(instances) == 1
    inst = instances[0]
    assert inst["id"] == instance_id
    assert inst["instance_type"] == "t3.micro"
    assert inst["state"] == "running"
    assert inst["monthly_cost"] == 7.6
    assert inst["env_tag"] == "staging"
    # No CloudWatch data published in the moto sandbox -> defaults to "assume busy".
    assert inst["avg_cpu_percent"] == 100.0
    assert inst["avg_network_bytes_per_day"] == 0.0
    assert inst["lookback_days"] == 14


@mock_aws
def test_collect_ec2_instances_uses_published_cloudwatch_metrics():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    cloudwatch = session.client("cloudwatch")
    instance_id = _launch_instance(ec2)

    now = datetime.datetime.utcnow()
    cloudwatch.put_metric_data(
        Namespace="AWS/EC2",
        MetricData=[
            {
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                "Timestamp": now - datetime.timedelta(days=1),
                "Value": 1.5,
                "Unit": "Percent",
            }
        ],
    )

    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.return_value = 7.6

    instances = collect_ec2_instances(session, "us-east-1", pricing_client=fake_pricing, now=now)

    assert instances[0]["avg_cpu_percent"] == 1.5


@mock_aws
def test_pricing_failure_does_not_crash_the_scan():
    session = boto3.Session(region_name="us-east-1")
    ec2 = session.client("ec2")
    _launch_instance(ec2)

    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.side_effect = LookupError("no price found")

    instances = collect_ec2_instances(session, "us-east-1", pricing_client=fake_pricing)

    assert len(instances) == 1
    assert instances[0]["monthly_cost"] == 0.0
