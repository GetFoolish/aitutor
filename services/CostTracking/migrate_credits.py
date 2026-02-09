"""
Migration script to initialize credits for existing users
Run this once if you have existing users without credits field
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)


def initialize_credits():
    """Add credits field to existing users"""
    mongo_db.users.update_many(
        {"credits": {"$exists": False}},  # Only update users without credits field
        {
            "$set": {
                "credits": {
                    "balance": 0.0,
                    "currency": "USD"
                },
                "payment_history": []
            }
        }
    )
    logger.info("✓ Credits initialized for existing users")


if __name__ == "__main__":
    initialize_credits()
