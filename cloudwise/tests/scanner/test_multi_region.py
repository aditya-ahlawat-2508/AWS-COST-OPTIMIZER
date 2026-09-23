from unittest.mock import MagicMock

import boto3
from moto import mock_aws

from services.scanner.orchestrator import discover_regions, run_scan_for_account
from app.database import org_scoped_session
from app.models import AWSAccount, Organization


def _make_org_and_account():
    with org_scoped_session(org_id=None) as session:
        org = Organization(name="Acme")
        session.add(org)
        session.flush()
        org_id = org.id

    with org_scoped_session(org_id=str(org_id)) as session:
        account = AWSAccount(
            org_id=org_id, aws_account_id="111111111111",
            role_arn="arn:aws:iam::111111111111:role/CloudWiseReadOnly", external_id="ext-1",
        )
        session.add(account)
        session.flush()
        return org_id, account.id


@mock_aws
def test_discover_regions_returns_multiple_regions():
    session = boto3.Session(region_name="us-east-1")
    regions = discover_regions(session)
    assert "us-east-1" in regions
    assert "us-west-2" in regions
    assert len(regions) > 5  # moto returns the full standard region list


@mock_aws
def test_scan_aggregates_instances_across_regions():
    boto_session = boto3.Session(region_name="us-east-1")
    boto_session.client("ec2", region_name="us-east-1").run_instances(
        ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro"
    )
    boto_session.client("ec2", region_name="us-west-2").run_instances(
        ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro"
    )

    org_id, account_id = _make_org_and_account()
    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.return_value = 7.6

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        result = run_scan_for_account(
            session, org_id, account, regions=["us-east-1", "us-west-2"],
            pricing_client=fake_pricing, boto_session=boto_session,
        )

    # 2 instances + their 2 auto-created root EBS volumes = 4
    assert result["resources_scanned"] == 4
    assert set(result["regions_scanned"]) == {"us-east-1", "us-west-2"}


@mock_aws
def test_scan_defaults_to_discovering_all_regions_when_none_given():
    boto_session = boto3.Session(region_name="us-east-1")
    boto_session.client("ec2", region_name="eu-west-1").run_instances(
        ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro"
    )

    org_id, account_id = _make_org_and_account()
    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.return_value = 7.6

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        result = run_scan_for_account(
            session, org_id, account, pricing_client=fake_pricing, boto_session=boto_session,
        )

    assert "eu-west-1" in result["regions_scanned"]
    assert result["resources_scanned"] >= 2  # the eu-west-1 instance + its root volume
