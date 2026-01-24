"""
Payment API Endpoints
"""

import os
import stripe
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from managers.mongodb_manager import mongo_db
from shared.auth_middleware import get_current_user
from services.PaymentService.stripe_handler import StripePaymentHandler
from shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])


class CheckoutSessionRequest(BaseModel):
    plan: str


@router.post("/create-checkout-session")
async def create_checkout_session(request: Request, body: CheckoutSessionRequest):
    """Create Stripe checkout session"""

    user_id = get_current_user(request)

    # Validate user authentication
    if not user_id:
        logger.error("[PAYMENT] User not authenticated for checkout session creation")
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Check if user already has an active subscription
    user = mongo_db.users.find_one(
        {"user_id": user_id},
        {"stripe_subscription_id": 1, "subscription_status": 1, "subscription_plan": 1}
    )
    
    if user:
        subscription_id = user.get("stripe_subscription_id")
        subscription_status = user.get("subscription_status")
        current_plan = user.get("subscription_plan")
        
        # Prevent multiple active subscriptions
        if subscription_id and subscription_status == "active":
            logger.warning(
                f"[PAYMENT] User {user_id} attempted to purchase new plan but already has "
                f"active {current_plan} subscription: {subscription_id}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"You already have an active {current_plan} subscription. Please cancel your current subscription before purchasing a new plan."
            )

    plan = body.plan

    try:
        session = StripePaymentHandler.create_checkout_session(
            user_id=user_id,
            plan=plan
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[PAYMENT] Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    logger.info(f"[WEBHOOK] Received webhook event. Signature header present: {bool(sig_header)}")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            stripe_webhook_secret
        )
        logger.info(f"[WEBHOOK] Event verified successfully. Type: {event['type']}")
    except ValueError as e:
        logger.error(f"[WEBHOOK] Invalid payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"[WEBHOOK] Invalid signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle events
    if event["type"] == "checkout.session.completed":
        logger.info(f"[WEBHOOK] Processing checkout.session.completed event")
        try:
            StripePaymentHandler.handle_payment_success(event)
            logger.info(f"[WEBHOOK] Successfully processed checkout.session.completed event")
        except Exception as e:
            logger.error(f"[WEBHOOK] Error processing payment success: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing payment")
            
    elif event["type"] == "invoice.paid":
        logger.info(f"[WEBHOOK] Processing invoice.paid event (subscription renewal)")
        try:
            StripePaymentHandler.handle_subscription_renewal(event)
            logger.info(f"[WEBHOOK] Successfully processed invoice.paid event")
        except Exception as e:
            logger.error(f"[WEBHOOK] Error processing subscription renewal: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing renewal")
            
    else:
        logger.info(f"[WEBHOOK] Received unhandled event type: {event['type']}")

    return {"status": "success"}


@router.get("/success", response_class=HTMLResponse)
async def payment_success():
    """Payment success redirect page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Successful</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                padding: 40px;
                text-align: center;
                max-width: 500px;
            }
            .success-icon {
                width: 80px;
                height: 80px;
                margin: 0 auto 20px;
                background: #4CAF50;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 40px;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            p {
                color: #666;
                margin-bottom: 30px;
                font-size: 16px;
                line-height: 1.6;
            }
            .button {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 30px;
                border-radius: 5px;
                text-decoration: none;
                font-weight: 600;
                transition: background 0.3s;
            }
            .button:hover {
                background: #764ba2;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✓</div>
            <h1>Payment Successful!</h1>
            <p>Your payment has been processed successfully and your credits have been added to your account.</p>
            <a href="/account" class="button">Back to Account</a>
        </div>
    </body>
    </html>
    """


@router.get("/cancel", response_class=HTMLResponse)
async def payment_cancel():
    """Payment cancelled redirect page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Cancelled</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
                padding: 40px;
                text-align: center;
                max-width: 500px;
            }
            .cancel-icon {
                width: 80px;
                height: 80px;
                margin: 0 auto 20px;
                background: #f5576c;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 40px;
                color: white;
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
                font-size: 28px;
            }
            p {
                color: #666;
                margin-bottom: 30px;
                font-size: 16px;
                line-height: 1.6;
            }
            .button {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 30px;
                border-radius: 5px;
                text-decoration: none;
                font-weight: 600;
                transition: background 0.3s;
            }
            .button:hover {
                background: #764ba2;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="cancel-icon">✕</div>
            <h1>Payment Cancelled</h1>
            <p>Your payment has been cancelled. No charges were made to your account.</p>
            <a href="/pricing" class="button">Try Again</a>
        </div>
    </body>
    </html>
    """
