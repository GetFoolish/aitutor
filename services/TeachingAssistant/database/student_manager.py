"""
Student Manager - MongoDB operations for student data
Based on the Cognitive Memory Pipeline architecture

This module handles:
- Student CRUD operations
- Biography versioning and updates
- Academic journey tracking
- Statistics aggregation
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from ..models.student import (
    Student,
    StudentCreate,
    Biography,
    BiographyVersion,
    AcademicJourney,
    Milestone,
    OnboardingData,
)

logger = logging.getLogger(__name__)


class StudentManager:
    """
    Manages student data in MongoDB.

    Key responsibilities:
    - Create/update student profiles
    - Manage Living Biography with versioning
    - Track academic journey and milestones
    - Aggregate statistics
    """

    COLLECTION_NAME = "students"

    def __init__(self, mongo_client):
        self.db = mongo_client.db
        self.collection = self.db[self.COLLECTION_NAME]
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            self.collection.create_index("_id", unique=True)
            self.collection.create_index("email", sparse=True)
            self.collection.create_index("created_at")
            logger.info("[STUDENT_MANAGER] Indexes ensured on students collection")
        except Exception as e:
            logger.error(f"[STUDENT_MANAGER] Failed to create indexes: {e}")

    def get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get a student by ID"""
        return self.collection.find_one({"_id": student_id})

    def get_student_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a student by their auth user_id (maps to _id)"""
        return self.collection.find_one({"_id": user_id})

    def create_student(self, student_data: StudentCreate, student_id: str) -> Dict[str, Any]:
        """
        Create a new student profile.

        Args:
            student_data: Student creation data
            student_id: Unique identifier (usually user_id from auth)

        Returns:
            Created student document
        """
        now = datetime.utcnow()

        student_doc = {
            "_id": student_id,
            "name": student_data.name,
            "email": student_data.email,
            "onboarding_data": (
                student_data.onboarding_data.model_dump()
                if student_data.onboarding_data
                else OnboardingData().model_dump()
            ),
            "biography": {
                "text": "",
                "version": 0,
                "last_updated": now,
                "session_count": 0,
            },
            "biography_history": [],
            "academic_journey": {
                "current_topic": "",
                "mastered_topics": [],
                "struggling_topics": [],
                "milestones": [],
            },
            "statistics": {
                "total_sessions": 0,
                "total_questions_answered": 0,
                "total_questions_correct": 0,
                "average_session_duration_minutes": 0.0,
                "last_session_date": None,
            },
            "created_at": now,
            "updated_at": now,
        }

        self.collection.insert_one(student_doc)
        logger.info(f"[STUDENT_MANAGER] Created student {student_id}")
        return student_doc

    def get_or_create_student(self, user_id: str, name: str = "Student") -> Dict[str, Any]:
        """
        Get existing student or create new one.

        Args:
            user_id: Auth user ID
            name: Default name if creating new student

        Returns:
            Student document
        """
        student = self.get_student_by_user_id(user_id)
        if student:
            return student

        return self.create_student(
            StudentCreate(name=name),
            student_id=user_id
        )

    def get_biography(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get student's current biography"""
        student = self.collection.find_one(
            {"_id": student_id},
            {"biography": 1}
        )
        return student.get("biography") if student else None

    def update_biography(
        self,
        student_id: str,
        new_biography_text: str,
        session_count_increment: int = 1
    ) -> bool:
        """
        Update student's biography with versioning.

        This is called by the Biographer Agent after each session.

        Args:
            student_id: Student to update
            new_biography_text: The new biography text
            session_count_increment: How many sessions to add (usually 1)

        Returns:
            True if successful
        """
        student = self.get_student(student_id)
        if not student:
            logger.error(f"[STUDENT_MANAGER] Student {student_id} not found for biography update")
            return False

        now = datetime.utcnow()
        current_biography = student.get("biography", {})
        current_version = current_biography.get("version", 0)
        current_session_count = current_biography.get("session_count", 0)

        new_version = current_version + 1
        new_session_count = current_session_count + session_count_increment

        # Create version history entry
        version_entry = {
            "version": new_version,
            "text": new_biography_text,
            "created_at": now,
            "session_count": new_session_count,
        }

        # Update student document
        result = self.collection.update_one(
            {"_id": student_id},
            {
                "$set": {
                    "biography.text": new_biography_text,
                    "biography.version": new_version,
                    "biography.last_updated": now,
                    "biography.session_count": new_session_count,
                    "updated_at": now,
                },
                "$push": {
                    "biography_history": {
                        "$each": [version_entry],
                        "$slice": -50,  # Keep last 50 versions
                    }
                }
            }
        )

        if result.modified_count > 0:
            logger.info(
                f"[STUDENT_MANAGER] Updated biography for {student_id} "
                f"(v{current_version} -> v{new_version})"
            )
            return True
        return False

    def get_biography_history(
        self,
        student_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get biography version history"""
        student = self.collection.find_one(
            {"_id": student_id},
            {"biography_history": {"$slice": -limit}}
        )
        return student.get("biography_history", []) if student else []

    def rollback_biography(self, student_id: str, target_version: int) -> bool:
        """
        Rollback biography to a previous version.

        Args:
            student_id: Student to rollback
            target_version: Version number to restore

        Returns:
            True if successful
        """
        student = self.get_student(student_id)
        if not student:
            return False

        history = student.get("biography_history", [])
        target = next(
            (v for v in history if v["version"] == target_version),
            None
        )

        if not target:
            logger.error(f"[STUDENT_MANAGER] Version {target_version} not found")
            return False

        now = datetime.utcnow()
        current_version = student.get("biography", {}).get("version", 0)

        result = self.collection.update_one(
            {"_id": student_id},
            {
                "$set": {
                    "biography.text": target["text"],
                    "biography.version": current_version + 1,  # New version for rollback
                    "biography.last_updated": now,
                    "updated_at": now,
                },
                "$push": {
                    "biography_history": {
                        "version": current_version + 1,
                        "text": target["text"],
                        "created_at": now,
                        "session_count": student.get("biography", {}).get("session_count", 0),
                        "rollback_from": target_version,
                    }
                }
            }
        )

        if result.modified_count > 0:
            logger.info(f"[STUDENT_MANAGER] Rolled back biography to v{target_version}")
            return True
        return False

    def update_academic_journey(
        self,
        student_id: str,
        current_topic: Optional[str] = None,
        mastered_topic: Optional[str] = None,
        struggling_topic: Optional[str] = None,
        milestone: Optional[Milestone] = None
    ) -> bool:
        """
        Update student's academic journey.

        Args:
            student_id: Student to update
            current_topic: Set new current topic
            mastered_topic: Add topic to mastered list
            struggling_topic: Add topic to struggling list
            milestone: Add new milestone

        Returns:
            True if successful
        """
        update_ops = {"$set": {"updated_at": datetime.utcnow()}}

        if current_topic:
            update_ops["$set"]["academic_journey.current_topic"] = current_topic

        if mastered_topic:
            update_ops["$addToSet"] = update_ops.get("$addToSet", {})
            update_ops["$addToSet"]["academic_journey.mastered_topics"] = mastered_topic

        if struggling_topic:
            update_ops["$addToSet"] = update_ops.get("$addToSet", {})
            update_ops["$addToSet"]["academic_journey.struggling_topics"] = struggling_topic

        if milestone:
            update_ops["$push"] = update_ops.get("$push", {})
            update_ops["$push"]["academic_journey.milestones"] = milestone.model_dump()

        result = self.collection.update_one({"_id": student_id}, update_ops)
        return result.modified_count > 0

    def update_statistics(
        self,
        student_id: str,
        session_duration_minutes: float,
        questions_answered: int,
        questions_correct: int
    ) -> bool:
        """
        Update student statistics after a session.

        Args:
            student_id: Student to update
            session_duration_minutes: Duration of the session
            questions_answered: Questions answered in session
            questions_correct: Questions answered correctly

        Returns:
            True if successful
        """
        student = self.get_student(student_id)
        if not student:
            return False

        stats = student.get("statistics", {})
        total_sessions = stats.get("total_sessions", 0) + 1
        total_questions = stats.get("total_questions_answered", 0) + questions_answered
        total_correct = stats.get("total_questions_correct", 0) + questions_correct

        # Calculate running average
        prev_avg = stats.get("average_session_duration_minutes", 0)
        new_avg = ((prev_avg * (total_sessions - 1)) + session_duration_minutes) / total_sessions

        now = datetime.utcnow()

        result = self.collection.update_one(
            {"_id": student_id},
            {
                "$set": {
                    "statistics.total_sessions": total_sessions,
                    "statistics.total_questions_answered": total_questions,
                    "statistics.total_questions_correct": total_correct,
                    "statistics.average_session_duration_minutes": round(new_avg, 2),
                    "statistics.last_session_date": now,
                    "updated_at": now,
                }
            }
        )

        if result.modified_count > 0:
            logger.info(
                f"[STUDENT_MANAGER] Updated stats for {student_id}: "
                f"sessions={total_sessions}, questions={total_questions}"
            )
            return True
        return False

    def update_onboarding_data(
        self,
        student_id: str,
        onboarding_data: OnboardingData
    ) -> bool:
        """Update student's onboarding data"""
        result = self.collection.update_one(
            {"_id": student_id},
            {
                "$set": {
                    "onboarding_data": onboarding_data.model_dump(),
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        return result.modified_count > 0

    def list_students(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List students with pagination"""
        cursor = self.collection.find(
            {},
            {
                "_id": 1,
                "name": 1,
                "email": 1,
                "statistics": 1,
                "biography.version": 1,
                "created_at": 1,
            }
        ).skip(skip).limit(limit)
        return list(cursor)

    def delete_student(self, student_id: str) -> bool:
        """Delete a student (use with caution)"""
        result = self.collection.delete_one({"_id": student_id})
        if result.deleted_count > 0:
            logger.info(f"[STUDENT_MANAGER] Deleted student {student_id}")
            return True
        return False
