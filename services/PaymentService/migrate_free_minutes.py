"""
Migration script to add free_minutes field to existing users
Run this once to update all existing users who don't have the free_minutes field

Usage:
    python services/PaymentService/migrate_free_minutes.py
"""
import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)


def migrate_free_minutes():
    """Add free_minutes field to existing users who don't have it"""
    
    # Find users without free_minutes field
    users_without_field = mongo_db.users.count_documents({"free_minutes": {"$exists": False}})
    
    if users_without_field == 0:
        logger.info("[OK] All users already have free_minutes field")
        print("[OK] All users already have free_minutes field")
        return
    
    logger.info(f"Found {users_without_field} users without free_minutes field. Migrating...")
    print(f"Found {users_without_field} users without free_minutes field. Migrating...")
    
    # Add free_minutes field to all users who don't have it
    result = mongo_db.users.update_many(
        {"free_minutes": {"$exists": False}},
        {
            "$set": {
                "free_minutes": {
                    "balance": 0.0,
                    "last_reset_date": None
                }
            }
        }
    )
    
    logger.info(f"[OK] Migrated {result.modified_count} users with free_minutes field")
    print(f"[OK] Migrated {result.modified_count} users with free_minutes field")
    print("[OK] Existing users will receive 15 daily minutes starting from their next session")
    
    # Show summary of a few users
    sample_users = list(mongo_db.users.find(
        {},
        {
            "user_id": 1,
            "email": 1,
            "credits.balance": 1,
            "free_minutes.balance": 1
        }
    ).limit(5))
    
    print("\n--- Sample User Balances ---")
    for user in sample_users:
        email = user.get("email", "N/A")
        paid = user.get("credits", {}).get("balance", 0)
        free = user.get("free_minutes", {}).get("balance", 0)
        print(f"  {email[:30]:30s} | Paid: {paid:6.1f} min | Free: {free:6.1f} min")
    print("----------------------------\n")


if __name__ == "__main__":
    print("=" * 60)
    print("FREE MINUTES MIGRATION SCRIPT")
    print("=" * 60)
    print()
    
    try:
        migrate_free_minutes()
        print()
        print("[SUCCESS] Migration completed successfully!")
        print()
        print("Next steps:")
        print("  1. Restart your backend services")
        print("  2. Existing users will get 15 free minutes on their next session")
        print("  3. Their existing paid minutes will remain intact")
        print()
    except Exception as e:
        logger.error(f"[ERROR] Migration failed: {e}", exc_info=True)
        print(f"\n[ERROR] Migration failed: {e}")
        print("Please check the logs for more details.")
        sys.exit(1)

