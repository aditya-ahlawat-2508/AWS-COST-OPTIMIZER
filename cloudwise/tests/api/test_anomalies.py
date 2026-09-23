from datetime import date, timedelta

from app.database import org_scoped_session
from app.models import AWSAccount, SpendDaily


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def _seed_account(client, token):
    client.post(
        "/accounts",
        json={
            "aws_account_id": "111111111111",
            "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
            "external_id": "ext-1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    org_id = _me(client, token)["org_id"]
    with org_scoped_session(org_id=org_id) as session:
        account = session.query(AWSAccount).filter_by(org_id=org_id).one()
        return org_id, account.id


def test_anomalies_endpoint_flags_a_real_spike(client, make_clerk_token):
    token = make_clerk_token()
    org_id, account_id = _seed_account(client, token)

    today = date.today()
    with org_scoped_session(org_id=org_id) as session:
        for i in range(21):
            usage_date = today - timedelta(days=20 - i)
            cost = 50.0 if i >= 14 else 10.0  # last 7 days spike vs prior 14-day baseline
            session.add(
                SpendDaily(
                    org_id=org_id, account_id=account_id, usage_date=usage_date,
                    service="AmazonEC2-NatGateway", unblended_cost=cost, amortized_cost=cost,
                )
            )

    resp = client.get("/anomalies", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["service"] == "AmazonEC2-NatGateway"
    assert body[0]["baseline_daily_avg"] == 10.0
    assert body[0]["recent_daily_avg"] == 50.0


def test_anomalies_endpoint_returns_empty_for_stable_spend(client, make_clerk_token):
    token = make_clerk_token()
    org_id, account_id = _seed_account(client, token)

    today = date.today()
    with org_scoped_session(org_id=org_id) as session:
        for i in range(21):
            usage_date = today - timedelta(days=20 - i)
            session.add(
                SpendDaily(
                    org_id=org_id, account_id=account_id, usage_date=usage_date,
                    service="AmazonS3", unblended_cost=5.0, amortized_cost=5.0,
                )
            )

    resp = client.get("/anomalies", headers={"Authorization": f"Bearer {token}"})
    assert resp.json() == []


def test_anomalies_are_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    org_id, account_id = _seed_account(client, token_a)

    today = date.today()
    with org_scoped_session(org_id=org_id) as session:
        for i in range(21):
            usage_date = today - timedelta(days=20 - i)
            cost = 50.0 if i >= 14 else 10.0
            session.add(
                SpendDaily(
                    org_id=org_id, account_id=account_id, usage_date=usage_date,
                    service="AmazonEC2", unblended_cost=cost, amortized_cost=cost,
                )
            )

    resp_b = client.get("/anomalies", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.json() == []
