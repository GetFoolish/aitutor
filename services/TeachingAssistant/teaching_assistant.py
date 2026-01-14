"""
Teaching Assistant v5 - Cognitive Memory Pipeline
All state is stored in MongoDB via SessionManager.
Integrates with Living Biography for personalized tutoring.

v4 improvements integrated:
- Event processing loop support (running, ongoing)
- Colored logging
"""

import asyncio
from typing import Optional, Dict, Any, List

from .greeting_handler import GreetingHandler
from .session_manager import SessionManager
from managers.mongodb_manager import MongoDBManager

from shared.logging_config import get_logger

logger = get_logger(__name__)


class TeachingAssistant:
    """
    Teaching Assistant v5 with Cognitive Memory Pipeline.

    Key innovations:
    - Living Biography: Narrative documents that evolve with each session
    - Semantic Memory: Pinecone-powered retrieval for relevant memories
    - Conversation Tracking: Full conversation logs for biography updates
    - Personalized Prompts: Biography-driven session openings and closings
    """

    def __init__(self):
        mongo = MongoDBManager()
        self.session_manager = SessionManager(mongo)
        self.greeting_handler = GreetingHandler()
        self.mongo = mongo

        # v4 improvement: Event processing loop support
        self.running = False

        logger.info("[TEACHING_ASSISTANT] v5 Initialized with Cognitive Memory Pipeline")

    async def ongoing(self):
        """
        Event processing loop (v4 improvement).
        Called by lifespan manager in api.py.

        Handles background tasks like:
        - Inactivity checks
        - Memory consolidation
        - Session cleanup
        """
        logger.info("[TEACHING_ASSISTANT] Event processing loop started")

        while self.running:
            try:
                # Get all active sessions and check for inactivity
                active_sessions = self.session_manager.list_active_sessions()

                for session in active_sessions:
                    session_id = session.get("session_id")
                    if session_id:
                        # Check for inactivity (this will push prompt if needed)
                        self.check_inactivity(session_id)

                # Sleep before next check (don't check too frequently)
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                logger.info("[TEACHING_ASSISTANT] Event processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"[TEACHING_ASSISTANT] Error in event processing loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying

        logger.info("[TEACHING_ASSISTANT] Event processing loop stopped")

    def start_session(self, user_id: str, student_name: str = None) -> dict:
        """
        Start a new session with biography-driven personalization.

        NEW in v5: Loads student biography and injects into system prompt.

        Args:
            user_id: Auth user ID (maps to student_id)
            student_name: Optional name for new students

        Returns:
            Dict with session_id, prompt (with biography), and session_info
        """
        # Ensure student exists (create if needed)
        student = self._ensure_student(user_id, student_name)
        student_id = student.get("_id", user_id)

        # Create session linked to student
        session = self.session_manager.create_session(user_id, student_id)

        # Get biography data for personalized greeting
        biography_data = self.session_manager.get_student_biography(student_id)

        # Generate personalized greeting with biography
        greeting = self.greeting_handler.get_greeting(user_id, biography_data)

        logger.info(
            f"[TEACHING_ASSISTANT] Started session {session['session_id']} "
            f"for student {student_id} (biography version: {student.get('biography', {}).get('version', 0)})"
        )

        return {
            "session_id": session["session_id"],
            "prompt": greeting,
            "session_info": self.session_manager.get_session_info(session["session_id"]),
            "biography_version": student.get("biography", {}).get("version", 0),
        }

    def _ensure_student(self, user_id: str, name: str = None) -> Dict[str, Any]:
        """Ensure student document exists, create if needed"""
        student = self.mongo.db.students.find_one({"_id": user_id})

        if not student:
            # Create new student document
            from datetime import datetime
            student = {
                "_id": user_id,
                "name": name or "Student",
                "onboarding_data": {
                    "core_values": [],
                    "north_star_goals": [],
                    "personality_traits": [],
                    "blind_spots": [],
                    "emotional_baseline": "neutral",
                    "interests": [],
                    "created_at": datetime.utcnow(),
                },
                "biography": {
                    "text": "",
                    "version": 0,
                    "last_updated": datetime.utcnow(),
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
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            self.mongo.db.students.insert_one(student)
            logger.info(f"[TEACHING_ASSISTANT] Created new student {user_id}")

        return student

    def end_session(self, session_id: str) -> dict:
        """
        End session with cognitive memory processing.

        NEW in v5:
        - Extracts memories from conversation
        - Updates biography via Biographer Agent
        - Stores data in MongoDB and Pinecone

        Returns:
            Dict with closing prompt and session summary
        """
        # End session (this triggers biography update and memory extraction)
        session_summary = self.session_manager.end_session(session_id)

        if not session_summary:
            return {
                "prompt": "",
                "session_info": {"session_active": False}
            }

        # Generate personalized closing with session insights
        closing = self.greeting_handler.get_closing(
            duration_minutes=session_summary.get("duration_minutes", 0),
            questions_answered=session_summary.get("questions_answered", 0),
            topics_covered=session_summary.get("topics_covered", []),
            key_moments=session_summary.get("key_moments", []),
        )

        # Update student statistics
        session = self.session_manager.get_session_by_id(session_id)
        if session:
            student_id = session.get("student_id", session.get("user_id"))
            self._update_student_stats(
                student_id,
                session_summary.get("duration_minutes", 0),
                session_summary.get("questions_answered", 0),
                session_summary.get("questions_correct", 0),
            )

        return {
            "prompt": closing,
            "session_info": session_summary
        }

    def _update_student_stats(
        self,
        student_id: str,
        duration: float,
        questions: int,
        correct: int
    ):
        """Update student statistics after session"""
        from datetime import datetime

        student = self.mongo.db.students.find_one({"_id": student_id})
        if not student:
            return

        stats = student.get("statistics", {})
        total_sessions = stats.get("total_sessions", 0) + 1
        total_questions = stats.get("total_questions_answered", 0) + questions
        total_correct = stats.get("total_questions_correct", 0) + correct

        # Calculate running average
        prev_avg = stats.get("average_session_duration_minutes", 0)
        new_avg = ((prev_avg * (total_sessions - 1)) + duration) / total_sessions if total_sessions > 0 else duration

        self.mongo.db.students.update_one(
            {"_id": student_id},
            {
                "$set": {
                    "statistics.total_sessions": total_sessions,
                    "statistics.total_questions_answered": total_questions,
                    "statistics.total_questions_correct": total_correct,
                    "statistics.average_session_duration_minutes": round(new_avg, 2),
                    "statistics.last_session_date": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            }
        )

    def add_conversation_turn(
        self,
        session_id: str,
        speaker: str,
        text: str,
        emotion: str = None
    ) -> None:
        """
        Add a conversation turn to the session log.

        NEW in v5: Full conversation tracking for biography updates.

        Args:
            session_id: Session to add turn to
            speaker: "adam", "student", or "system"
            text: What was said
            emotion: Detected emotion (optional)
        """
        self.session_manager.add_conversation_turn(
            session_id=session_id,
            speaker=speaker,
            text=text,
            emotion=emotion
        )

    def record_question_answered(
        self,
        session_id: str,
        question_id: str,
        is_correct: bool
    ) -> None:
        """Record a question answer"""
        self.session_manager.record_question_answered(session_id, is_correct)

    def record_conversation_turn(self, session_id: str) -> None:
        """Record a conversation turn (legacy method for inactivity tracking)"""
        self.session_manager.record_conversation_turn(session_id)

    def check_inactivity(self, session_id: str) -> Optional[str]:
        """Check inactivity and return prompt if needed"""
        if self.session_manager.check_inactivity(session_id):
            prompt = self.greeting_handler.get_inactivity_prompt()
            self.session_manager.push_instruction(session_id, prompt)
            return prompt
        return None

    def get_session_info(self, session_id: str) -> dict:
        """Get current session info"""
        return self.session_manager.get_session_info(session_id)

    def get_active_session(self, user_id: str) -> Optional[dict]:
        """Get active session for user"""
        return self.session_manager.get_active_session(user_id)

    def push_instruction(self, session_id: str, instruction: str) -> str:
        """Push an instruction to be delivered via SSE"""
        return self.session_manager.push_instruction(session_id, instruction)

    def retrieve_memories(
        self,
        session_id: str,
        query_text: str
    ) -> Optional[str]:
        """
        Retrieve relevant memories and inject as system update.

        NEW in v5: Semantic memory retrieval during conversation.

        Args:
            session_id: Current session
            query_text: Current conversation context

        Returns:
            Memory injection prompt if relevant memories found, None otherwise
        """
        session = self.session_manager.get_session_by_id(session_id)
        if not session:
            return None

        student_id = session.get("student_id", session.get("user_id"))

        # Retrieve relevant memories
        memories = self.session_manager.retrieve_relevant_memories(
            student_id=student_id,
            query_text=query_text,
            top_k=3
        )

        if not memories:
            return None

        # Generate memory injection prompt
        prompt = self.greeting_handler.get_memory_injection_prompt(
            memories=memories,
            current_context=query_text
        )

        if prompt:
            # Push as system update
            self.session_manager.push_instruction(session_id, prompt)
            logger.debug(f"[TEACHING_ASSISTANT] Injected {len(memories)} memories into session")

        return prompt

    def get_student_biography(self, user_id: str) -> Dict[str, Any]:
        """
        Get student's current biography and stats.

        Args:
            user_id: Student/user ID

        Returns:
            Dict with biography, academic journey, and statistics
        """
        student = self.mongo.db.students.find_one({"_id": user_id})
        if not student:
            return {
                "biography": "",
                "academic_journey": {},
                "statistics": {},
            }

        return {
            "biography": student.get("biography", {}).get("text", ""),
            "biography_version": student.get("biography", {}).get("version", 0),
            "academic_journey": student.get("academic_journey", {}),
            "statistics": student.get("statistics", {}),
            "onboarding_data": student.get("onboarding_data", {}),
        }

    def update_onboarding_data(
        self,
        user_id: str,
        onboarding_data: Dict[str, Any]
    ) -> bool:
        """
        Update student onboarding data and optionally regenerate initial biography.

        Args:
            user_id: Student ID
            onboarding_data: New onboarding data

        Returns:
            True if successful
        """
        from datetime import datetime

        result = self.mongo.db.students.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "onboarding_data": onboarding_data,
                    "updated_at": datetime.utcnow(),
                }
            }
        )

        if result.modified_count > 0:
            # Optionally regenerate biography if this is initial onboarding
            student = self.mongo.db.students.find_one({"_id": user_id})
            if student and not student.get("biography", {}).get("text"):
                self._generate_initial_biography(user_id, onboarding_data)

        return result.modified_count > 0

    def _generate_initial_biography(
        self,
        user_id: str,
        onboarding_data: Dict[str, Any]
    ) -> None:
        """Generate initial biography from onboarding data"""
        try:
            from .core.biographer import biographer_agent

            student = self.mongo.db.students.find_one({"_id": user_id})
            name = student.get("name", "Student") if student else "Student"

            biography = biographer_agent.generate_initial_biography(
                name=name,
                onboarding_data=onboarding_data
            )

            if biography:
                from datetime import datetime
                self.mongo.db.students.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "biography.text": biography,
                            "biography.version": 1,
                            "biography.last_updated": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        },
                        "$push": {
                            "biography_history": {
                                "version": 1,
                                "text": biography,
                                "created_at": datetime.utcnow(),
                                "session_count": 0,
                            }
                        }
                    }
                )
                logger.info(f"[TEACHING_ASSISTANT] Generated initial biography for {user_id}")

        except Exception as e:
            logger.error(f"[TEACHING_ASSISTANT] Failed to generate initial biography: {e}")

    def set_academic_topic(self, user_id: str, topic: str) -> bool:
        """Set the current academic topic for a student"""
        from datetime import datetime

        result = self.mongo.db.students.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "academic_journey.current_topic": topic,
                    "updated_at": datetime.utcnow(),
                }
            }
        )
        return result.modified_count > 0
