"""
Free Minutes Handler - Manages daily free minutes allocation
Separate free minutes from paid minutes to prevent conflicts
"""
from datetime import datetime, date
from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger
import math

logger = get_logger(__name__)

# Daily free minutes amount
DAILY_FREE_MINUTES = 15


def allocate_daily_free_minutes(user_id: str) -> bool:
    """
    Allocate 15 free minutes per day if not already allocated today.
    Free minutes are tracked separately from paid minutes.
    
    Args:
        user_id: User ID
    
    Returns:
        True if minutes were allocated, False if already allocated today
    """
    try:
        user = mongo_db.users.find_one({"user_id": user_id})
        if not user:
            logger.warning(f"[FREE_MINUTES] User {user_id} not found")
            return False
        
        today = date.today()
        today_str = today.isoformat()
        
        # Check last_daily_reset_date in free_minutes
        free_minutes = user.get("free_minutes", {})
        last_reset = free_minutes.get("last_reset_date")
        
        if last_reset:
            try:
                if isinstance(last_reset, datetime):
                    last_reset_date = last_reset.date()
                elif isinstance(last_reset, str):
                    last_reset_date = datetime.fromisoformat(last_reset).date()
                else:
                    last_reset_date = None
                
                if last_reset_date and last_reset_date == today:
                    logger.debug(f"[FREE_MINUTES] User {user_id} already received daily minutes today")
                    return False
            except ValueError:
                logger.warning(f"[FREE_MINUTES] Invalid last_reset date for user {user_id}: {last_reset}")
        
        # Set free_minutes to 15 (separate from paid balance)
        result = mongo_db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "free_minutes.balance": DAILY_FREE_MINUTES,
                    "free_minutes.last_reset_date": today_str
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"[FREE_MINUTES] ✅ Allocated {DAILY_FREE_MINUTES} free minutes to user {user_id} for {today_str}")
            return True
        else:
            logger.warning(f"[FREE_MINUTES] Failed to update free minutes for user {user_id}")
            return False
        
    except Exception as e:
        logger.error(f"[FREE_MINUTES] ❌ Error allocating daily minutes for user {user_id}: {str(e)}", exc_info=True)
        return False


def check_user_balance(user_id: str) -> dict:
    """
    Get current user balance (both free and paid minutes).
    
    Args:
        user_id: User ID
    
    Returns:
        Dict with 'free': float, 'paid': float, 'total': float
    """
    try:
        user = mongo_db.users.find_one(
            {"user_id": user_id},
            {"credits.balance": 1, "free_minutes.balance": 1}
        )
        
        if not user:
            logger.warning(f"[FREE_MINUTES] User {user_id} not found when checking balance")
            return {"free": 0.0, "paid": 0.0, "total": 0.0}
        
        paid_balance = user.get("credits", {}).get("balance", 0.0)
        free_balance = user.get("free_minutes", {}).get("balance", 0.0)
        
        return {
            "free": float(free_balance),
            "paid": float(paid_balance),
            "total": float(free_balance + paid_balance)
        }
        
    except Exception as e:
        logger.error(f"[FREE_MINUTES] ❌ Error checking balance for user {user_id}: {str(e)}", exc_info=True)
        return {"free": 0.0, "paid": 0.0, "total": 0.0}


def deduct_minutes(user_id: str, minutes: float) -> bool:
    """
    Deduct minutes from user balance.
    Deducts from free minutes first, then from paid minutes.
    
    Args:
        user_id: User ID
        minutes: Minutes to deduct (will be rounded up)
    
    Returns:
        True if successful, False if insufficient balance
    """
    try:
        minutes_to_deduct = math.ceil(minutes)
        
        if minutes_to_deduct <= 0:
            logger.debug(f"[FREE_MINUTES] Skipping deduction - zero or negative minutes for user {user_id}")
            return True
        
        balances = check_user_balance(user_id)
        free_balance = balances["free"]
        paid_balance = balances["paid"]
        total_balance = balances["total"]
        
        if total_balance < minutes_to_deduct:
            logger.warning(
                f"[FREE_MINUTES] ⚠️ Insufficient total balance for user {user_id}: "
                f"has {total_balance} min, needs {minutes_to_deduct} min"
            )
            # Deduct what they have (prevents negative balance)
            minutes_to_deduct = int(total_balance)
            if minutes_to_deduct <= 0:
                return False
        
        # Deduct from free minutes first
        if free_balance >= minutes_to_deduct:
            # All from free minutes
            result = mongo_db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"free_minutes.balance": -minutes_to_deduct}}
            )
            logger.info(
                f"[FREE_MINUTES] ✅ Deducted {minutes_to_deduct} min from FREE balance. "
                f"Free: {free_balance:.1f} → {free_balance - minutes_to_deduct:.1f}"
            )
        elif free_balance > 0:
            # Partial from free, rest from paid
            from_free = int(free_balance)
            from_paid = minutes_to_deduct - from_free
            
            result = mongo_db.users.update_one(
                {"user_id": user_id},
                {
                    "$set": {"free_minutes.balance": 0},
                    "$inc": {"credits.balance": -from_paid}
                }
            )
            logger.info(
                f"[FREE_MINUTES] ✅ Deducted {from_free} min from FREE + {from_paid} min from PAID. "
                f"Total: {total_balance:.1f} → {total_balance - minutes_to_deduct:.1f}"
            )
        else:
            # All from paid minutes
            result = mongo_db.users.update_one(
                {"user_id": user_id},
                {"$inc": {"credits.balance": -minutes_to_deduct}}
            )
            logger.info(
                f"[FREE_MINUTES] ✅ Deducted {minutes_to_deduct} min from PAID balance. "
                f"Paid: {paid_balance:.1f} → {paid_balance - minutes_to_deduct:.1f}"
            )
        
        return result.modified_count > 0
            
    except Exception as e:
        logger.error(f"[FREE_MINUTES] ❌ Error deducting minutes for user {user_id}: {str(e)}", exc_info=True)
        return False

