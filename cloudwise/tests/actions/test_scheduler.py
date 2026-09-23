import datetime
import os
import pathlib
import subprocess
import sys

import boto3
import pytest
from moto import mock_aws

ROOT = pathlib.Path(__file__).resolve().parents[2]
API_DIR = ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

TEST_DB_NAME = "cloudwise_test"
os.environ.setdefault(
    "DATABASE_URL",
    f"postgresql+psycopg://cloudwise_app:cloudwise_app_dev_password@localhost/{TEST_DB_NAME}",
)
os.environ.setdefault("CLERK_ISSUER", "https://test.clerk.accounts.dev")

_PSQL_ENV = dict(os.environ)
_PSQL_ENV["PGHOST"] = os.environ.get("TEST_PGHOST", "localhost")
if "TEST_PGUSER" in os.environ:
    _PSQL_ENV["PGUSER"] = os.environ["TEST_PGUSER"]
if "TEST_PGPASSWORD" in os.environ:
    _PSQL_ENV["PGPASSWORD"] = os.environ["TEST_PGPASSWORD"]


def _psql(*args: str) -> None:
    subprocess.run(
        ["psql", "-d", TEST_DB_NAME, "-v", "ON_ERROR_STOP=1", *args],
        check=True, capture_output=True, text=True, env=_PSQL_ENV,
    )


@pytest.fixture(scope="module", autouse=True)
def _reset_schema():
    _psql("-c", "DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    _psql("-f", str(API_DIR / "db" / "init.sql"))
    yield


@pytest.fixture(autouse=True)
def _truncate():
    yield
    _psql(
        "-c",
        "TRUNCATE organizations, users, aws_accounts, findings, change_requests, audit_log, "
        "spend_daily, schedules CASCADE;",
    )


from app.database import org_scoped_session  # noqa: E402
from app.models import AuditLog, AWSAccount, Organization, Schedule  # noqa: E402
from services.actions.scheduler import run_due_schedules  # noqa: E402


def _seed(start_hour=9, stop_hour=18, weekdays_only=True, enabled=True):
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
            actions_role_arn="arn:aws:iam::111111111111:role/CloudWiseActions",
            actions_external_id="ext-actions-1",
        )
        session.add(account)
        session.flush()
        account_id = account.id

    return org_id, account_id


@mock_aws
def test_starts_instance_within_office_hours_if_stopped():
    org_id, account_id = _seed()

    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]
    ec2.stop_instances(InstanceIds=[instance_id])

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        schedule = Schedule(
            org_id=org_id, account_id=account_id, resource_id=instance_id,
            timezone="UTC", start_hour=9, stop_hour=18, weekdays_only=True, enabled=True,
        )
        session.add(schedule)
        session.flush()

        # Wednesday 14:00 UTC -> within 9-18 office hours
        now = datetime.datetime(2026, 9, 23, 14, 0, tzinfo=datetime.timezone.utc)
        results = run_due_schedules(
            session, org_id, [schedule], {account_id: account}, region="us-east-1",
            now=now, boto_session=boto_session,
        )

    assert len(results) == 1
    assert results[0]["action"] == "start"
    assert results[0]["success"] is True

    described = ec2.describe_instances(InstanceIds=[instance_id])
    assert described["Reservations"][0]["Instances"][0]["State"]["Name"] in ("pending", "running")


@mock_aws
def test_stops_instance_outside_office_hours_if_running():
    org_id, account_id = _seed()

    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        schedule = Schedule(
            org_id=org_id, account_id=account_id, resource_id=instance_id,
            timezone="UTC", start_hour=9, stop_hour=18, weekdays_only=True, enabled=True,
        )
        session.add(schedule)
        session.flush()

        # 02:00 UTC -> outside 9-18 office hours
        now = datetime.datetime(2026, 9, 23, 2, 0, tzinfo=datetime.timezone.utc)
        results = run_due_schedules(
            session, org_id, [schedule], {account_id: account}, region="us-east-1",
            now=now, boto_session=boto_session,
        )

    assert results[0]["action"] == "stop"
    assert results[0]["success"] is True

    with org_scoped_session(org_id=str(org_id)) as session:
        audit_rows = session.query(AuditLog).filter_by(org_id=org_id).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].action == "run_schedule:stop_ec2"


@mock_aws
def test_no_op_when_state_already_matches_schedule():
    org_id, account_id = _seed()

    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]
    # Instance is running, and it's within office hours -> nothing to do.

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        schedule = Schedule(
            org_id=org_id, account_id=account_id, resource_id=instance_id,
            timezone="UTC", start_hour=9, stop_hour=18, weekdays_only=True, enabled=True,
        )
        session.add(schedule)
        session.flush()

        now = datetime.datetime(2026, 9, 23, 14, 0, tzinfo=datetime.timezone.utc)
        results = run_due_schedules(
            session, org_id, [schedule], {account_id: account}, region="us-east-1",
            now=now, boto_session=boto_session,
        )

    assert results == []


@mock_aws
def test_disabled_schedule_is_skipped():
    org_id, account_id = _seed()

    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        schedule = Schedule(
            org_id=org_id, account_id=account_id, resource_id=instance_id,
            timezone="UTC", start_hour=9, stop_hour=18, weekdays_only=True, enabled=False,
        )
        session.add(schedule)
        session.flush()

        now = datetime.datetime(2026, 9, 23, 2, 0, tzinfo=datetime.timezone.utc)
        results = run_due_schedules(
            session, org_id, [schedule], {account_id: account}, region="us-east-1",
            now=now, boto_session=boto_session,
        )

    assert results == []


@mock_aws
def test_account_without_actions_role_is_skipped():
    org_id, account_id = _seed()

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        account.actions_role_arn = None
        account.actions_external_id = None
        session.flush()

        schedule = Schedule(
            org_id=org_id, account_id=account_id, resource_id="i-doesnotmatter",
            timezone="UTC", start_hour=9, stop_hour=18, weekdays_only=True, enabled=True,
        )
        session.add(schedule)
        session.flush()

        now = datetime.datetime(2026, 9, 23, 2, 0, tzinfo=datetime.timezone.utc)
        results = run_due_schedules(session, org_id, [schedule], {account_id: account}, region="us-east-1", now=now)

    assert results == []
