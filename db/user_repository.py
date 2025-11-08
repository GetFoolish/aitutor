from __future__ import annotations

from typing import Any, Dict, Optional

from pymongo.collection import Collection

from .mongo_client import get_database

USERS_COLLECTION = "users"


def _collection() -> Collection:
    return get_database()[USERS_COLLECTION]


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    document = _collection().find_one({"_id": user_id})
    if not document:
        return None
    document.pop("_id", None)
    return document


def upsert_user(user_id: str, data: Dict[str, Any]) -> None:
    _collection().update_one(
        {"_id": user_id},
        {"$set": data},
        upsert=True,
    )


def delete_user(user_id: str) -> None:
    _collection().delete_one({"_id": user_id})
