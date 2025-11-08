from __future__ import annotations

from typing import Any, Dict, List, Optional

from pymongo.collection import Collection

from .mongo_client import get_database

PERSEUS_COLLECTION = "perseus_questions"


def _collection() -> Collection:
    return get_database()[PERSEUS_COLLECTION]


def get_random_questions(sample_size: int) -> List[Dict[str, Any]]:
    pipeline = [{"$sample": {"size": sample_size}}]
    documents = list(_collection().aggregate(pipeline))
    for doc in documents:
        doc.pop("_id", None)
    return documents


def upsert_question(document_id: str, payload: Dict[str, Any]) -> None:
    _collection().update_one(
        {"_id": document_id},
        {"$set": payload},
        upsert=True,
    )


def get_question(document_id: str) -> Optional[Dict[str, Any]]:
    document = _collection().find_one({"_id": document_id})
    if not document:
        return None
    document.pop("_id", None)
    return document
