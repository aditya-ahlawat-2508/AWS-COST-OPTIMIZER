from app.database import org_scoped_session
from app.models import AWSAccount, ChangeRequest, Finding


def _connect_account_and_finding(client, token):
    resp = client.post(
        "/accounts",
        json={
            "aws_account_id": "111111111111",
            "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
            "external_id": "ext-1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    org_id = me["org_id"]

    with org_scoped_session(org_id=org_id) as session:
        account = session.query(AWSAccount).filter_by(org_id=org_id).one()
        finding = Finding(
            org_id=org_id,
            account_id=account.id,
            rule_id="idle_ec2",
            resource_id="i-0123456789abcdef0",
            resource_type="ec2_instance",
            evidence={"fix": "Stop it."},
            monthly_savings=10.0,
            effort="low",
            risk="medium",
        )
        session.add(finding)
        session.flush()
        finding_id = str(finding.id)

    return org_id, finding_id


def test_owner_can_approve_pending_change_request(client, make_clerk_token):
    token = make_clerk_token(org_role="org:admin")  # first user in org -> owner regardless
    org_id, finding_id = _connect_account_and_finding(client, token)

    with org_scoped_session(org_id=org_id) as session:
        from app.models import User

        user = session.query(User).filter_by(org_id=org_id).one()
        cr = ChangeRequest(
            org_id=org_id, finding_id=finding_id, action_type="stop_ec2", requested_by=user.id, status="pending"
        )
        session.add(cr)
        session.flush()
        cr_id = str(cr.id)

    resp = client.post(f"/change-requests/{cr_id}/approve", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"


def test_viewer_cannot_approve_change_request(client, make_clerk_token):
    org_id_str = "org_viewer_test"
    owner_token = make_clerk_token(clerk_org_id=org_id_str, org_role="org:admin", email="owner@acmecorp.io")
    viewer_token = make_clerk_token(clerk_org_id=org_id_str, org_role="org:member", email="viewer@acmecorp.io")

    org_id, finding_id = _connect_account_and_finding(client, owner_token)
    # provision the viewer too
    client.get("/auth/me", headers={"Authorization": f"Bearer {viewer_token}"})

    with org_scoped_session(org_id=org_id) as session:
        from app.models import User

        owner = session.query(User).filter_by(org_id=org_id, role="owner").one()
        cr = ChangeRequest(
            org_id=org_id, finding_id=finding_id, action_type="stop_ec2", requested_by=owner.id, status="pending"
        )
        session.add(cr)
        session.flush()
        cr_id = str(cr.id)

    resp = client.post(f"/change-requests/{cr_id}/approve", headers={"Authorization": f"Bearer {viewer_token}"})
    assert resp.status_code == 403


def test_cannot_approve_already_approved_change_request(client, make_clerk_token):
    token = make_clerk_token()
    org_id, finding_id = _connect_account_and_finding(client, token)

    with org_scoped_session(org_id=org_id) as session:
        from app.models import User

        user = session.query(User).filter_by(org_id=org_id).one()
        cr = ChangeRequest(
            org_id=org_id, finding_id=finding_id, action_type="stop_ec2", requested_by=user.id, status="approved"
        )
        session.add(cr)
        session.flush()
        cr_id = str(cr.id)

    resp = client.post(f"/change-requests/{cr_id}/approve", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 409


def test_change_requests_are_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    org_id, finding_id = _connect_account_and_finding(client, token_a)

    with org_scoped_session(org_id=org_id) as session:
        from app.models import User

        user = session.query(User).filter_by(org_id=org_id).one()
        session.add(
            ChangeRequest(
                org_id=org_id, finding_id=finding_id, action_type="stop_ec2", requested_by=user.id, status="pending"
            )
        )

    resp_a = client.get("/change-requests", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/change-requests", headers={"Authorization": f"Bearer {token_b}"})
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 0
