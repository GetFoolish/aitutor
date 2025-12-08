"""
Base Storage Interface for Question Persistence
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseStorage(ABC):
    """
    Abstract base class for question storage backends.

    Implement this interface to support different storage backends
    (MongoDB, PostgreSQL, file-based, etc.)
    """

    @abstractmethod
    async def save_generated_question(
        self,
        question: Dict[str, Any],
        source_question_id: str,
        generation_cost: Optional[float] = None,
        cost_breakdown: Optional[Dict[str, float]] = None,
        tokens_used: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Save a generated question and link it to its source.

        Args:
            question: The generated question document (Perseus format)
            source_question_id: ID of the source question in the database
            generation_cost: Total cost of generation in USD
            cost_breakdown: Detailed cost breakdown by component
            tokens_used: Token usage breakdown

        Returns:
            The ID of the saved generated question
        """
        pass

    @abstractmethod
    async def get_question_for_generation(self) -> Optional[Dict[str, Any]]:
        """
        Get a question that's ready for generation.

        Prioritizes questions with fewer generated variants.

        Returns:
            Question document or None if no questions available
        """
        pass

    @abstractmethod
    async def get_questions_with_images(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get questions that contain images.

        Args:
            limit: Maximum number of questions to return

        Returns:
            List of question documents with images
        """
        pass

    @abstractmethod
    async def increment_generated_count(self, question_id: str) -> bool:
        """
        Increment the generated_count for a question.

        Args:
            question_id: ID of the question

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the storage backend.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the storage backend."""
        pass
