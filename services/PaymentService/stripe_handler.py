"""
Stripe Payment Handler - Handles payment processing and webhooks
"""

import stripe
import os
from datetime import datetime
from managers.mongodb_manager import mongo_db
from services.PaymentService.stripe_config import PAYMENT_OPTIONS
from shared.logging_config import get_logger

logger = get_logger(__name__)


class StripePaymentHandler:
    """Handle Stripe payment operations"""

    @staticmethod
    def create_checkout_session(user_id: str, plan: str):
        """Create Stripe checkout session"""

        if plan not in PAYMENT_OPTIONS:
            raise ValueError(f"Invalid plan: {plan}")

        plan_details = PAYMENT_OPTIONS[plan]

        # Get frontend URL from environment
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": plan_details["price_id"],
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=f"{frontend_url}/app/payment/success",
            cancel_url=f"{frontend_url}/app/payment/cancel",
            client_reference_id=user_id,
            metadata={
                "user_id": user_id,
                "plan": plan,
                "minutes": plan_details["minutes"]
            }
        )

        logger.info(f"[STRIPE] Created checkout session for user {user_id}, plan {plan}")
        return session

    @staticmethod
    def handle_payment_success(event: dict):
        """Handle successful payment webhook"""

        try:
            session = event["data"]["object"]
            user_id = session.get("client_reference_id")
            plan = session.get("metadata", {}).get("plan")
            minutes = int(session.get("metadata", {}).get("minutes", 0))
            stripe_session_id = session.get("id")

            # Log webhook event for debugging
            logger.info(f"[WEBHOOK] Processing payment success: user_id={user_id}, plan={plan}, minutes={minutes}")

            # Validate required fields - skip if test event (user_id=None)
            if not stripe_session_id:
                logger.error(f"[STRIPE] Missing stripe_session_id in webhook event")
                raise ValueError("Missing stripe_session_id in webhook event")

            # If this is a test event (stripe trigger), log and return gracefully
            if not user_id:
                logger.warning(f"[WEBHOOK] Received test webhook event (no user_id). Skipping processing. Session: {stripe_session_id}")
                return

            logger.info(f"[STRIPE] Processing successful payment for user {user_id}, session {stripe_session_id}, plan {plan}")

            # Check idempotency: verify if this payment was already processed
            existing_payment = mongo_db.payments.find_one({"stripe_session_id": stripe_session_id})
            if existing_payment:
                logger.warning(f"[STRIPE] Payment already processed for session {stripe_session_id}. Skipping to prevent duplicate minutes.")
                return

            # Update user credits (minutes) and subscription plan in MongoDB
            try:
                mongo_db.users.update_one(
                    {"user_id": user_id},
                    {
                        "$inc": {"credits.balance": minutes},
                        "$set": {"subscription_plan": plan},
                        "$push": {
                            "payment_history": {
                                "payment_id": session.get("payment_intent"),
                                "plan": plan,
                                "minutes": minutes,
                                "amount": session.get("amount_total") / 100,
                                "status": "completed",
                                "timestamp": datetime.utcnow()
                            }
                        }
                    }
                )
            except Exception as e:
                logger.error(f"[STRIPE] Failed to update user minutes for user {user_id}: {str(e)}")
                raise

            # Log payment to payments collection
            try:
                mongo_db.payments.insert_one({
                    "user_id": user_id,
                    "payment_id": session.get("payment_intent"),
                    "plan": plan,
                    "minutes": minutes,
                    "amount": session.get("amount_total") / 100,
                    "status": "completed",
                    "timestamp": datetime.utcnow(),
                    "stripe_session_id": stripe_session_id
                })
            except Exception as e:
                logger.error(f"[STRIPE] Failed to log payment to payments collection: {str(e)}")
                raise

            logger.info(f"[STRIPE] Successfully updated tutoring minutes for user {user_id}: +{minutes} minutes, plan set to {plan}")

        except Exception as e:
            logger.error(f"[STRIPE] Error processing payment webhook: {str(e)}")
            raise
