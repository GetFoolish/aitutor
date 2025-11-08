"""
Payment Routes - Stripe Checkout and Webhooks
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request, Header
from pydantic import BaseModel
from typing import Optional

from auth.auth_routes import get_current_user
from db.auth_repository import add_credits
from .stripe_service import StripeService, CREDIT_PACKAGES

router = APIRouter(prefix="/payments", tags=["payments"])


class CheckoutRequest(BaseModel):
    package_id: str
    success_url: str
    cancel_url: str


class SubscriptionRequest(BaseModel):
    plan_id: str  # monthly or annual


@router.get("/packages")
async def get_credit_packages():
    """Get available credit packages"""
    return {
        "packages": [
            {
                "id": package_id,
                "name": package["name"],
                "credits": package["credits"],
                "price_usd": package["price_usd"],
            }
            for package_id, package in CREDIT_PACKAGES.items()
        ]
    }


@router.post("/create-checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a Stripe Checkout session for credit purchase.
    Returns checkout_url to redirect user to Stripe.
    """
    session = StripeService.create_checkout_session(
        user_id=current_user["user_id"],
        package_id=request.package_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url
    )

    return session


@router.post("/create-subscription")
async def create_subscription(
    request: SubscriptionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a recurring subscription for unlimited credits.
    """
    subscription = StripeService.create_subscription(
        user_id=current_user["user_id"],
        email=current_user["email"],
        plan_id=request.plan_id
    )

    return subscription


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """
    Stripe webhook handler.
    Listens for payment completion and adds credits to user account.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )

    # Get raw body
    payload = await request.body()

    # Verify webhook signature
    event = StripeService.verify_webhook_signature(payload, stripe_signature)

    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Extract user_id and credits from metadata
        user_id = session.get('metadata', {}).get('user_id')
        credits = int(session.get('metadata', {}).get('credits', 0))

        if user_id and credits > 0:
            # Add credits to user account
            success = add_credits(user_id, credits)

            if success:
                print(f"✅ Added {credits} credits to user {user_id}")
            else:
                print(f"❌ Failed to add credits to user {user_id}")

    elif event['type'] == 'payment_intent.succeeded':
        # Payment succeeded
        print(f"Payment succeeded: {event['data']['object']['id']}")

    elif event['type'] == 'invoice.payment_succeeded':
        # Subscription renewal succeeded
        invoice = event['data']['object']
        user_id = invoice.get('metadata', {}).get('user_id')

        # For subscriptions, add monthly credits
        if user_id:
            add_credits(user_id, 1000)  # Monthly subscription gets 1000 credits
            print(f"✅ Added 1000 subscription credits to user {user_id}")

    return {"status": "success"}


@router.get("/history")
async def get_payment_history(current_user: dict = Depends(get_current_user)):
    """
    Get user's payment history.
    TODO: Store transactions in MongoDB for better tracking.
    """
    # For now, return empty list
    # In production, query transactions from MongoDB
    return {
        "transactions": [],
        "total_spent": 0.0,
        "total_credits_purchased": 0
    }
