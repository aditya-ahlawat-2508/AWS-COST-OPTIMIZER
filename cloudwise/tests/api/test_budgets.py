from datetime import date

from app.database import org_scoped_session
from app.models import AWSAccount, SpendDaily, Subscription


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def test_create_and_list_org_wide_budget(client, make_clerk_token):
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/budgets", json={"name": "Overall", "monthly_limit_usd": 500}, headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["spent_this_month"] == 0.0

    resp = client.get("/budgets", headers=headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Overall"


def test_budget_spent_this_month_sums_current_month_spend(client, make_clerk_token):
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/accounts",
        json={
            "aws_account_id": "111111111111",
            "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
            "external_id": "ext-1",
        },
        headers=headers,
    )
    org_id = _me(client, token)["org_id"]

    with org_scoped_session(org_id=org_id) as session:
        account = session.query(AWSAccount).filter_by(org_id=org_id).one()
        today = date.today().replace(day=1)
        session.add(
            SpendDaily(
                org_id=org_id, account_id=account.id, usage_date=today, service="AmazonEC2",
                unblended_cost=42.0, amortized_cost=42.0,
            )
        )

    resp = client.post("/budgets", json={"name": "Overall", "monthly_limit_usd": 500}, headers=headers)
    assert resp.json()["spent_this_month"] == 42.0


def test_budget_scoped_to_one_account_ignores_other_accounts_spend(client, make_clerk_token):
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}

    org_id_bootstrap = _me(client, token)["org_id"]
    with org_scoped_session(org_id=org_id_bootstrap) as session:
        # Free tier caps at 1 connected account; this test needs two.
        session.add(Subscription(org_id=org_id_bootstrap, tier="growth", status="active"))

    for aws_id in ["111111111111", "222222222222"]:
        client.post(
            "/accounts",
            json={
                "aws_account_id": aws_id,
                "role_arn": f"arn:aws:iam::{aws_id}:role/CloudWiseReadOnly",
                "external_id": "ext-1",
            },
            headers=headers,
        )
    org_id = _me(client, token)["org_id"]

    with org_scoped_session(org_id=org_id) as session:
        accounts = {a.aws_account_id: a for a in session.query(AWSAccount).filter_by(org_id=org_id).all()}
        today = date.today().replace(day=1)
        session.add(
            SpendDaily(
                org_id=org_id, account_id=accounts["111111111111"].id, usage_date=today,
                service="AmazonEC2", unblended_cost=10.0, amortized_cost=10.0,
            )
        )
        session.add(
            SpendDaily(
                org_id=org_id, account_id=accounts["222222222222"].id, usage_date=today,
                service="AmazonEC2", unblended_cost=99.0, amortized_cost=99.0,
            )
        )
        scoped_account_id = str(accounts["111111111111"].id)

    resp = client.post(
        "/budgets",
        json={"name": "acme-prod only", "monthly_limit_usd": 100, "account_id": scoped_account_id},
        headers=headers,
    )
    assert resp.json()["spent_this_month"] == 10.0


def test_budgets_are_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    client.post("/budgets", json={"name": "A's budget", "monthly_limit_usd": 100},
                headers={"Authorization": f"Bearer {token_a}"})

    resp_b = client.get("/budgets", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.json() == []
