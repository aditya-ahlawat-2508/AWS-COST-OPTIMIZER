from demo.seed_demo import ACCOUNTS, FINDINGS, seed


def test_seed_demo_is_idempotent_and_creates_expected_counts(client):
    seed()
    seed()  # re-running must not duplicate or crash

    resp = client.get("/demo/accounts")
    assert resp.status_code == 200
    assert len(resp.json()) == len(ACCOUNTS)

    resp = client.get("/demo/findings")
    assert resp.status_code == 200
    assert len(resp.json()) == len(FINDINGS)


def test_demo_endpoints_require_no_auth(client):
    seed()
    resp = client.get("/demo/spend")
    assert resp.status_code == 200
    assert resp.json()["total_cost"] > 0


def test_demo_endpoints_do_not_expose_write_actions(client):
    # There should be no POST route under /demo at all.
    from app.main import app

    demo_routes = [r for r in app.routes if getattr(r, "path", "").startswith("/demo")]
    for route in demo_routes:
        assert "POST" not in route.methods
        assert "DELETE" not in route.methods
        assert "PUT" not in route.methods


def test_demo_findings_include_realized_and_open_status(client):
    seed()
    resp = client.get("/demo/findings")
    statuses = {f["status"] for f in resp.json()}
    assert "done" in statuses
    assert "open" in statuses
