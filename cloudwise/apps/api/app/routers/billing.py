import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import billing, billing_razorpay
from ..deps import get_current_user, get_db
from ..models import User
from ..schemas import CheckoutRequest, CheckoutResponse, EntitlementOut, RazorpayCheckoutRequest

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/entitlement", response_model=EntitlementOut)
def get_entitlement(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EntitlementOut:
    return EntitlementOut(**billing.get_entitlement(db, user.org_id))


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest, user: User = Depends(get_current_user)) -> CheckoutResponse:
    try:
        url = billing.create_checkout_session(user.org_id, payload.tier, payload.success_url, payload.cancel_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Billing is not configured: {exc}"
        )
    return CheckoutResponse(checkout_url=url)


@router.post("/webhook", include_in_schema=False)
async def webhook(request: Request) -> dict:
    # Deliberately no Clerk auth dependency here — Stripe calls this
    # endpoint directly, and it authenticates itself via the signature below,
    # not a user's session token.
    import stripe

    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe webhook signature")

    billing.handle_webhook_event(event)
    return {"received": True}


@router.post("/razorpay/checkout", response_model=CheckoutResponse)
def razorpay_checkout(payload: RazorpayCheckoutRequest, user: User = Depends(get_current_user)) -> CheckoutResponse:
    try:
        url = billing_razorpay.create_subscription_link(user.org_id, payload.tier)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Razorpay billing is not configured: {exc}"
        )
    return CheckoutResponse(checkout_url=url)


@router.post("/razorpay/webhook", include_in_schema=False)
async def razorpay_webhook(request: Request) -> dict:
    # Same as the Stripe webhook: no Clerk auth, authenticated by its own
    # HMAC signature instead.
    payload = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    if not billing_razorpay.verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay webhook signature")

    billing_razorpay.handle_webhook_event(json.loads(payload))
    return {"received": True}
