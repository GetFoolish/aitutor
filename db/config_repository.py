from __future__ import annotations

from typing import Any, Dict

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from .mongo_client import get_database

CONFIG_COLLECTION = "config"


def _collection() -> Collection:
    return get_database()[CONFIG_COLLECTION]


def get_config_document(key: str) -> Dict[str, Any]:
    document = _collection().find_one({"_id": key})
    if not document:
        raise KeyError(f"Configuration document '{key}' not found in MongoDB.")
    return document.get("data", {})


def upsert_config_document(key: str, data: Dict[str, Any]) -> None:
    _collection().update_one(
        {"_id": key},
        {"$set": {"data": data}},
        upsert=True,
    )
