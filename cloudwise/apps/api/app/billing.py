"""Stripe billing + server-side entitlement checks (blueprint Section 09:
'entitlements checked server-side', Section 03's tier table). Razorpay for
INR customers is the other half of the blueprint's billing story but isn't
built yet — this module's shape (tier -> limits, an entitlement lookup the
rest of the app calls) is meant to have a second provider slot beside Stripe
later, not to be Stripe-specific by design.
"""
import datetime
import os
from typing import Any, Dict, Optional
from uuid import UUID

import stripe
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .database import org_scoped_session
from .models import Subscription

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

# None means unlimited. Matches the blueprint's Free/Starter/Growth table.
TIER_LIMITS = {
    "free": {"max_accounts": 1},
    "starter": {"max_accounts": 3},
    "growth": {"max_accounts": None},
}

STRIPE_PRICE_IDS = {
    "starter": os.environ.get("STRIPE_PRICE_STARTER", ""),
    "growth": os.environ.get("STRIPE_PRICE_GROWTH", ""),
}


def get_entitlement(db: Session, org_id: UUID) -> Dict[str, Any]:
    # No subscription row at all just means free tier — not an error state,
    # and true for every org until they first check out.
    sub = db.get(Subscription, org_id)
    tier = sub.tier if sub else "free"
    sub_status = sub.status if sub else "active"
    return {"tier": tier, "status": sub_status, "max_accounts": TIER_LIMITS[tier]["max_accounts"]}


def create_checkout_session(org_id: UUID, tier: str, success_url: str, cancel_url: str) -> str:
    price_id = STRIPE_PRICE_IDS.get(tier)
    if not price_id:
        raise ValueError(f"No Stripe price is configured for tier '{tier}'")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(org_id),
        metadata={"org_id": str(org_id), "tier": tier},
    )
    return session.url


def handle_webhook_event(event: Dict[str, Any]) -> None:
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _apply_checkout_completed(obj)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _apply_subscription_change(event_type, obj)
    # Other event types (invoice.*, etc.) are deliberately ignored for now.


def _apply_checkout_completed(session_obj: Dict[str, Any]) -> None:
    org_id = UUID(session_obj["metadata"]["org_id"])
    tier = session_obj["metadata"]["tier"]

    with org_scoped_session(org_id=str(org_id)) as db:
        sub = db.get(Subscription, org_id)
        if sub is None:
            sub = Subscription(org_id=org_id)
            db.add(sub)
        sub.tier = tier
        sub.status = "active"
        sub.stripe_customer_id = session_obj.get("customer")
        sub.stripe_subscription_id = session_obj.get("subscription")
        sub.updated_at = datetime.datetime.utcnow()


def _apply_subscription_change(event_type: str, subscription_obj: Dict[str, Any]) -> None:
    customer_id = subscription_obj["customer"]

    # Same bootstrap problem as login: this event only carries a
    # stripe_customer_id, not our org_id, so the lookup has to run before
    # org context is known — see db/init.sql's allow_billing_lookup policy.
    with org_scoped_session(org_id=None, allow_billing_lookup=True) as db:
        sub = db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        ).scalar_one_or_none()
        if sub is None:
            return  # unknown customer id; nothing in our DB to update

        db.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(sub.org_id)})

        if event_type == "customer.subscription.deleted":
            sub.status = "canceled"
            sub.tier = "free"
        else:
            sub.status = subscription_obj.get("status", sub.status)
            period_end = subscription_obj.get("current_period_end")
            if period_end:
                sub.current_period_end = datetime.datetime.utcfromtimestamp(period_end)
        sub.updated_at = datetime.datetime.utcnow()
