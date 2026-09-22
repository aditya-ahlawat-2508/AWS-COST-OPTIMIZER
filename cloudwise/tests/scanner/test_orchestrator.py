from unittest.mock import MagicMock

import boto3
from moto import mock_aws
from sqlalchemy import select

from app.database import org_scoped_session
from app.models import AWSAccount, Finding, Organization
from services.scanner.orchestrator import run_scan_for_account


def _make_org_and_account():
    with org_scoped_session(org_id=None) as session:
        org = Organization(name="Acme")
        session.add(org)
        session.flush()
        org_id = org.id

    with org_scoped_session(org_id=str(org_id)) as session:
        account = AWSAccount(
            org_id=org_id,
            aws_account_id="111111111111",
            role_arn="arn:aws:iam::111111111111:role/CloudWiseReadOnly",
            external_id="ext-1",
        )
        session.add(account)
        session.flush()
        account_id = account.id

    return org_id, account_id


@mock_aws
def test_scan_writes_findings_for_idle_instance():
    org_id, account_id = _make_org_and_account()

    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")

    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.return_value = 7.6

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        result = run_scan_for_account(
            session, org_id, account, region="us-east-1", pricing_client=fake_pricing, boto_session=boto_session
        )

    # No CloudWatch metrics published in the moto sandbox means avg_cpu
    # defaults to 100 (assume busy), so idle_ec2 should NOT fire — and
    # non_prod_schedule needs an env tag, which this instance lacks too.
    assert result["resources_scanned"] == 1
    assert result["findings_written"] == 0
    with org_scoped_session(org_id=str(org_id)) as session:
        findings = session.execute(select(Finding).where(Finding.org_id == org_id)).scalars().all()
        assert findings == []


@mock_aws
def test_scan_persists_finding_evidence_and_fix():
    import datetime

    org_id, account_id = _make_org_and_account()

    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    cloudwatch = boto_session.client("cloudwatch")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]

    now = datetime.datetime.utcnow()
    cloudwatch.put_metric_data(
        Namespace="AWS/EC2",
        MetricData=[
            {
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                "Timestamp": now - datetime.timedelta(days=1),
                "Value": 0.5,
                "Unit": "Percent",
            }
        ],
    )

    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.return_value = 7.6

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        result = run_scan_for_account(
            session, org_id, account, region="us-east-1", pricing_client=fake_pricing, boto_session=boto_session
        )
    assert result["findings_written"] == 1

    with org_scoped_session(org_id=str(org_id)) as session:
        finding = session.execute(select(Finding).where(Finding.org_id == org_id)).scalar_one()
        assert finding.rule_id == "idle_ec2"
        assert finding.resource_id == instance_id
        assert float(finding.monthly_savings) == 7.6
        assert "fix" in finding.evidence
        assert finding.status == "open"


@mock_aws
def test_rescan_preserves_user_dismissed_status():
    import datetime

    org_id, account_id = _make_org_and_account()

    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    cloudwatch = boto_session.client("cloudwatch")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]
    now = datetime.datetime.utcnow()
    cloudwatch.put_metric_data(
        Namespace="AWS/EC2",
        MetricData=[
            {
                "MetricName": "CPUUtilization",
                "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                "Timestamp": now - datetime.timedelta(days=1),
                "Value": 0.5,
                "Unit": "Percent",
            }
        ],
    )
    fake_pricing = MagicMock()
    fake_pricing.get_ec2_monthly_cost.return_value = 7.6

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        run_scan_for_account(
            session, org_id, account, region="us-east-1", pricing_client=fake_pricing, boto_session=boto_session
        )

    with org_scoped_session(org_id=str(org_id)) as session:
        finding = session.execute(select(Finding).where(Finding.org_id == org_id)).scalar_one()
        finding.status = "dismissed"

    fake_pricing.get_ec2_monthly_cost.return_value = 9.9  # price changed since last scan
    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        run_scan_for_account(
            session, org_id, account, region="us-east-1", pricing_client=fake_pricing, boto_session=boto_session
        )

    with org_scoped_session(org_id=str(org_id)) as session:
        finding = session.execute(select(Finding).where(Finding.org_id == org_id)).scalar_one()
        assert finding.status == "dismissed"
        assert float(finding.monthly_savings) == 9.9
