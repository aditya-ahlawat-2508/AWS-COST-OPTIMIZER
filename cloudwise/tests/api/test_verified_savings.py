import datetime

from app.database import org_scoped_session
from app.models import AWSAccount, ChangeRequest, Finding, SpendDaily, User


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def _seed_executed_change_request(client, token, executed_at):
    client.post(
        "/accounts",
        json={"aws_account_id": "111111111111", "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
              "external_id": "ext-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = _me(client, token)["org_id"]

    with org_scoped_session(org_id=org_id) as session:
        account = session.query(AWSAccount).filter_by(org_id=org_id).one()
        user = session.query(User).filter_by(org_id=org_id).one()

        finding = Finding(
            org_id=org_id, account_id=account.id, rule_id="idle_ec2", resource_id="i-abc123",
            resource_type="ec2_instance", evidence={}, monthly_savings=50.0, effort="low", risk="medium",
            status="done",
        )
        session.add(finding)
        session.flush()

        executed_date = executed_at.date()
        for i in range(7):
            session.add(SpendDaily(
                org_id=org_id, account_id=account.id, service="AmazonEC2",
                usage_date=executed_date - datetime.timedelta(days=7 - i),
                unblended_cost=10.0, amortized_cost=10.0,
            ))
            session.add(SpendDaily(
                org_id=org_id, account_id=account.id, service="AmazonEC2",
                usage_date=executed_date + datetime.timedelta(days=i),
                unblended_cost=4.0, amortized_cost=4.0,
            ))

        cr = ChangeRequest(
            org_id=org_id, finding_id=finding.id, action_type="stop_ec2", requested_by=user.id,
            approved_by=user.id, status="executed", executed_at=executed_at,
        )
        session.add(cr)
        session.flush()
        return str(cr.id)


def test_verified_savings_shows_a_real_drop(client, make_clerk_token):
    token = make_clerk_token()
    executed_at = datetime.datetime.utcnow() - datetime.timedelta(days=3)
    cr_id = _seed_executed_change_request(client, token, executed_at)

    resp = client.get(f"/change-requests/{cr_id}/verified-savings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["before_daily_avg"] == 10.0
    assert body["after_daily_avg"] == 4.0
    assert body["verified_monthly_savings"] == 180.0


def test_verified_savings_rejects_non_executed_change_request(client, make_clerk_token):
    token = make_clerk_token()
    client.post(
        "/accounts",
        json={"aws_account_id": "111111111111", "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
              "external_id": "ext-1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = _me(client, token)["org_id"]
    with org_scoped_session(org_id=org_id) as session:
        account = session.query(AWSAccount).filter_by(org_id=org_id).one()
        user = session.query(User).filter_by(org_id=org_id).one()
        finding = Finding(
            org_id=org_id, account_id=account.id, rule_id="idle_ec2", resource_id="i-x",
            resource_type="ec2_instance", evidence={}, monthly_savings=10.0, effort="low", risk="low",
        )
        session.add(finding)
        session.flush()
        cr = ChangeRequest(
            org_id=org_id, finding_id=finding.id, action_type="stop_ec2", requested_by=user.id, status="pending",
        )
        session.add(cr)
        session.flush()
        cr_id = str(cr.id)

    resp = client.get(f"/change-requests/{cr_id}/verified-savings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 409


def test_verified_savings_returns_404_for_unknown_change_request(client, make_clerk_token):
    token = make_clerk_token()
    resp = client.get(
        "/change-requests/00000000-0000-0000-0000-000000000000/verified-savings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
