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
            },
            subscription_data={
                "metadata": {
                    "user_id": user_id,
                    "plan": plan,
                    "minutes": plan_details["minutes"]
                }
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

            # Get subscription ID from session
            subscription_id = session.get("subscription")
            if not subscription_id:
                logger.warning(f"[STRIPE] No subscription_id in checkout session for user {user_id}")

            # Retrieve full subscription object to get current_period_end
            subscription = None
            subscription_period_end = None
            if subscription_id:
                try:
                    subscription = stripe.Subscription.retrieve(subscription_id)
                    subscription_period_end = datetime.fromtimestamp(subscription.current_period_end)
                except Exception as e:
                    logger.warning(f"[STRIPE] Could not retrieve subscription details: {e}")

            # Update user with RESET balance (not increment) and subscription tracking
            try:
                update_fields = {
                    "$set": {
                        "credits.balance": minutes,  # RESET balance (not increment)
                        "subscription_plan": plan
                    },
                    "$push": {
                        "payment_history": {
                            "payment_id": session.get("payment_intent"),
                            "plan": plan,
                            "minutes": minutes,
                            "amount": session.get("amount_total") / 100,
                            "status": "completed",
                            "timestamp": datetime.utcnow(),
                            "type": "initial_subscription"
                        }
                    }
                }
                
                # Add subscription tracking fields if available
                if subscription_id:
                    update_fields["$set"]["stripe_subscription_id"] = subscription_id
                    update_fields["$set"]["subscription_status"] = "active"
                    if subscription_period_end:
                        update_fields["$set"]["subscription_current_period_end"] = subscription_period_end
                
                mongo_db.users.update_one({"user_id": user_id}, update_fields)
                
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

    @staticmethod
    def handle_subscription_renewal(event: dict):
        """Handle monthly subscription renewal from invoice.paid event"""
        
        try:
            invoice = event["data"]["object"]
            subscription_id = invoice.get("subscription")
            customer_id = invoice.get("customer")
            invoice_id = invoice.get("id")
            
            logger.info(f"[WEBHOOK] Processing subscription renewal: subscription={subscription_id}, invoice={invoice_id}")
            
            # Skip if this is the first invoice (already handled by checkout.session.completed)
            billing_reason = invoice.get("billing_reason")
            if billing_reason == "subscription_create":
                logger.info(f"[WEBHOOK] Skipping initial subscription invoice (already processed)")
                return
            
            # Validate subscription_id
            if not subscription_id:
                logger.error(f"[STRIPE] No subscription_id in invoice")
                return
            
            # Get subscription details from Stripe to access metadata
            try:
                subscription = stripe.Subscription.retrieve(subscription_id)
            except Exception as e:
                logger.error(f"[STRIPE] Failed to retrieve subscription {subscription_id}: {e}")
                return
            
            # Extract plan details from subscription metadata
            plan = subscription.get("metadata", {}).get("plan")
            if not plan or plan not in PAYMENT_OPTIONS:
                logger.error(f"[STRIPE] Invalid or missing plan in subscription metadata: {plan}")
                return
            
            plan_details = PAYMENT_OPTIONS[plan]
            minutes = plan_details["minutes"]
            
            # Find user by subscription_id
            user = mongo_db.users.find_one({"stripe_subscription_id": subscription_id})
            if not user:
                logger.error(f"[STRIPE] No user found with subscription_id: {subscription_id}")
                return
            
            user_id = user["user_id"]
            
            # Check idempotency: prevent duplicate renewals
            existing_payment = mongo_db.payments.find_one({
                "stripe_invoice_id": invoice_id,
                "status": "renewed"
            })
            if existing_payment:
                logger.warning(f"[STRIPE] Invoice {invoice_id} already processed. Skipping duplicate renewal.")
                return
            
            # RESET paid minutes (don't carry over old balance)
            subscription_period_end = datetime.fromtimestamp(subscription.current_period_end)
            
            mongo_db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "credits.balance": minutes,  # RESET to plan minutes
                        "subscription_plan": plan,
                        "subscription_status": "active",
                        "subscription_current_period_end": subscription_period_end
                    },
                    "$push": {
                        "payment_history": {
                            "payment_id": invoice.get("payment_intent"),
                            "plan": plan,
                            "minutes": minutes,
                            "amount": invoice.get("amount_paid") / 100,
                            "status": "renewed",
                            "timestamp": datetime.utcnow(),
                            "type": "subscription_renewal"
                        }
                    }
                }
            )
            
            # Log renewal to payments collection
            mongo_db.payments.insert_one({
                "user_id": user_id,
                "payment_id": invoice.get("payment_intent"),
                "plan": plan,
                "minutes": minutes,
                "amount": invoice.get("amount_paid") / 100,
                "status": "renewed",
                "timestamp": datetime.utcnow(),
                "stripe_subscription_id": subscription_id,
                "stripe_invoice_id": invoice_id,
                "type": "subscription_renewal"
            })
            
            logger.info(
                f"[STRIPE] Successfully renewed subscription for user {user_id}: "
                f"RESET to {minutes} minutes (was carrying {user.get('credits', {}).get('balance', 0)} minutes), "
                f"plan={plan}"
            )
            
        except Exception as e:
            logger.error(f"[STRIPE] Error processing subscription renewal: {str(e)}", exc_info=True)
            raise
