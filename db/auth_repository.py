"""
Authentication Repository - User CRUD for Auth
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pymongo.collection import Collection
from .mongo_client import get_database

USERS_COLLECTION = "users"


def _collection() -> Collection:
    return get_database()[USERS_COLLECTION]


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    return _collection().find_one({"email": email})


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    return _collection().find_one({"_id": user_id})


def get_user_by_oauth_id(auth_provider: str, oauth_id: str) -> Optional[Dict[str, Any]]:
    """Get user by OAuth provider and ID"""
    return _collection().find_one({
        "auth_provider": auth_provider,
        "oauth_id": oauth_id
    })


def create_user(user_data: Dict[str, Any]) -> str:
    """Create a new user and return user_id"""
    # Use email as _id for uniqueness
    user_data["_id"] = user_data["user_id"]
    result = _collection().insert_one(user_data)
    return str(result.inserted_id)


def update_user(user_id: str, update_data: Dict[str, Any]) -> bool:
    """Update user data"""
    result = _collection().update_one(
        {"_id": user_id},
        {"$set": update_data}
    )
    return result.modified_count > 0


def update_last_login(user_id: str) -> None:
    """Update user's last login timestamp"""
    _collection().update_one(
        {"_id": user_id},
        {"$set": {"last_login": datetime.utcnow()}}
    )


def add_child_to_parent(parent_id: str, child_id: str) -> bool:
    """Add a child to parent's children list"""
    result = _collection().update_one(
        {"_id": parent_id},
        {"$addToSet": {"children": child_id}}
    )
    return result.modified_count > 0


def deduct_credits(user_id: str, amount: int) -> bool:
    """Deduct credits from user account"""
    result = _collection().update_one(
        {"_id": user_id, "credits": {"$gte": amount}},
        {"$inc": {"credits": -amount}}
    )
    return result.modified_count > 0


def add_credits(user_id: str, amount: int) -> bool:
    """Add credits to user account"""
    result = _collection().update_one(
        {"_id": user_id},
        {"$inc": {"credits": amount}}
    )
    return result.modified_count > 0


def get_user_credits(user_id: str) -> Optional[int]:
    """Get user's credit balance"""
    user = get_user_by_id(user_id)
    return user.get("credits") if user else None
