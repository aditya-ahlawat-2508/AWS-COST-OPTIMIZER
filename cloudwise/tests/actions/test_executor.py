import pathlib
import subprocess
import sys

import boto3
import pytest
from moto import mock_aws

ROOT = pathlib.Path(__file__).resolve().parents[2]
API_DIR = ROOT / "apps" / "api"
sys.path.insert(0, str(API_DIR))

import os  # noqa: E402

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
        check=True,
        capture_output=True,
        text=True,
        env=_PSQL_ENV,
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
        "TRUNCATE organizations, users, aws_accounts, findings, change_requests, audit_log, spend_daily CASCADE;",
    )


from app.database import org_scoped_session  # noqa: E402
from app.models import AuditLog, AWSAccount, ChangeRequest, Finding, Organization, User  # noqa: E402
from services.actions.executor import execute_change_request  # noqa: E402


def _seed(action_type="stop_ec2", resource_id=None):
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

        user = User(org_id=org_id, clerk_user_id="user_1", email="a@acmecorp.io", role="owner")
        session.add(user)
        session.flush()

        finding = Finding(
            org_id=org_id,
            account_id=account.id,
            rule_id="idle_ec2",
            resource_id=resource_id or "i-placeholder",
            resource_type="ec2_instance",
            evidence={"fix": "Stop it."},
            monthly_savings=10.0,
            effort="low",
            risk="medium",
        )
        session.add(finding)
        session.flush()

        change_request = ChangeRequest(
            org_id=org_id,
            finding_id=finding.id,
            action_type=action_type,
            requested_by=user.id,
            approved_by=user.id,
            status="approved",
        )
        session.add(change_request)
        session.flush()

        return org_id, account.id, finding.id, change_request.id


@mock_aws
def test_execute_stop_ec2_succeeds_and_writes_audit_log():
    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]

    org_id, account_id, _finding_id, cr_id = _seed(action_type="stop_ec2", resource_id=instance_id)

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        cr = session.get(ChangeRequest, cr_id)
        outcome = execute_change_request(session, cr, account, region="us-east-1", boto_session=boto_session)

    assert outcome["success"] is True

    with org_scoped_session(org_id=str(org_id)) as session:
        cr = session.get(ChangeRequest, cr_id)
        assert cr.status == "executed"
        assert cr.executed_at is not None

        audit_rows = session.query(AuditLog).filter_by(org_id=org_id).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].action == "execute_change_request:stop_ec2"
        assert audit_rows[0].details["success"] is True


@mock_aws
def test_execute_marks_failed_when_precheck_fails():
    boto_session = boto3.Session(region_name="us-east-1")
    ec2 = boto_session.client("ec2")
    instance_id = ec2.run_instances(ImageId="ami-12345678", MinCount=1, MaxCount=1, InstanceType="t3.micro")[
        "Instances"
    ][0]["InstanceId"]
    ec2.stop_instances(InstanceIds=[instance_id])  # already stopped -> pre-check should fail

    org_id, account_id, _finding_id, cr_id = _seed(action_type="stop_ec2", resource_id=instance_id)

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        cr = session.get(ChangeRequest, cr_id)
        outcome = execute_change_request(session, cr, account, region="us-east-1", boto_session=boto_session)

    assert outcome["success"] is False

    with org_scoped_session(org_id=str(org_id)) as session:
        cr = session.get(ChangeRequest, cr_id)
        assert cr.status == "failed"
        assert "error" in cr.execution_result


def test_execute_refuses_unapproved_change_request():
    org_id, account_id, _finding_id, cr_id = _seed()
    with org_scoped_session(org_id=str(org_id)) as session:
        cr = session.get(ChangeRequest, cr_id)
        cr.status = "pending"
        session.flush()

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        cr = session.get(ChangeRequest, cr_id)
        with pytest.raises(ValueError, match="not approved"):
            execute_change_request(session, cr, account)


def test_execute_refuses_account_without_actions_role():
    org_id, account_id, _finding_id, cr_id = _seed()
    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        account.actions_role_arn = None
        account.actions_external_id = None
        session.flush()

    with org_scoped_session(org_id=str(org_id)) as session:
        account = session.get(AWSAccount, account_id)
        cr = session.get(ChangeRequest, cr_id)
        with pytest.raises(ValueError, match="has not connected an actions role"):
            execute_change_request(session, cr, account)
