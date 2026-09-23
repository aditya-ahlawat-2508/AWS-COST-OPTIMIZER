def test_razorpay_checkout_returns_503_when_unconfigured(client, make_clerk_token, monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
    token = make_clerk_token()
    resp = client.post(
        "/billing/razorpay/checkout", json={"tier": "starter"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code in (400, 503)


def test_razorpay_checkout_requires_auth(client):
    resp = client.post("/billing/razorpay/checkout", json={"tier": "starter"})
    assert resp.status_code in (401, 403)


def test_razorpay_webhook_rejects_bad_signature(client):
    resp = client.post(
        "/billing/razorpay/webhook",
        content=b'{"event": "subscription.activated"}',
        headers={"x-razorpay-signature": "bogus"},
    )
    assert resp.status_code == 400
