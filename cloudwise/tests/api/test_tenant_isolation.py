def test_two_orgs_cannot_see_each_others_accounts(client, make_clerk_token):
    token_a = make_clerk_token(org_slug="acme-inc")
    token_b = make_clerk_token(org_slug="widget-co")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = client.post(
        "/accounts",
        json={
            "aws_account_id": "111111111111",
            "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
            "external_id": "ext-a",
            "label": "Acme prod",
        },
        headers=headers_a,
    )
    assert resp.status_code == 201, resp.text

    resp = client.post(
        "/accounts",
        json={
            "aws_account_id": "222222222222",
            "role_arn": "arn:aws:iam::222222222222:role/CloudWiseReadOnly",
            "external_id": "ext-b",
            "label": "Widget prod",
        },
        headers=headers_b,
    )
    assert resp.status_code == 201, resp.text

    accounts_a = client.get("/accounts", headers=headers_a).json()
    accounts_b = client.get("/accounts", headers=headers_b).json()

    assert [a["aws_account_id"] for a in accounts_a] == ["111111111111"]
    assert [a["aws_account_id"] for a in accounts_b] == ["222222222222"]


def test_same_org_multiple_users_share_data(client, make_clerk_token):
    same_org_id = "org_shared_acme"
    token_owner = make_clerk_token(clerk_org_id=same_org_id, org_role="org:admin", email="owner@acmecorp.io")
    token_member = make_clerk_token(clerk_org_id=same_org_id, org_role="org:member", email="member@acmecorp.io")

    client.post(
        "/accounts",
        json={
            "aws_account_id": "333333333333",
            "role_arn": "arn:aws:iam::333333333333:role/CloudWiseReadOnly",
            "external_id": "ext-c",
        },
        headers={"Authorization": f"Bearer {token_owner}"},
    )

    resp = client.get("/accounts", headers={"Authorization": f"Bearer {token_member}"})
    assert resp.status_code == 200
    assert [a["aws_account_id"] for a in resp.json()] == ["333333333333"]


def test_first_user_in_org_becomes_owner_later_members_default_to_viewer(client, make_clerk_token):
    org_id = "org_roles_test"
    token_first = make_clerk_token(clerk_org_id=org_id, org_role="org:admin")
    token_second = make_clerk_token(clerk_org_id=org_id, org_role="org:member", email="second@acmecorp.io")

    me_first = client.get("/auth/me", headers={"Authorization": f"Bearer {token_first}"}).json()
    me_second = client.get("/auth/me", headers={"Authorization": f"Bearer {token_second}"}).json()

    assert me_first["role"] == "owner"
    assert me_second["role"] == "viewer"
    assert me_first["org_id"] == me_second["org_id"]


def test_findings_are_also_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()

    resp_a = client.get("/findings", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/findings", headers={"Authorization": f"Bearer {token_b}"})

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json() == []
    assert resp_b.json() == []


def test_unauthenticated_requests_are_rejected(client):
    resp = client.get("/accounts")
    assert resp.status_code in (401, 403)


def test_token_without_active_organization_is_rejected(client, sign_raw_claims):
    import os

    # No org_id claim at all -> extract_identity must refuse it.
    token = sign_raw_claims({"sub": "user_no_org", "iss": os.environ["CLERK_ISSUER"]})
    resp = client.get("/accounts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_forged_signature_is_rejected(client):
    import jwt

    forged = jwt.encode({"sub": "user_x", "org_id": "org_x"}, "not-the-real-key", algorithm="HS256")
    resp = client.get("/accounts", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401
