def _register(client, org_name: str, email: str, password: str = "supersecret123") -> str:
    resp = client.post("/auth/register", json={"org_name": org_name, "email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def test_two_orgs_cannot_see_each_others_accounts(client):
    token_a = _register(client, "Acme Inc", "owner@acmecorp.io")
    token_b = _register(client, "Widget Co", "owner@widgetco.io")

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


def test_findings_are_also_org_scoped(client):
    token_a = _register(client, "Acme Inc", "findings-a@acmecorp.io")
    token_b = _register(client, "Widget Co", "findings-b@widgetco.io")

    resp_a = client.get("/findings", headers={"Authorization": f"Bearer {token_a}"})
    resp_b = client.get("/findings", headers={"Authorization": f"Bearer {token_b}"})

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json() == []
    assert resp_b.json() == []


def test_duplicate_email_registration_is_rejected(client):
    _register(client, "Acme Inc", "dupe@acmecorp.io")
    resp = client.post(
        "/auth/register",
        json={"org_name": "Someone Else", "email": "dupe@acmecorp.io", "password": "anotherpassword"},
    )
    assert resp.status_code == 409


def test_login_rejects_wrong_password(client):
    _register(client, "Acme Inc", "owner2@acmecorp.io", password="correcthorsebattery")
    resp = client.post("/auth/login", json={"email": "owner2@acmecorp.io", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_succeeds_with_correct_password(client):
    _register(client, "Acme Inc", "owner3@acmecorp.io", password="correcthorsebattery")
    resp = client.post("/auth/login", json={"email": "owner3@acmecorp.io", "password": "correcthorsebattery"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_unauthenticated_requests_are_rejected(client):
    resp = client.get("/accounts")
    assert resp.status_code in (401, 403)


def test_forged_token_for_unknown_org_is_rejected(client):
    import jwt

    from app.config import settings

    fake_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "org_id": "00000000-0000-0000-0000-000000000000"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    resp = client.get("/accounts", headers={"Authorization": f"Bearer {fake_token}"})
    assert resp.status_code == 401
