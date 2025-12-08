"""
MongoDB Storage Implementation for Question Bank Generator

This storage adapter is compatible with the existing SherlockEDApi models
and the validate-questions endpoint workflow.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document, Link
from bson import ObjectId

from .base_storage import BaseStorage

# Import logger
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import get_logger

logger = get_logger(__name__)


class QuestionDocument(Document):
    """Original question document model (compatible with SherlockEDApi)."""
    answerArea: Optional[Dict] = None
    hints: Optional[List] = None
    itemDataVersion: Optional[Dict] = None
    question: Dict
    source: str = "khan"
    generated_count: int = 0
    generated: List[Link["GeneratedQuestionDocument"]] = []
    created_at: datetime = datetime.now()

    class Settings:
        name = "questions"


class GeneratedQuestionDocument(Document):
    """Generated question document model (compatible with SherlockEDApi)."""
    answerArea: Optional[Dict] = None
    hints: Optional[List] = None
    itemDataVersion: Optional[Dict] = None
    question: Dict
    source: str = "aitutor"
    human_approved: bool = False
    created_at: datetime = datetime.now()
    generation_cost: Optional[float] = None
    cost_breakdown: Optional[Dict] = None
    tokens_used: Optional[Dict] = None

    class Settings:
        name = "questions-generated"


class MongoDBStorage(BaseStorage):
    """
    MongoDB storage implementation using Beanie ODM.

    Compatible with SherlockEDApi's data models and the validate-questions
    endpoint workflow.

    Usage:
        storage = MongoDBStorage(connection_string="mongodb://localhost:27017")
        await storage.connect()

        # Save a generated question
        question_id = await storage.save_generated_question(
            question=generated_question,
            source_question_id="abc123"
        )

        await storage.disconnect()
    """

    def __init__(self, connection_string: Optional[str] = None, database_name: str = "aitutor"):
        """
        Initialize MongoDB storage.

        Args:
            connection_string: MongoDB connection string (default from MONGODB_URI env)
            database_name: Name of the database to use
        """
        self.connection_string = connection_string or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to MongoDB and initialize Beanie."""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client[self.database_name]

            # Initialize Beanie with document models
            await init_beanie(
                database=self.db,
                document_models=[QuestionDocument, GeneratedQuestionDocument]
            )

            self._connected = True
            logger.info(f"Connected to MongoDB database: {self.database_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")

    async def save_generated_question(
        self,
        question: Dict[str, Any],
        source_question_id: str,
        generation_cost: Optional[float] = None,
        cost_breakdown: Optional[Dict[str, float]] = None,
        tokens_used: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Save a generated question and link it to source.

        This matches the workflow expected by the validate-questions endpoint:
        1. Creates GeneratedQuestionDocument
        2. Links it to the source QuestionDocument
        3. Updates generated_count on source
        """
        if not self._connected:
            raise RuntimeError("Not connected to MongoDB")

        # Create generated question document
        generated_doc = GeneratedQuestionDocument(
            question=question.get('question', {}),
            answerArea=question.get('answerArea'),
            hints=question.get('hints'),
            itemDataVersion=question.get('itemDataVersion'),
            source="aitutor",
            human_approved=False,
            created_at=datetime.now(),
            generation_cost=generation_cost,
            cost_breakdown=cost_breakdown,
            tokens_used=tokens_used
        )

        # Insert the generated question
        await generated_doc.insert()

        # Link to source question
        try:
            source_doc = await QuestionDocument.get(ObjectId(source_question_id))
            if source_doc:
                source_doc.generated.append(generated_doc)
                source_doc.generated_count = len(source_doc.generated)
                await source_doc.save()
                logger.debug(f"Linked generated question to source {source_question_id}")
        except Exception as e:
            logger.warning(f"Could not link to source question: {e}")

        return str(generated_doc.id)

    async def get_question_for_generation(self) -> Optional[Dict[str, Any]]:
        """
        Get a question ready for generation.

        Prioritizes by generated_count: 0s first, then 1s, then 2s.
        """
        if not self._connected:
            raise RuntimeError("Not connected to MongoDB")

        # Try to find questions with generated_count = 0 first
        for target_count in [0, 1, 2]:
            questions = await QuestionDocument.find(
                QuestionDocument.source == "khan",
                QuestionDocument.generated_count == target_count
            ).to_list(limit=10)

            if questions:
                import random
                question = random.choice(questions)
                return {
                    "_id": str(question.id),
                    "question": question.question,
                    "answerArea": question.answerArea,
                    "hints": question.hints,
                    "itemDataVersion": question.itemDataVersion,
                    "source": question.source,
                    "generated_count": question.generated_count
                }

        return None

    async def get_questions_with_images(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get questions that contain image widgets.

        Uses MongoDB query to find questions with image widgets.
        """
        if not self._connected:
            raise RuntimeError("Not connected to MongoDB")

        # Query for questions with image widgets
        # Looking for widgets with type="image" or backgroundImage
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"question.widgets": {"$elemMatch": {"type": "image"}}},
                        {"question.content": {"$regex": r"\[\[☃ image"}}
                    ]
                }
            },
            {"$limit": limit}
        ]

        # Fallback: get all questions and filter in Python
        all_questions = await QuestionDocument.find(
            QuestionDocument.source == "khan"
        ).to_list(limit=limit * 2)

        result = []
        for q in all_questions:
            # Check if question has images
            widgets = q.question.get('widgets', {})
            has_image = False

            for widget_data in widgets.values():
                if widget_data.get('type') == 'image':
                    has_image = True
                    break
                if 'backgroundImage' in widget_data.get('options', {}):
                    has_image = True
                    break

            if has_image:
                result.append({
                    "_id": str(q.id),
                    "question": q.question,
                    "answerArea": q.answerArea,
                    "hints": q.hints,
                    "itemDataVersion": q.itemDataVersion,
                    "source": q.source,
                    "generated_count": q.generated_count
                })

            if len(result) >= limit:
                break

        return result

    async def increment_generated_count(self, question_id: str) -> bool:
        """Increment generated_count for a question."""
        if not self._connected:
            raise RuntimeError("Not connected to MongoDB")

        try:
            question = await QuestionDocument.get(ObjectId(question_id))
            if question:
                question.generated_count += 1
                await question.save()
                return True
            return False
        except Exception as e:
            logger.error(f"Error incrementing count: {e}")
            return False

    async def load_questions_from_json(self, directory: str) -> int:
        """
        Load questions from JSON files into MongoDB.

        Utility method to seed the database from CurriculumBuilder JSON files.

        Args:
            directory: Path to directory containing JSON files

        Returns:
            Number of questions loaded
        """
        import json
        from pathlib import Path

        if not self._connected:
            raise RuntimeError("Not connected to MongoDB")

        loaded = 0
        directory = Path(directory)

        for json_file in directory.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Check if already exists (by file content hash or similar)
                existing = await QuestionDocument.find_one(
                    QuestionDocument.question == data.get('question')
                )

                if not existing:
                    doc = QuestionDocument(
                        question=data.get('question', {}),
                        answerArea=data.get('answerArea'),
                        hints=data.get('hints'),
                        itemDataVersion=data.get('itemDataVersion'),
                        source="khan",
                        generated_count=0,
                        created_at=datetime.now()
                    )
                    await doc.insert()
                    loaded += 1

            except Exception as e:
                logger.warning(f"Error loading {json_file}: {e}")
                continue

        logger.info(f"Loaded {loaded} questions into MongoDB")
        return loaded
