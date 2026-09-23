import hashlib
import hmac
from unittest.mock import MagicMock, patch

from app import billing_razorpay
from app.database import org_scoped_session
from app.models import Organization, Subscription


def _make_org():
    with org_scoped_session(org_id=None) as session:
        org = Organization(name="Acme")
        session.add(org)
        session.flush()
        return org.id


def test_create_subscription_link_calls_razorpay_with_org_notes():
    org_id = _make_org()
    fake_http = MagicMock()
    fake_http.post.return_value = MagicMock(
        json=lambda: {"short_url": "https://rzp.io/i/abc123"},
        raise_for_status=lambda: None,
    )

    with patch.dict(billing_razorpay.RAZORPAY_PLAN_IDS, {"starter": "plan_123"}), patch.object(
        billing_razorpay, "RAZORPAY_KEY_ID", "rzp_test_key"
    ), patch.object(billing_razorpay, "RAZORPAY_KEY_SECRET", "rzp_test_secret"):
        url = billing_razorpay.create_subscription_link(org_id, "starter", http_client=fake_http)

    assert url == "https://rzp.io/i/abc123"
    call_kwargs = fake_http.post.call_args.kwargs
    assert call_kwargs["json"]["notes"] == {"org_id": str(org_id), "tier": "starter"}
    assert call_kwargs["json"]["plan_id"] == "plan_123"


def test_create_subscription_link_rejects_unconfigured_tier():
    org_id = _make_org()
    with patch.dict(billing_razorpay.RAZORPAY_PLAN_IDS, {"starter": ""}):
        try:
            billing_razorpay.create_subscription_link(org_id, "starter", http_client=MagicMock())
            assert False, "expected ValueError"
        except ValueError:
            pass


def test_verify_webhook_signature_accepts_correct_hmac():
    payload = b'{"event": "subscription.activated"}'
    with patch.object(billing_razorpay, "RAZORPAY_WEBHOOK_SECRET", "whsec_test"):
        expected = hmac.new(b"whsec_test", payload, hashlib.sha256).hexdigest()
        assert billing_razorpay.verify_webhook_signature(payload, expected) is True


def test_verify_webhook_signature_rejects_wrong_signature():
    payload = b'{"event": "subscription.activated"}'
    with patch.object(billing_razorpay, "RAZORPAY_WEBHOOK_SECRET", "whsec_test"):
        assert billing_razorpay.verify_webhook_signature(payload, "not-the-real-signature") is False


def test_webhook_subscription_activated_creates_subscription():
    org_id = _make_org()
    event = {
        "event": "subscription.activated",
        "payload": {
            "subscription": {
                "entity": {"id": "sub_abc123", "notes": {"org_id": str(org_id), "tier": "growth"}}
            }
        },
    }

    billing_razorpay.handle_webhook_event(event)

    with org_scoped_session(org_id=str(org_id)) as session:
        sub = session.get(Subscription, org_id)
        assert sub.tier == "growth"
        assert sub.status == "active"
        assert sub.provider == "razorpay"
        assert sub.razorpay_subscription_id == "sub_abc123"


def test_webhook_subscription_cancelled_reverts_to_free():
    org_id = _make_org()
    with org_scoped_session(org_id=str(org_id)) as session:
        session.add(
            Subscription(org_id=org_id, tier="growth", status="active", provider="razorpay",
                         razorpay_subscription_id="sub_xyz789")
        )

    event = {
        "event": "subscription.cancelled",
        "payload": {"subscription": {"entity": {"id": "sub_xyz789"}}},
    }
    billing_razorpay.handle_webhook_event(event)

    with org_scoped_session(org_id=str(org_id)) as session:
        sub = session.get(Subscription, org_id)
        assert sub.tier == "free"
        assert sub.status == "canceled"


def test_webhook_for_unknown_subscription_is_a_noop():
    event = {
        "event": "subscription.cancelled",
        "payload": {"subscription": {"entity": {"id": "sub_does_not_exist"}}},
    }
    billing_razorpay.handle_webhook_event(event)  # must not raise


def test_stripe_and_razorpay_subscriptions_do_not_collide():
    # An org billed by Stripe first, then somehow hit by a stray Razorpay
    # webhook for a different org, must not affect the Stripe one.
    org_a = _make_org()
    org_b = _make_org()

    with org_scoped_session(org_id=str(org_a)) as session:
        session.add(Subscription(org_id=org_a, tier="starter", status="active", provider="stripe",
                                  stripe_customer_id="cus_a"))
    with org_scoped_session(org_id=str(org_b)) as session:
        session.add(Subscription(org_id=org_b, tier="growth", status="active", provider="razorpay",
                                  razorpay_subscription_id="sub_b"))

    billing_razorpay.handle_webhook_event(
        {"event": "subscription.cancelled", "payload": {"subscription": {"entity": {"id": "sub_b"}}}}
    )

    with org_scoped_session(org_id=str(org_a)) as session:
        assert session.get(Subscription, org_a).tier == "starter"
    with org_scoped_session(org_id=str(org_b)) as session:
        assert session.get(Subscription, org_b).tier == "free"
