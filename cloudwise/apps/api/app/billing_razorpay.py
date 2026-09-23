"""Razorpay billing for INR customers — the other half of the blueprint's
billing story (Section 03: "Stripe for USD customers; Razorpay for INR").
Mirrors app/billing.py's shape (checkout/subscription-link creation +
webhook handling updating the same subscriptions table) rather than
introducing a parallel data model; provider distinguishes which one billed
an org last.

Uses plain HTTP (Razorpay's REST API + HMAC-signed webhooks) instead of the
razorpay SDK — one dependency to test against rather than two payment SDKs.
"""
import hashlib
import hmac
import os
from typing import Any, Dict
from uuid import UUID

import requests

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_API_BASE = "https://api.razorpay.com/v1"

RAZORPAY_PLAN_IDS = {
    "starter": os.environ.get("RAZORPAY_PLAN_STARTER", ""),
    "growth": os.environ.get("RAZORPAY_PLAN_GROWTH", ""),
}


def create_subscription_link(org_id: UUID, tier: str, http_client=requests) -> str:
    plan_id = RAZORPAY_PLAN_IDS.get(tier)
    if not plan_id:
        raise ValueError(f"No Razorpay plan is configured for tier '{tier}'")
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError("RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are not configured")

    response = http_client.post(
        f"{RAZORPAY_API_BASE}/subscriptions",
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        json={
            "plan_id": plan_id,
            "customer_notify": 1,
            "total_count": 12,
            "notes": {"org_id": str(org_id), "tier": tier},
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["short_url"]


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_webhook_event(event: Dict[str, Any]) -> None:
    event_type = event.get("event")
    if event_type == "subscription.activated":
        _apply_subscription_activated(event["payload"]["subscription"]["entity"])
    elif event_type in ("subscription.cancelled", "subscription.completed"):
        _apply_subscription_ended(event["payload"]["subscription"]["entity"])
    # Other event types (subscription.charged, payment.failed, etc.) are
    # deliberately ignored for now, same as the Stripe side.


def _apply_subscription_activated(subscription_entity: Dict[str, Any]) -> None:
    from .database import org_scoped_session
    from .models import Subscription

    notes = subscription_entity.get("notes", {})
    org_id = UUID(notes["org_id"])
    tier = notes["tier"]

    with org_scoped_session(org_id=str(org_id)) as db:
        sub = db.get(Subscription, org_id)
        if sub is None:
            sub = Subscription(org_id=org_id)
            db.add(sub)
        sub.tier = tier
        sub.status = "active"
        sub.provider = "razorpay"
        sub.razorpay_subscription_id = subscription_entity["id"]


def _apply_subscription_ended(subscription_entity: Dict[str, Any]) -> None:
    from sqlalchemy import select, text

    from .database import org_scoped_session
    from .models import Subscription

    razorpay_subscription_id = subscription_entity["id"]

    # Same bootstrap problem as the Stripe side and login: this event only
    # carries a razorpay_subscription_id, not our org_id.
    with org_scoped_session(org_id=None, allow_billing_lookup=True) as db:
        sub = db.execute(
            select(Subscription).where(Subscription.razorpay_subscription_id == razorpay_subscription_id)
        ).scalar_one_or_none()
        if sub is None:
            return

        db.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(sub.org_id)})
        sub.status = "canceled"
        sub.tier = "free"
