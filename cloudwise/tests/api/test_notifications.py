from unittest.mock import patch

from app.database import org_scoped_session
from app.models import AWSAccount, Finding, SpendDaily
from datetime import date


def _me(client, token):
    return client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()


def test_get_slack_settings_defaults_to_none(client, make_clerk_token):
    token = make_clerk_token()
    resp = client.get("/notifications/slack", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["slack_webhook_url"] is None


def test_set_and_get_slack_webhook(client, make_clerk_token):
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(
        "/notifications/slack", json={"slack_webhook_url": "https://hooks.slack.com/services/x"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["slack_webhook_url"] == "https://hooks.slack.com/services/x"

    resp = client.get("/notifications/slack", headers=headers)
    assert resp.json()["slack_webhook_url"] == "https://hooks.slack.com/services/x"


def test_send_digest_without_webhook_returns_400(client, make_clerk_token):
    token = make_clerk_token()
    resp = client.post("/notifications/slack/send-digest", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@patch("services.notifications.digest.send_slack_message")
def test_send_digest_with_webhook_configured(mock_send, client, make_clerk_token):
    mock_send.return_value = True
    token = make_clerk_token()
    headers = {"Authorization": f"Bearer {token}"}

    client.put("/notifications/slack", json={"slack_webhook_url": "https://hooks.slack.com/services/x"}, headers=headers)
    client.post(
        "/accounts",
        json={"aws_account_id": "111111111111", "role_arn": "arn:aws:iam::111111111111:role/CloudWiseReadOnly",
              "external_id": "ext-1"},
        headers=headers,
    )
    org_id = _me(client, token)["org_id"]
    with org_scoped_session(org_id=org_id) as session:
        account = session.query(AWSAccount).filter_by(org_id=org_id).one()
        session.add(
            Finding(org_id=org_id, account_id=account.id, rule_id="idle_ec2", resource_id="i-x",
                    resource_type="ec2_instance", evidence={}, monthly_savings=10.0, effort="low", risk="low")
        )
        session.add(
            SpendDaily(org_id=org_id, account_id=account.id, usage_date=date.today(), service="AmazonEC2",
                       unblended_cost=5.0, amortized_cost=5.0)
        )

    resp = client.post("/notifications/slack/send-digest", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["sent"] is True
    assert mock_send.call_count == 1
    sent_text = mock_send.call_args.args[1]
    assert "i-x" in sent_text


def test_notifications_are_org_scoped(client, make_clerk_token):
    token_a = make_clerk_token()
    token_b = make_clerk_token()
    client.put(
        "/notifications/slack", json={"slack_webhook_url": "https://hooks.slack.com/services/a"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_b = client.get("/notifications/slack", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.json()["slack_webhook_url"] is None
