from app.database import org_scoped_session
from app.models import AWSAccount, Finding


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def _seed_finding(client, token):
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
        finding = Finding(
            org_id=org_id, account_id=account.id, rule_id="idle_ec2", resource_id="i-abc123",
            resource_type="ec2_instance", evidence={"fix": "Stop it."}, monthly_savings=10.0,
            effort="low", risk="medium",
        )
        session.add(finding)
        session.flush()
        return str(finding.id)


def test_get_finding_by_id(client, make_clerk_token):
    token = make_clerk_token()
    finding_id = _seed_finding(client, token)

    resp = client.get(f"/findings/{finding_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["resource_id"] == "i-abc123"


def test_get_finding_returns_404_for_unknown_id(client, make_clerk_token):
    token = make_clerk_token()
    resp = client.get(
        "/findings/00000000-0000-0000-0000-000000000000", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


def test_get_finding_returns_404_for_other_orgs_finding(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    finding_id = _seed_finding(client, token_a)

    resp = client.get(f"/findings/{finding_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
