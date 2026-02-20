"""
MongoDB wrapper with automatic Pydantic validation.

Provides type-safe document access with explicit error handling.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class ValidatedCollection(Generic[T]):
    """
    Wrapper around PyMongo collection with automatic validation.

    Usage:
        from models.question_schemas import QuestionDocument
        validated = ValidatedCollection(mongo.ai_generated_questions, QuestionDocument)
        doc = validated.find_one({"question_id": "abc123"})  # Returns QuestionDocument or None
    """

    def __init__(self, collection, model_class: type[T]):
        """
        Initialize validated collection wrapper.

        Args:
            collection: PyMongo collection instance
            model_class: Pydantic model class for validation
        """
        self.collection = collection
        self.model_class = model_class

    def find_one(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        skip_validation: bool = False,
    ) -> Optional[T]:
        """
        Find one document with validation.

        Args:
            filter: MongoDB query filter
            projection: Fields to include/exclude
            skip_validation: Skip Pydantic validation (returns raw dict)

        Returns:
            Validated model instance or None if not found/invalid

        Raises:
            ValidationError: If document exists but fails validation (when skip_validation=False)
        """
        doc = self.collection.find_one(filter, projection)
        if doc is None:
            return None

        if skip_validation:
            return doc  # type: ignore

        try:
            return self.model_class.model_validate(doc)
        except ValidationError as e:
            logger.error(
                f"[MONGO_VALIDATE] Document validation failed for {self.model_class.__name__}: {e.error_count()} errors\n"
                f"Filter: {filter}\n"
                f"First error: {e.errors()[0] if e.errors() else 'unknown'}"
            )
            raise

    def find_one_safe(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
    ) -> Optional[T]:
        """
        Find one document with validation, returning None on validation failure.

        Like find_one() but returns None instead of raising ValidationError.
        Logs validation errors for debugging.
        """
        try:
            return self.find_one(filter, projection, skip_validation=False)
        except ValidationError:
            return None

    def find(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip_validation: bool = False,
    ) -> List[T]:
        """
        Find multiple documents with validation.

        Args:
            filter: MongoDB query filter
            projection: Fields to include/exclude
            limit: Maximum number of documents
            skip_validation: Skip Pydantic validation

        Returns:
            List of validated model instances (skips invalid documents with warning)
        """
        cursor = self.collection.find(filter, projection)
        if limit:
            cursor = cursor.limit(limit)

        results = []
        for doc in cursor:
            if skip_validation:
                results.append(doc)  # type: ignore
                continue

            try:
                validated = self.model_class.model_validate(doc)
                results.append(validated)
            except ValidationError as e:
                logger.warning(
                    f"[MONGO_VALIDATE] Skipping invalid document in {self.model_class.__name__}: "
                    f"{e.error_count()} errors. ID: {doc.get('_id', 'unknown')}"
                )
                continue

        return results

    def insert_one(self, document: T) -> Any:
        """
        Insert a validated document.

        Args:
            document: Pydantic model instance

        Returns:
            InsertOneResult from PyMongo
        """
        doc_dict = document.model_dump(exclude_none=False)
        return self.collection.insert_one(doc_dict)

    def insert_many(self, documents: List[T]) -> Any:
        """
        Insert multiple validated documents.

        Args:
            documents: List of Pydantic model instances

        Returns:
            InsertManyResult from PyMongo
        """
        doc_dicts = [doc.model_dump(exclude_none=False) for doc in documents]
        return self.collection.insert_many(doc_dicts)

    def update_one(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
    ) -> Any:
        """
        Update one document (no validation on update operations).

        Args:
            filter: MongoDB query filter
            update: Update operations ($set, $inc, etc.)
            upsert: Create if not exists

        Returns:
            UpdateResult from PyMongo
        """
        return self.collection.update_one(filter, update, upsert=upsert)


# Convenience wrapper for backward compatibility
def validate_and_get(
    collection,
    filter: Dict[str, Any],
    model_class: type[T],
    projection: Optional[Dict[str, Any]] = None,
) -> Optional[T]:
    """
    One-off validated find_one without creating a wrapper instance.

    Args:
        collection: PyMongo collection
        filter: Query filter
        model_class: Pydantic model class
        projection: Fields to project

    Returns:
        Validated instance or None
    """
    wrapper = ValidatedCollection(collection, model_class)
    return wrapper.find_one_safe(filter, projection)
