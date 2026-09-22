import os


def test_copilot_chat_returns_503_when_unconfigured(client, make_clerk_token, monkeypatch):
    # No ANTHROPIC_API_KEY in this environment -> anthropic.Anthropic() itself
    # raises, and the route must turn that into a clean 503, not a 500.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    token = make_clerk_token()
    resp = client.post(
        "/copilot/chat", json={"message": "hi"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 503


def test_copilot_chat_requires_auth(client):
    resp = client.post("/copilot/chat", json={"message": "hi"})
    assert resp.status_code in (401, 403)


def test_copilot_chat_rejects_empty_message(client, make_clerk_token):
    token = make_clerk_token()
    resp = client.post("/copilot/chat", json={"message": ""}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422
