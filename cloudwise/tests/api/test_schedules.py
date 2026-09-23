from app.database import org_scoped_session
from app.models import AWSAccount


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def _connect_account(client, token):
    resp = client.post(
        "/accounts",
        json={
            "aws_account_id": "111111111111",
            "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
            "external_id": "ext-1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


def test_create_and_list_schedule(client, make_clerk_token):
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}
    account_id = _connect_account(client, token)

    resp = client.post(
        "/schedules",
        json={
            "account_id": account_id,
            "resource_id": "i-0123456789abcdef0",
            "start_hour": 9,
            "stop_hour": 18,
            "weekdays_only": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    resp = client.get("/schedules", headers=headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["resource_id"] == "i-0123456789abcdef0"


def test_create_schedule_rejects_invalid_hour_window(client, make_clerk_token):
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}
    account_id = _connect_account(client, token)

    resp = client.post(
        "/schedules",
        json={"account_id": account_id, "resource_id": "i-x", "start_hour": 18, "stop_hour": 9},
        headers=headers,
    )
    assert resp.status_code == 422


def test_delete_schedule(client, make_clerk_token):
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}
    account_id = _connect_account(client, token)

    resp = client.post(
        "/schedules",
        json={"account_id": account_id, "resource_id": "i-x", "start_hour": 9, "stop_hour": 18},
        headers=headers,
    )
    schedule_id = resp.json()["id"]

    resp = client.delete(f"/schedules/{schedule_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get("/schedules", headers=headers)
    assert resp.json() == []


def test_schedules_are_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    account_id = _connect_account(client, token_a)

    client.post(
        "/schedules",
        json={"account_id": account_id, "resource_id": "i-x", "start_hour": 9, "stop_hour": 18},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    resp_b = client.get("/schedules", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.json() == []


def test_run_schedules_now_with_no_schedules_is_a_noop(client, make_clerk_token):
    token = make_clerk_token()
    resp = client.post("/schedules/run", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {"evaluated": 0, "actions_taken": 0}
