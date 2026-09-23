from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from services.scanner.nat_gateway import collect_nat_gateways


def _make_nat_gateway(session):
    ec2 = session.client("ec2")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/24")["Subnet"]["SubnetId"]
    eip_alloc = ec2.allocate_address(Domain="vpc")["AllocationId"]
    nat = ec2.create_nat_gateway(SubnetId=subnet_id, AllocationId=eip_alloc)["NatGateway"]
    return nat["NatGatewayId"]


@mock_aws
def test_collect_nat_gateways_returns_expected_shape():
    session = boto3.Session(region_name="us-east-1")
    nat_id = _make_nat_gateway(session)

    fake_pricing = MagicMock()
    fake_pricing.get_nat_gateway_hourly_rate.return_value = 0.045

    gateways = collect_nat_gateways(session, "us-east-1", pricing_client=fake_pricing)

    assert len(gateways) == 1
    gw = gateways[0]
    assert gw["id"] == nat_id
    assert gw["hourly_rate"] == 0.045
    assert gw["avg_bytes_out_per_day"] == 0.0  # no CloudWatch data published in moto


@mock_aws
def test_pricing_failure_does_not_crash_nat_scan():
    session = boto3.Session(region_name="us-east-1")
    _make_nat_gateway(session)

    fake_pricing = MagicMock()
    fake_pricing.get_nat_gateway_hourly_rate.side_effect = LookupError("no price")

    gateways = collect_nat_gateways(session, "us-east-1", pricing_client=fake_pricing)

    assert len(gateways) == 1
    assert gateways[0]["hourly_rate"] == 0.0
