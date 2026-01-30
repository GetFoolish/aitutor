"""
Session Manager for TeachingAssistant v5
Manages session state in MongoDB with conversation tracking.
Integrates with the Cognitive Memory Pipeline for biography updates.

v4 improvements integrated:
- Config-driven architecture
- Colored logging

v1-memory additions (Moltbot-inspired):
- ConversationStore integration for searchable history
- Full-text search across all sessions
- Token-aware context management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid

from shared.logging_config import get_logger

# Try to import config (v4 improvement)
try:
    from .core.config import TeachingAssistantConfig
except ImportError:
    TeachingAssistantConfig = None

logger = get_logger(__name__)

# Lazy imports to avoid circular dependencies
_biographer_agent = None
_memory_extractor = None
_student_manager = None
_conversation_store = None


def _get_conversation_store():
    """Lazy load ConversationStore to avoid circular imports"""
    global _conversation_store
    if _conversation_store is None:
        try:
            from .Memory.conversation_store import get_conversation_store
            _conversation_store = get_conversation_store
            logger.info("[SESSION_MANAGER] ConversationStore loaded")
        except ImportError as e:
            logger.warning(f"[SESSION_MANAGER] ConversationStore not available: {e}")
            _conversation_store = lambda x=None: None
    return _conversation_store


def _get_biographer():
    global _biographer_agent
    if _biographer_agent is None:
        try:
            from .core.biographer import biographer_agent
            _biographer_agent = biographer_agent
        except ImportError:
            logger.warning("[SESSION_MANAGER] Biographer not available")
    return _biographer_agent


def _get_memory_extractor():
    global _memory_extractor
    if _memory_extractor is None:
        try:
            from .core.memory_extractor import memory_extractor
            _memory_extractor = memory_extractor
        except ImportError:
            logger.warning("[SESSION_MANAGER] Memory extractor not available")
    return _memory_extractor


class SessionManager:
    """
    Manages session state in MongoDB instead of in-memory.
    Enables multi-user support and survives Cloud Run restarts.
    """

    INACTIVITY_THRESHOLD_SECONDS = 60
    GRACE_PERIOD_SECONDS = 60

    def __init__(self, mongo_client):
        self.db = mongo_client.db
        self.sessions = self.db.sessions
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            self.sessions.create_index("user_id")
            self.sessions.create_index("session_id", unique=True)
            self.sessions.create_index([("is_active", 1), ("user_id", 1)])
            # TTL index for automatic cleanup (documents expire at expires_at time)
            self.sessions.create_index("expires_at", expireAfterSeconds=0)
            logger.info("[SESSION_MANAGER] Indexes ensured on sessions collection")
        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Failed to create indexes: {e}")

    def create_session(self, user_id: str, student_id: str = None) -> Dict[str, Any]:
        """
        Start a new session for a user.

        Args:
            user_id: Auth user ID
            student_id: Student ID (defaults to user_id if not provided)
        """
        # End any existing active session for this user
        self.end_active_sessions(user_id)

        now = datetime.utcnow()
        session = {
            "session_id": f"sess_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "student_id": student_id or user_id,  # NEW: Link to student document
            "started_at": now,
            "last_activity": now,
            "ended_at": None,
            "is_active": True,
            "questions_answered_this_session": 0,
            "questions_correct_this_session": 0,
            "last_conversation_turn": now,
            "last_question_submission": None,
            "pending_instructions": [],
            "websocket_connected": False,
            "sse_connected": False,
            "expires_at": now + timedelta(hours=24),
            "inactivity_prompt_sent": False,
            # NEW: Cognitive Memory Pipeline fields
            "conversation": [],  # Full conversation log
            "emotional_arc": [],  # Emotions detected through session
            "topics_covered": [],  # Academic topics discussed
            "key_moments": [],  # Important moments identified
            "session_summary": None,  # AI-generated summary at end
        }
        self.sessions.insert_one(session)
        logger.info(f"[SESSION_MANAGER] Created session {session['session_id']} for user {user_id}")
        return session

    def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the active session for a user"""
        return self.sessions.find_one({
            "user_id": user_id,
            "is_active": True
        })

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by its ID"""
        return self.sessions.find_one({"session_id": session_id})

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions (for admin/observer use)"""
        return list(self.sessions.find({"is_active": True}))

    def update_activity(self, session_id: str) -> None:
        """Update last activity timestamp"""
        now = datetime.utcnow()
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "last_activity": now,
                    "expires_at": now + timedelta(hours=24)
                }
            }
        )

    def record_conversation_turn(self, session_id: str) -> None:
        """Record a conversation turn for inactivity tracking (legacy method)"""
        now = datetime.utcnow()
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "last_conversation_turn": now,
                    "last_activity": now,
                    "expires_at": now + timedelta(hours=24),
                    "inactivity_prompt_sent": False
                }
            }
        )

    def add_conversation_turn(
        self,
        session_id: str,
        speaker: str,
        text: str,
        emotion: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a conversation turn to the session log.

        NEW in v5: Full conversation tracking for biography updates.
        NEW in v1-memory: Also stores in ConversationStore for search/compaction.

        Args:
            session_id: Session to add turn to
            speaker: "adam", "student", or "system"
            text: What was said
            emotion: Detected emotion (optional)
            metadata: Additional metadata (optional)
        """
        now = datetime.utcnow()
        turn = {
            "speaker": speaker,
            "text": text,
            "timestamp": now,
            "emotion": emotion,
            "metadata": metadata or {}
        }

        update_ops = {
            "$push": {"conversation": turn},
            "$set": {
                "last_conversation_turn": now,
                "last_activity": now,
                "expires_at": now + timedelta(hours=24),
                "inactivity_prompt_sent": False
            }
        }

        # Track emotions in the arc
        if emotion:
            update_ops["$push"]["emotional_arc"] = emotion

        self.sessions.update_one({"session_id": session_id}, update_ops)
        logger.debug(f"[SESSION_MANAGER] Added {speaker} turn to session {session_id}")

        # NEW: Also store in ConversationStore for searchable history
        try:
            session = self.sessions.find_one({"session_id": session_id})
            if session:
                student_id = session.get("student_id", session.get("user_id"))
                get_store = _get_conversation_store()
                if get_store:
                    store = get_store(student_id)
                    if store and store.enabled:
                        store.add_turn(
                            session_id=session_id,
                            student_id=student_id,
                            speaker=speaker,
                            text=text,
                            emotion=emotion,
                            metadata=metadata
                        )
                        logger.debug(f"[SESSION_MANAGER] Turn also stored in ConversationStore")
        except Exception as e:
            logger.warning(f"[SESSION_MANAGER] ConversationStore write failed (non-critical): {e}")

    def get_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the full conversation log for a session"""
        session = self.sessions.find_one(
            {"session_id": session_id},
            {"conversation": 1}
        )
        return session.get("conversation", []) if session else []

    def add_topic(self, session_id: str, topic: str) -> None:
        """Add a topic covered in this session"""
        self.sessions.update_one(
            {"session_id": session_id},
            {"$addToSet": {"topics_covered": topic}}
        )

    def add_key_moment(self, session_id: str, moment: str) -> None:
        """Add a key moment to the session"""
        self.sessions.update_one(
            {"session_id": session_id},
            {"$push": {"key_moments": moment}}
        )

    def record_question_answered(
        self,
        session_id: str,
        is_correct: bool
    ) -> None:
        """Record a question answer"""
        now = datetime.utcnow()
        update = {
            "$set": {
                "last_question_submission": now,
                "last_activity": now,
                "expires_at": now + timedelta(hours=24),
                "inactivity_prompt_sent": False  # Reset on activity
            },
            "$inc": {
                "questions_answered_this_session": 1
            }
        }
        if is_correct:
            update["$inc"]["questions_correct_this_session"] = 1

        self.sessions.update_one({"session_id": session_id}, update)

    def push_instruction(self, session_id: str, instruction_text: str) -> str:
        """Add an instruction to the pending queue"""
        instruction = {
            "instruction_id": f"instr_{uuid.uuid4().hex[:8]}",
            "text": instruction_text,
            "created_at": datetime.utcnow(),
            "delivered": False
        }
        self.sessions.update_one(
            {"session_id": session_id},
            {"$push": {"pending_instructions": instruction}}
        )
        logger.info(f"[SESSION_MANAGER] Pushed instruction {instruction['instruction_id']} to session {session_id}")
        return instruction["instruction_id"]

    def get_pending_instructions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all undelivered instructions"""
        session = self.sessions.find_one(
            {"session_id": session_id},
            {"pending_instructions": 1}
        )
        if not session:
            return []
        return [
            inst for inst in session.get("pending_instructions", [])
            if not inst.get("delivered", False)
        ]

    def mark_instruction_delivered(
        self,
        session_id: str,
        instruction_id: str
    ) -> None:
        """Mark an instruction as delivered"""
        self.sessions.update_one(
            {
                "session_id": session_id,
                "pending_instructions.instruction_id": instruction_id
            },
            {"$set": {"pending_instructions.$.delivered": True}}
        )
        logger.info(f"[SESSION_MANAGER] Marked instruction {instruction_id} as delivered")

    def set_connection_status(
        self,
        session_id: str,
        websocket: bool = None,
        sse: bool = None
    ) -> None:
        """Update connection status"""
        update = {}
        if websocket is not None:
            update["websocket_connected"] = websocket
        if sse is not None:
            update["sse_connected"] = sse
        if update:
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": update}
            )

    def end_session(
        self,
        session_id: str,
        run_biographer: bool = True
    ) -> Dict[str, Any]:
        """
        End a session and process cognitive memory updates.

        NEW in v5: Runs the Biographer Agent to update the student's biography.

        Args:
            session_id: Session to end
            run_biographer: Whether to update biography (default True)

        Returns:
            Session summary with stats and processed data
        """
        session = self.sessions.find_one({"session_id": session_id})
        if not session:
            logger.warning(f"[SESSION_MANAGER] Session {session_id} not found")
            return {}

        now = datetime.utcnow()
        duration_minutes = (now - session["started_at"]).total_seconds() / 60
        
        # Get the credits available at session start
        credits_at_start = session.get("credits_at_start", 0)
        user_id = session["user_id"]
        
        # MINUTE DEDUCTION LOGIC
        import math
        from services.PaymentService.free_minutes_handler import deduct_minutes
        
        # Deduct MINIMUM of: (actual duration) OR (credits available at start)
        # This prevents negative balance if user overruns their credits
        minutes_to_deduct = min(math.ceil(duration_minutes), credits_at_start)
        
        # Deduct the minutes
        deduct_success = deduct_minutes(user_id, minutes_to_deduct)
        
        # Log if session exceeded available credits
        if duration_minutes > credits_at_start:
            logger.warning(
                f"[SESSION_MANAGER] ⚠️ Session {session_id[:8]}... exceeded available credits! "
                f"Duration: {duration_minutes:.2f} min, Credits: {credits_at_start} min, "
                f"Deducted: {minutes_to_deduct} min"
            )
        else:
            logger.info(
                f"[SESSION_MANAGER] ✅ Session {session_id[:8]}... ended normally. "
                f"Duration: {duration_minutes:.2f} min, Deducted: {minutes_to_deduct} min"
            )

        # Get conversation and session data
        conversation = session.get("conversation", [])
        emotional_arc = session.get("emotional_arc", [])
        topics_covered = session.get("topics_covered", [])
        key_moments = session.get("key_moments", [])
        student_id = session.get("student_id", session["user_id"])

        # Extract additional data using AI (if enabled)
        memory_extractor = _get_memory_extractor()
        biographer = _get_biographer()

        # Extract topics if not already done
        if not topics_covered and memory_extractor and memory_extractor.enabled:
            topics_covered = memory_extractor.extract_topics(conversation)
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"topics_covered": topics_covered}}
            )

        # Extract key moments if not already done
        if not key_moments and biographer and biographer.enabled:
            key_moments = biographer.extract_key_moments(conversation)
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"key_moments": key_moments}}
            )

        # Analyze emotions if not tracked
        if not emotional_arc and biographer and biographer.enabled:
            emotional_arc = biographer.analyze_session_emotions(conversation)
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"emotional_arc": emotional_arc}}
            )

        # Build session summary
        session_summary = {
            "topics_covered": topics_covered,
            "emotional_arc": emotional_arc,
            "key_moments": key_moments,
            "questions_answered": session["questions_answered_this_session"],
            "questions_correct": session["questions_correct_this_session"],
            "duration_minutes": round(duration_minutes, 2),
        }

        # Extract and store memories
        if memory_extractor and conversation:
            try:
                memories = memory_extractor.extract_memories(
                    student_id=student_id,
                    session_id=session_id,
                    transcript=conversation
                )

                if memories:
                    # Prefer vector store so memories get embeddings for semantic search
                    try:
                        from .Memory.mongodb_vector_store import MongoDBMemoryStore
                        from .Memory.schema import Memory as VectorMemory, MemoryType as VectorMemoryType

                        store = MongoDBMemoryStore(user_id=student_id)
                        if store.enabled:
                            vector_memories = []
                            for memory in memories:
                                mem_type = VectorMemoryType(memory.type.value)
                                vector_memories.append(VectorMemory(
                                    student_id=memory.student_id,
                                    session_id=memory.session_id,
                                    type=mem_type,
                                    text=memory.text,
                                    importance=memory.importance,
                                    metadata=memory.metadata.model_dump() if memory.metadata else {},
                                ))
                            saved = store.save_memories_batch(vector_memories)
                            logger.info(f"[SESSION_MANAGER] Stored {saved} memories via MongoDBMemoryStore")
                        else:
                            raise RuntimeError("MongoDBMemoryStore not enabled")
                    except Exception as store_err:
                        # Fallback to raw insert if vector store fails
                        logger.warning(f"[SESSION_MANAGER] Vector store save failed, falling back to raw insert: {store_err}")
                        memory_docs = []
                        for memory in memories:
                            memory_id = f"mem_{uuid.uuid4().hex[:12]}"
                            memory_docs.append({
                                "_id": memory_id,
                                "student_id": memory.student_id,
                                "session_id": memory.session_id,
                                "type": memory.type.value,
                                "text": memory.text,
                                "importance": memory.importance,
                                "timestamp": now,
                                "metadata": memory.metadata.model_dump() if memory.metadata else {},
                            })
                        if memory_docs:
                            self.db.memories.insert_many(memory_docs)
                            logger.info(f"[SESSION_MANAGER] Stored {len(memory_docs)} memories in MongoDB (fallback)")

            except Exception as e:
                logger.error(f"[SESSION_MANAGER] Memory extraction failed: {e}")

        # Run Biographer Agent to update biography
        if run_biographer and biographer and biographer.enabled and conversation:
            try:
                # Get current biography
                student = self.db.students.find_one({"_id": student_id})
                current_biography = ""
                if student:
                    current_biography = student.get("biography", {}).get("text", "")

                # Generate updated biography
                updated_biography = biographer.update_biography(
                    current_biography=current_biography,
                    session_transcript=conversation,
                    session_summary=session_summary
                )

                if updated_biography and updated_biography != current_biography:
                    # Update student document
                    current_version = student.get("biography", {}).get("version", 0) if student else 0
                    current_session_count = student.get("biography", {}).get("session_count", 0) if student else 0

                    version_entry = {
                        "version": current_version + 1,
                        "text": updated_biography,
                        "created_at": now,
                        "session_count": current_session_count + 1,
                    }

                    self.db.students.update_one(
                        {"_id": student_id},
                        {
                            "$set": {
                                "biography.text": updated_biography,
                                "biography.version": current_version + 1,
                                "biography.last_updated": now,
                                "biography.session_count": current_session_count + 1,
                                "updated_at": now,
                            },
                            "$push": {
                                "biography_history": {
                                    "$each": [version_entry],
                                    "$slice": -50,
                                }
                            }
                        },
                        upsert=True
                    )
                    logger.info(f"[SESSION_MANAGER] Updated biography for student {student_id}")

            except Exception as e:
                logger.error(f"[SESSION_MANAGER] Biography update failed: {e}")

        # Store session summary
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "is_active": False,
                    "ended_at": now,
                    "websocket_connected": False,
                    "sse_connected": False,
                    "session_summary": session_summary,
                    "duration_minutes": round(duration_minutes, 2),
                    "minutes_deducted": minutes_to_deduct,
                    "credits_exceeded": duration_minutes > credits_at_start,
                    "deduct_success": deduct_success
                }
            }
        )

        return {
            "session_id": session_id,
            "duration_minutes": round(duration_minutes, 2),
            "minutes_deducted": minutes_to_deduct,
            "questions_answered": session["questions_answered_this_session"],
            "questions_correct": session["questions_correct_this_session"],
            "topics_covered": topics_covered,
            "emotional_arc": emotional_arc,
            "key_moments": key_moments,
        }

    def end_active_sessions(self, user_id: str) -> int:
        """End all active sessions for a user (cleanup)"""
        result = self.sessions.update_many(
            {"user_id": user_id, "is_active": True},
            {
                "$set": {
                    "is_active": False,
                    "ended_at": datetime.utcnow(),
                    "websocket_connected": False,
                    "sse_connected": False
                }
            }
        )
        if result.modified_count > 0:
            logger.info(f"[SESSION_MANAGER] Ended {result.modified_count} active sessions for user {user_id}")
        return result.modified_count

    def check_inactivity(self, session_id: str) -> bool:
        """
        Check if session has been inactive beyond threshold.
        Returns True if inactive AND we haven't already sent a prompt.
        """
        session = self.sessions.find_one({"session_id": session_id})
        if not session or not session["is_active"]:
            return False

        # Don't send another prompt if we already sent one
        if session.get("inactivity_prompt_sent", False):
            return False

        now = datetime.utcnow()
        started_at = session["started_at"]

        # Grace period: don't check inactivity for first 60 seconds
        if (now - started_at).total_seconds() < self.GRACE_PERIOD_SECONDS:
            return False

        # Get the most recent activity time
        last_conversation = session.get("last_conversation_turn") or started_at
        last_question = session.get("last_question_submission") or started_at
        last_activity = max(last_conversation, last_question)

        inactive_seconds = (now - last_activity).total_seconds()
        is_inactive = inactive_seconds >= self.INACTIVITY_THRESHOLD_SECONDS

        if is_inactive:
            # Mark that we've sent a prompt to avoid spamming
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"inactivity_prompt_sent": True}}
            )

        return is_inactive

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session info for API response"""
        session = self.sessions.find_one({"session_id": session_id})
        if not session:
            return {"session_active": False}

        now = datetime.utcnow()
        duration_minutes = (now - session["started_at"]).total_seconds() / 60

        return {
            "session_id": session["session_id"],
            "user_id": session["user_id"],
            "student_id": session.get("student_id", session["user_id"]),
            "session_active": session["is_active"],
            "duration_minutes": round(duration_minutes, 2),
            "questions_answered": session["questions_answered_this_session"],
            "questions_correct": session["questions_correct_this_session"],
            "websocket_connected": session["websocket_connected"],
            "sse_connected": session["sse_connected"],
            "topics_covered": session.get("topics_covered", []),
            "conversation_turns": len(session.get("conversation", [])),
        }

    def retrieve_relevant_memories(
        self,
        student_id: str,
        query_text: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for mid-conversation injection.

        Uses MongoDB Atlas Vector Search for semantic similarity.

        Args:
            student_id: Student to search memories for
            query_text: Current conversation context
            top_k: Number of memories to retrieve

        Returns:
            List of relevant memories with similarity scores
        """
        try:
            from .Memory.mongodb_vector_store import MongoDBMemoryStore

            store = MongoDBMemoryStore(user_id=student_id)
            if not store.enabled:
                logger.warning("[SESSION_MANAGER] MongoDBMemoryStore not enabled")
                return []

            memories = store.search(
                query_text=query_text,
                student_id=student_id,
                top_k=top_k,
                min_importance=0.0
            )

            if memories:
                logger.info(f"[SESSION_MANAGER] Found {len(memories)} memories via vector search")

            return memories

        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Memory retrieval failed: {e}")
            return []

    def get_student_biography(self, student_id: str) -> Dict[str, Any]:
        """
        Get student biography and academic journey for session start.

        Returns:
            Dict with biography text and academic info
        """
        student = self.db.students.find_one({"_id": student_id})
        if not student:
            return {
                "biography": "",
                "current_topic": "",
                "total_sessions": 0,
                "last_session_date": None,
            }

        return {
            "biography": student.get("biography", {}).get("text", ""),
            "current_topic": student.get("academic_journey", {}).get("current_topic", ""),
            "mastered_topics": student.get("academic_journey", {}).get("mastered_topics", []),
            "total_sessions": student.get("statistics", {}).get("total_sessions", 0),
            "last_session_date": student.get("statistics", {}).get("last_session_date"),
            "total_questions": student.get("statistics", {}).get("total_questions_answered", 0),
        }

    # =========================================================================
    # NEW: Moltbot-inspired conversation search methods
    # =========================================================================

    def search_conversations(
        self,
        student_id: str,
        query: str,
        limit: int = 20,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search across all conversations for a student.

        Moltbot-style grep equivalent: find any message containing the query.

        Args:
            student_id: Student to search for
            query: Search query
            limit: Max results
            session_id: Optional - filter to specific session

        Returns:
            List of matching turns with context
        """
        try:
            get_store = _get_conversation_store()
            if not get_store:
                logger.warning("[SESSION_MANAGER] ConversationStore not available for search")
                return []

            store = get_store(student_id)
            if not store or not store.enabled:
                return []

            return store.search_conversations(
                query=query,
                student_id=student_id,
                session_id=session_id,
                limit=limit
            )
        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Conversation search failed: {e}")
            return []

    def get_cross_session_context(
        self,
        student_id: str,
        query: str,
        current_session_id: str = None,
        max_turns: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant conversation snippets from past sessions.

        Moltbot-style cross-session memory: find related past conversations.

        Args:
            student_id: Student ID
            query: Current context/question
            current_session_id: Exclude this session
            max_turns: Max turns to return

        Returns:
            List of relevant turns from past sessions
        """
        try:
            get_store = _get_conversation_store()
            if not get_store:
                return []

            store = get_store(student_id)
            if not store or not store.enabled:
                return []

            turns = store.get_cross_session_context(
                student_id=student_id,
                query=query,
                current_session_id=current_session_id,
                max_turns=max_turns
            )

            # Convert ConversationTurn objects to dicts
            return [
                {
                    "session_id": t.session_id,
                    "speaker": t.speaker,
                    "text": t.text,
                    "timestamp": t.timestamp.isoformat() if hasattr(t.timestamp, 'isoformat') else str(t.timestamp),
                    "turn_number": t.turn_number,
                }
                for t in turns
            ]
        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Cross-session retrieval failed: {e}")
            return []

    def get_conversation_stats(self, student_id: str) -> Dict[str, Any]:
        """
        Get conversation statistics for a student.

        Returns:
            Dict with total sessions, turns, tokens, etc.
        """
        try:
            get_store = _get_conversation_store()
            if not get_store:
                return {}

            store = get_store(student_id)
            if not store or not store.enabled:
                return {}

            return store.get_student_stats(student_id)
        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Stats retrieval failed: {e}")
            return {}
