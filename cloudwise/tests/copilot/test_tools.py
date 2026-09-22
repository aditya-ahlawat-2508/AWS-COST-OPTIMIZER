import uuid

from app.database import org_scoped_session
from app.models import AWSAccount, ChangeRequest, Finding, Organization
from services.copilot import tools


def _make_org_account_and_finding(rule_id="idle_ec2", monthly_savings=7.6):
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

        finding = Finding(
            org_id=org_id,
            account_id=account.id,
            rule_id=rule_id,
            resource_id="i-0123456789abcdef0",
            resource_type="ec2_instance",
            evidence={"fix": "Stop the instance."},
            monthly_savings=monthly_savings,
            effort="low",
            risk="medium",
        )
        session.add(finding)
        session.flush()
        finding_id = finding.id

    return org_id, finding_id


def test_list_findings_returns_org_data():
    org_id, finding_id = _make_org_account_and_finding()
    with org_scoped_session(org_id=str(org_id)) as session:
        results = tools.list_findings(session, org_id)
    assert len(results) == 1
    assert results[0]["id"] == str(finding_id)
    assert results[0]["monthly_savings"] == 7.6


def test_list_findings_filters_by_status():
    org_id, _finding_id = _make_org_account_and_finding()
    with org_scoped_session(org_id=str(org_id)) as session:
        assert tools.list_findings(session, org_id, status="dismissed") == []
        assert len(tools.list_findings(session, org_id, status="open")) == 1


def test_get_resource_returns_finding_details():
    org_id, _finding_id = _make_org_account_and_finding()
    with org_scoped_session(org_id=str(org_id)) as session:
        resource = tools.get_resource(session, org_id, "i-0123456789abcdef0")
    assert resource is not None
    assert resource["aws_account_id"] == "111111111111"
    assert resource["finding"]["monthly_savings"] == 7.6


def test_get_resource_returns_none_for_unknown_id():
    org_id, _finding_id = _make_org_account_and_finding()
    with org_scoped_session(org_id=str(org_id)) as session:
        assert tools.get_resource(session, org_id, "i-doesnotexist") is None


def test_propose_change_creates_pending_change_request():
    org_id, finding_id = _make_org_account_and_finding(rule_id="idle_ec2")
    with org_scoped_session(org_id=str(org_id)) as session:
        # requested_by needs a real user row (FK constraint)
        from app.models import User

        user = User(org_id=org_id, clerk_user_id="user_1", email="a@acmecorp.io", role="owner")
        session.add(user)
        session.flush()
        user_id = user.id

        result = tools.propose_change(session, org_id, user_id, str(finding_id))

    assert "change_request_id" in result
    assert result["action_type"] == "stop_ec2"
    assert result["status"] == "pending"

    with org_scoped_session(org_id=str(org_id)) as session:
        cr = session.get(ChangeRequest, uuid.UUID(result["change_request_id"]))
        assert cr.status == "pending"
        assert cr.rollback_plan == "Stop the instance."


def test_propose_change_rejects_unknown_finding():
    org_id, _finding_id = _make_org_account_and_finding()
    with org_scoped_session(org_id=str(org_id)) as session:
        from app.models import User

        user = User(org_id=org_id, clerk_user_id="user_2", email="b@acmecorp.io", role="owner")
        session.add(user)
        session.flush()
        result = tools.propose_change(session, org_id, user.id, "00000000-0000-0000-0000-000000000000")
    assert "error" in result


def test_propose_change_rejects_finding_from_another_org():
    org_a_id, finding_id = _make_org_account_and_finding()
    org_b_id, _ = _make_org_account_and_finding()

    with org_scoped_session(org_id=str(org_b_id)) as session:
        from app.models import User

        user = User(org_id=org_b_id, clerk_user_id="user_3", email="c@acmecorp.io", role="owner")
        session.add(user)
        session.flush()
        # Even though this finding_id is real, it belongs to org_a, and this
        # session is scoped to org_b — RLS means the .get() inside
        # propose_change simply won't find it.
        result = tools.propose_change(session, org_b_id, user.id, str(finding_id))
    assert "error" in result


def test_propose_change_rejects_rule_with_no_automated_action():
    org_id, finding_id = _make_org_account_and_finding(rule_id="s3_no_lifecycle")
    with org_scoped_session(org_id=str(org_id)) as session:
        from app.models import User

        user = User(org_id=org_id, clerk_user_id="user_4", email="d@acmecorp.io", role="owner")
        session.add(user)
        session.flush()
        result = tools.propose_change(session, org_id, user.id, str(finding_id))
    assert "error" in result
    assert "no automated action" in result["error"].lower()
