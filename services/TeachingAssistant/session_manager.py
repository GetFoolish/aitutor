"""
Session Manager for TeachingAssistant
Manages session state in MongoDB instead of in-memory.
Enables multi-user support and survives Cloud Run restarts.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid

from .core.config import TeachingAssistantConfig
from shared.logging_config import get_logger

logger = get_logger(__name__)


class SessionManager:
    """
    Manages session state in MongoDB instead of in-memory.
    Enables multi-user support and survives Cloud Run restarts.
    """

    def __init__(self, mongo_client, config: Optional[TeachingAssistantConfig] = None):
        self.db = mongo_client.db
        self.sessions = self.db.sessions
        self.config = config or TeachingAssistantConfig()
        self._ensure_indexes()

    def _ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            self.sessions.create_index("user_id")
            self.sessions.create_index("session_id", unique=True)
            self.sessions.create_index([("is_active", 1), ("user_id", 1)])
            logger.info("[SESSION_MANAGER] Indexes ensured on sessions collection")
        except Exception as e:
            logger.error(f"[SESSION_MANAGER] Failed to create indexes: {e}")

    def create_session(self, user_id: str) -> Dict[str, Any]:
        """Start a new session for a user"""
        # End any existing active session for this user
        self.end_active_sessions(user_id)

        now = datetime.utcnow()
        session = {
            "session_id": f"sess_{uuid.uuid4().hex[:16]}",
            "user_id": user_id,
            "started_at": now,
            "last_activity": now,
            "ended_at": None,
            "is_active": True,
            "questions_answered_this_session": 0,
            "questions_correct_this_session": 0,
            "last_conversation_turn": now,
            "last_question_submission": None,
            "pending_instructions": [],
            "pending_interventions": [],  # Queue for intervention events to be sent via SSE
            "websocket_connected": False,
            "sse_connected": False,
            "inactivity_prompt_sent": False,  # Track if we've sent an inactivity prompt
            # Struggle tracking fields
            "consecutive_errors": 0,
            "pause_start_time": None,
            "total_pauses": 0,
            "hint_requests": 0,
            "last_struggle_check": now,
            "struggle_score": 0.0,
            # Intervention effectiveness tracking
            "intervention_history": [],
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

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by its ID (alias for get_session_by_id)"""
        return self.get_session_by_id(session_id)

    def update_session(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Update session fields"""
        if updates:
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": updates}
            )

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
                    "last_activity": now
                }
            }
        )

    def record_conversation_turn(self, session_id: str) -> None:
        """Record a conversation turn for inactivity tracking"""
        now = datetime.utcnow()
        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "last_conversation_turn": now,
                    "last_activity": now,
                    "inactivity_prompt_sent": False  # Reset on activity
                }
            }
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

        # Log with colored tag - full instruction text
        logger.info(f"[INSTRUCTION CREATED] {instruction['instruction_id']}: {instruction_text}")

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

    def push_intervention(self, session_id: str, intervention: Dict[str, Any]) -> str:
        """Add an intervention to the pending queue for frontend SSE delivery"""
        intervention_event = {
            "intervention_id": f"intv_{uuid.uuid4().hex[:8]}",
            "type": intervention["type"],
            "message": intervention.get("message", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "delivered": False
        }
        self.sessions.update_one(
            {"session_id": session_id},
            {"$push": {"pending_interventions": intervention_event}}
        )
        logger.info(f"[SESSION_MANAGER] Pushed {intervention['type']} intervention {intervention_event['intervention_id']} to session {session_id}")
        return intervention_event["intervention_id"]

    def get_pending_interventions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all undelivered interventions"""
        session = self.sessions.find_one(
            {"session_id": session_id},
            {"pending_interventions": 1}
        )
        if not session:
            return []
        return [
            intv for intv in session.get("pending_interventions", [])
            if not intv.get("delivered", False)
        ]

    def mark_intervention_delivered(
        self,
        session_id: str,
        intervention_id: str
    ) -> None:
        """Mark an intervention as delivered"""
        self.sessions.update_one(
            {
                "session_id": session_id,
                "pending_interventions.intervention_id": intervention_id
            },
            {"$set": {"pending_interventions.$.delivered": True}}
        )
        logger.info(f"[SESSION_MANAGER] Marked intervention {intervention_id} as delivered")

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

    def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a session and return summary"""
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

        self.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "is_active": False,
                    "ended_at": now,
                    "websocket_connected": False,
                    "sse_connected": False,
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
            "questions_correct": session["questions_correct_this_session"]
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

        # Grace period: don't check inactivity for first N seconds
        if (now - started_at).total_seconds() < self.config.grace_period:
            return False

        # Get the most recent activity time
        last_conversation = session.get("last_conversation_turn") or started_at
        last_question = session.get("last_question_submission") or started_at
        last_activity = max(last_conversation, last_question)

        inactive_seconds = (now - last_activity).total_seconds()
        is_inactive = inactive_seconds >= self.config.inactivity_threshold

        if is_inactive:
            # Mark that we've sent a prompt to avoid spamming
            self.sessions.update_one(
                {"session_id": session_id},
                {"$set": {"inactivity_prompt_sent": True}}
            )

        return is_inactive

    def record_intervention(
        self,
        session_id: str,
        intervention_type: str,
        struggle_score_before: float
    ) -> str:
        """
        Record a new intervention in the session history.
        Returns the intervention_id for later effectiveness tracking.
        """
        intervention = {
            "intervention_id": f"intv_{uuid.uuid4().hex[:8]}",
            "type": intervention_type,
            "timestamp": datetime.utcnow(),
            "struggle_score_before": struggle_score_before,
            "struggle_score_after": None,
            "was_effective": None
        }
        self.sessions.update_one(
            {"session_id": session_id},
            {"$push": {"intervention_history": intervention}}
        )
        logger.info(
            f"[SESSION_MANAGER] Recorded intervention {intervention['intervention_id']} "
            f"of type '{intervention_type}' for session {session_id}"
        )
        return intervention["intervention_id"]

    def update_intervention_effectiveness(
        self,
        session_id: str,
        intervention_id: str,
        struggle_score_after: float
    ) -> None:
        """
        Update an intervention's effectiveness metrics.
        Calculates was_effective based on score reduction.
        """
        session = self.sessions.find_one({"session_id": session_id})
        if not session:
            logger.warning(f"[SESSION_MANAGER] Session {session_id} not found")
            return

        # Find the intervention in history
        intervention_history = session.get("intervention_history", [])
        for i, intervention in enumerate(intervention_history):
            if intervention["intervention_id"] == intervention_id:
                struggle_score_before = intervention["struggle_score_before"]
                # Intervention is effective if struggle score decreased by at least 0.1
                # Use small epsilon (0.001) for floating-point comparison tolerance
                score_reduction = struggle_score_before - struggle_score_after
                was_effective = score_reduction >= (0.1 - 0.001)

                self.sessions.update_one(
                    {
                        "session_id": session_id,
                        "intervention_history.intervention_id": intervention_id
                    },
                    {
                        "$set": {
                            "intervention_history.$.struggle_score_after": struggle_score_after,
                            "intervention_history.$.was_effective": was_effective
                        }
                    }
                )
                logger.info(
                    f"[SESSION_MANAGER] Updated intervention {intervention_id} effectiveness: "
                    f"was_effective={was_effective} (score: {struggle_score_before:.2f} -> {struggle_score_after:.2f})"
                )
                return

        logger.warning(
            f"[SESSION_MANAGER] Intervention {intervention_id} not found in session {session_id}"
        )

    def get_recent_interventions(
        self,
        session_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent interventions for a session"""
        session = self.sessions.find_one(
            {"session_id": session_id},
            {"intervention_history": 1}
        )
        if not session:
            return []

        history = session.get("intervention_history", [])
        # Return most recent interventions (already in chronological order)
        return history[-limit:] if len(history) > limit else history

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
            "session_active": session["is_active"],
            "duration_minutes": round(duration_minutes, 2),
            "questions_answered": session["questions_answered_this_session"],
            "questions_correct": session["questions_correct_this_session"],
            "websocket_connected": session["websocket_connected"],
            "sse_connected": session["sse_connected"]
        }
