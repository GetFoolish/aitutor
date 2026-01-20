"""
Stripe Configuration for Payment Processing
"""

import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

# Payment options (same as pricing page)
# Time-based pricing: minutes of tutoring per plan
# NOTE: Use PRICE IDs (starts with 'price_'), NOT Product IDs (starts with 'prod_')
# Find price IDs in Stripe Dashboard: Products → [Product Name] → Pricing section
PAYMENT_OPTIONS = {
    "starter": {
        "price_id": "price_1SnJvyJPgLGkt9xCA0KOYe1u",  # Replace with actual price ID from Stripe dashboard
        "minutes": 300,  # 5 hours in minutes
        "amount_cents": 999  # $9.99
    },
    "pro": {
        "price_id": "price_1SnKZzJPgLGkt9xCky3Pt6fb",  # Replace with actual price ID from Stripe dashboard
        "minutes": 1200,  # 20 hours in minutes
        "amount_cents": 1999  # $19.99
    },
    "premium": {
        "price_id": "price_1SnKbOJPgLGkt9xCL90zaCCR",  # Replace with actual price ID from Stripe dashboard
        "minutes": 3000,  # 50 hours in minutes
        "amount_cents": 3999  # $39.99
    }
}
