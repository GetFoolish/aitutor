"""
Stripe Payment Integration for Credits
"""
import os
import stripe
from typing import Dict, Optional
from fastapi import HTTPException, status

# Stripe Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Credit Packages
CREDIT_PACKAGES = {
    "starter": {
        "name": "Starter Pack",
        "credits": 100,
        "price_usd": 9.99,
        "price_id": os.getenv("STRIPE_STARTER_PRICE_ID", ""),
    },
    "pro": {
        "name": "Pro Pack",
        "credits": 500,
        "price_usd": 39.99,
        "price_id": os.getenv("STRIPE_PRO_PRICE_ID", ""),
    },
    "unlimited": {
        "name": "Unlimited Pack",
        "credits": 2000,
        "price_usd": 99.99,
        "price_id": os.getenv("STRIPE_UNLIMITED_PRICE_ID", ""),
    },
}


class StripeService:
    """
    Handles Stripe payment operations for credit purchases.
    """

    @staticmethod
    def create_checkout_session(
        user_id: str,
        package_id: str,
        success_url: str,
        cancel_url: str
    ) -> Dict:
        """
        Create a Stripe Checkout session for credit purchase.

        Args:
            user_id: The user's ID
            package_id: Credit package ID (starter, pro, unlimited)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled

        Returns:
            Session dict with checkout_url
        """
        if not stripe.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe not configured. Set STRIPE_SECRET_KEY."
            )

        if package_id not in CREDIT_PACKAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid package. Choose from: {list(CREDIT_PACKAGES.keys())}"
            )

        package = CREDIT_PACKAGES[package_id]

        try:
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': package['name'],
                            'description': f"{package['credits']} AI Tutor Credits",
                        },
                        'unit_amount': int(package['price_usd'] * 100),  # Stripe uses cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={
                    'user_id': user_id,
                    'package_id': package_id,
                    'credits': package['credits'],
                },
            )

            return {
                "checkout_url": session.url,
                "session_id": session.id,
            }

        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Stripe error: {str(e)}"
            )

    @staticmethod
    def verify_webhook_signature(payload: bytes, sig_header: str) -> Dict:
        """
        Verify Stripe webhook signature and extract event.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header

        Returns:
            Stripe event dict
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe webhook secret not configured."
            )

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return event

        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload"
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid signature"
            )

    @staticmethod
    def create_subscription(
        user_id: str,
        email: str,
        plan_id: str = "monthly"
    ) -> Dict:
        """
        Create a recurring subscription for unlimited credits.

        Args:
            user_id: The user's ID
            email: User's email
            plan_id: Subscription plan (monthly, annual)

        Returns:
            Subscription dict
        """
        if not stripe.api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe not configured."
            )

        try:
            # Create or retrieve customer
            customers = stripe.Customer.list(email=email, limit=1)
            if customers.data:
                customer = customers.data[0]
            else:
                customer = stripe.Customer.create(
                    email=email,
                    metadata={'user_id': user_id}
                )

            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{
                    'price': os.getenv(f"STRIPE_{plan_id.upper()}_PRICE_ID", ""),
                }],
                metadata={'user_id': user_id, 'plan': plan_id}
            )

            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
            }

        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Stripe error: {str(e)}"
            )


# Frontend Integration Instructions
"""
=== STRIPE INTEGRATION ===

1. Setup Stripe Account:
   - Go to: https://dashboard.stripe.com/register
   - Get API keys from Developers > API keys
   - Set environment variables:
     - STRIPE_SECRET_KEY (backend)
     - STRIPE_PUBLISHABLE_KEY (frontend)
     - STRIPE_WEBHOOK_SECRET (for webhooks)

2. Create Products in Stripe Dashboard:
   - Go to Products > Add Product
   - Create three products: Starter Pack, Pro Pack, Unlimited Pack
   - Set prices: $9.99, $39.99, $99.99
   - Copy Price IDs to environment variables

3. Frontend (React):
   ```bash
   npm install @stripe/stripe-js @stripe/react-stripe-js
   ```

   ```tsx
   import { loadStripe } from '@stripe/stripe-js';

   const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY);

   // When user clicks "Buy Credits"
   const handleBuyCredits = async (packageId) => {
     const response = await fetch('/payments/create-checkout', {
       method: 'POST',
       headers: { 'Authorization': `Bearer ${token}` },
       body: JSON.stringify({
         package_id: packageId,
         success_url: 'http://localhost:3000/payment/success',
         cancel_url: 'http://localhost:3000/payment/cancel'
       })
     });

     const { checkout_url } = await response.json();
     window.location.href = checkout_url;  // Redirect to Stripe Checkout
   };
   ```

4. Webhook Setup:
   - Go to Developers > Webhooks > Add endpoint
   - URL: https://yourdomain.com/payments/webhook
   - Events: checkout.session.completed, payment_intent.succeeded
   - Copy webhook signing secret to STRIPE_WEBHOOK_SECRET

5. Test Mode:
   - Use test card: 4242 4242 4242 4242
   - Any future expiry date
   - Any 3-digit CVC
"""
