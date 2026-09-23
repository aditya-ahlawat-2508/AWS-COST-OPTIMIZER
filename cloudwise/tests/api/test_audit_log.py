from app.database import org_scoped_session
from app.models import AuditLog


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def test_audit_log_lists_org_entries_newest_first(client, make_clerk_token):
    token = make_clerk_token()
    org_id = _me(client, token)["org_id"]

    # Two separate transactions: Postgres's now() is constant within one
    # transaction, so inserting both rows in the same `with` block would give
    # them an identical created_at and make the ordering assertion flaky.
    with org_scoped_session(org_id=org_id) as session:
        session.add(AuditLog(org_id=org_id, action="first", details={}))
    with org_scoped_session(org_id=org_id) as session:
        session.add(AuditLog(org_id=org_id, action="second", details={}))

    resp = client.get("/audit-log", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    actions = [entry["action"] for entry in resp.json()]
    assert actions[0] == "second"
    assert actions[1] == "first"


def test_audit_log_is_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    org_a = _me(client, token_a)["org_id"]

    with org_scoped_session(org_id=org_a) as session:
        session.add(AuditLog(org_id=org_a, action="secret", details={}))

    resp_b = client.get("/audit-log", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.json() == []


def test_audit_log_requires_auth(client):
    resp = client.get("/audit-log")
    assert resp.status_code in (401, 403)
