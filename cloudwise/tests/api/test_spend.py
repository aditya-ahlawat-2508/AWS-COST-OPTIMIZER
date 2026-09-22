from datetime import date

from app.database import org_scoped_session
from app.models import AWSAccount, SpendDaily


def _connect_account_and_seed_spend(client, token, aws_account_id: str):
    resp = client.post(
        "/accounts",
        json={
            "aws_account_id": aws_account_id,
            "role_arn": f"arn:aws:iam::{aws_account_id}:role/CloudWiseReadOnly",
            "external_id": "ext-1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    org_id = me["org_id"]

    with org_scoped_session(org_id=org_id) as session:
        account = session.query(AWSAccount).filter_by(org_id=org_id, aws_account_id=aws_account_id).one()
        session.add(
            SpendDaily(
                org_id=org_id,
                account_id=account.id,
                usage_date=date(2026, 9, 1),
                service="AmazonEC2",
                unblended_cost=10.0,
                amortized_cost=8.0,
                currency="USD",
            )
        )
        session.add(
            SpendDaily(
                org_id=org_id,
                account_id=account.id,
                usage_date=date(2026, 9, 1),
                service="AmazonS3",
                unblended_cost=5.0,
                amortized_cost=5.0,
                currency="USD",
            )
        )
    return org_id


def test_spend_grouped_by_service(client, make_clerk_token):
    token = make_clerk_token()
    _connect_account_and_seed_spend(client, token, "111111111111")

    resp = client.get(
        "/spend",
        params={"group_by": "service", "start_date": "2026-08-01", "end_date": "2026-09-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_cost"] == 15.0
    by_service = {b["key"]: b["cost"] for b in body["breakdown"]}
    assert by_service == {"AmazonEC2": 10.0, "AmazonS3": 5.0}


def test_spend_amortized_view(client, make_clerk_token):
    token = make_clerk_token()
    _connect_account_and_seed_spend(client, token, "222222222222")

    resp = client.get(
        "/spend",
        params={"view": "amortized", "start_date": "2026-08-01", "end_date": "2026-09-30"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["total_cost"] == 13.0


def test_spend_is_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    _connect_account_and_seed_spend(client, token_a, "333333333333")

    resp = client.get(
        "/spend",
        params={"start_date": "2026-08-01", "end_date": "2026-09-30"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.json()["total_cost"] == 0.0
