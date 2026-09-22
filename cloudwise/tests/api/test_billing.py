import uuid
from unittest.mock import MagicMock, patch

from app import billing
from app.database import org_scoped_session
from app.models import Organization, Subscription


def _make_org():
    with org_scoped_session(org_id=None) as session:
        org = Organization(name="Acme")
        session.add(org)
        session.flush()
        return org.id


def test_get_entitlement_defaults_to_free_with_no_subscription_row():
    org_id = _make_org()
    with org_scoped_session(org_id=str(org_id)) as session:
        entitlement = billing.get_entitlement(session, org_id)
    assert entitlement == {"tier": "free", "status": "active", "max_accounts": 1}


def test_get_entitlement_reflects_existing_subscription():
    org_id = _make_org()
    with org_scoped_session(org_id=str(org_id)) as session:
        session.add(Subscription(org_id=org_id, tier="growth", status="active"))

    with org_scoped_session(org_id=str(org_id)) as session:
        entitlement = billing.get_entitlement(session, org_id)
    assert entitlement == {"tier": "growth", "status": "active", "max_accounts": None}


@patch("app.billing.stripe")
def test_create_checkout_session_calls_stripe_with_org_metadata(mock_stripe):
    org_id = _make_org()
    mock_stripe.checkout.Session.create.return_value = MagicMock(url="https://checkout.stripe.com/session/xyz")

    with patch.dict(billing.STRIPE_PRICE_IDS, {"starter": "price_123"}):
        url = billing.create_checkout_session(org_id, "starter", "https://app/success", "https://app/cancel")

    assert url == "https://checkout.stripe.com/session/xyz"
    call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
    assert call_kwargs["metadata"] == {"org_id": str(org_id), "tier": "starter"}
    assert call_kwargs["line_items"] == [{"price": "price_123", "quantity": 1}]


def test_create_checkout_session_rejects_unconfigured_tier():
    org_id = _make_org()
    with patch.dict(billing.STRIPE_PRICE_IDS, {"starter": ""}):
        try:
            billing.create_checkout_session(org_id, "starter", "https://a", "https://b")
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_webhook_checkout_completed_creates_subscription():
    org_id = _make_org()
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_123",
                "subscription": "sub_123",
                "metadata": {"org_id": str(org_id), "tier": "starter"},
            }
        },
    }

    billing.handle_webhook_event(event)

    with org_scoped_session(org_id=str(org_id)) as session:
        sub = session.get(Subscription, org_id)
        assert sub.tier == "starter"
        assert sub.status == "active"
        assert sub.stripe_customer_id == "cus_123"


def test_webhook_subscription_updated_changes_status_by_customer_id():
    org_id = _make_org()
    with org_scoped_session(org_id=str(org_id)) as session:
        session.add(
            Subscription(org_id=org_id, tier="growth", status="active", stripe_customer_id="cus_456")
        )

    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"customer": "cus_456", "status": "past_due", "current_period_end": 1893456000}},
    }
    billing.handle_webhook_event(event)

    with org_scoped_session(org_id=str(org_id)) as session:
        sub = session.get(Subscription, org_id)
        assert sub.status == "past_due"


def test_webhook_subscription_deleted_reverts_to_free():
    org_id = _make_org()
    with org_scoped_session(org_id=str(org_id)) as session:
        session.add(Subscription(org_id=org_id, tier="growth", status="active", stripe_customer_id="cus_789"))

    event = {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_789"}}}
    billing.handle_webhook_event(event)

    with org_scoped_session(org_id=str(org_id)) as session:
        sub = session.get(Subscription, org_id)
        assert sub.tier == "free"
        assert sub.status == "canceled"


def test_webhook_for_unknown_customer_is_a_noop():
    event = {
        "type": "customer.subscription.updated",
        "data": {"object": {"customer": "cus_does_not_exist", "status": "active"}},
    }
    billing.handle_webhook_event(event)  # must not raise


def test_free_tier_account_limit_is_enforced(client, make_clerk_token):
    token = make_clerk_token()
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

    resp = client.post(
        "/accounts",
        json={
            "aws_account_id": "222222222222",
            "role_arn": "arn:aws:iam::222222222222:role/CloudWiseReadOnly",
            "external_id": "ext-2",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_growth_tier_has_no_account_limit(client, make_clerk_token):
    token = make_clerk_token()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    with org_scoped_session(org_id=me["org_id"]) as session:
        session.add(Subscription(org_id=uuid.UUID(me["org_id"]), tier="growth", status="active"))

    for i in range(3):
        resp = client.post(
            "/accounts",
            json={
                "aws_account_id": f"{i}11111111111",
                "role_arn": f"arn:aws:iam::{i}11111111111:role/CloudWiseReadOnly",
                "external_id": f"ext-{i}",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
