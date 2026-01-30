"""
Event Processor - Process events and coordinate system components
Based on v4 teaching-assistant branch implementation

Handles:
- Event processing and routing
- Skill execution triggering
- Context updates coordination
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .context import Event, EventType, SessionContext
from .config import TeachingAssistantConfig

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages session contexts with caching and persistence.

    Provides:
    - In-memory context storage
    - Context creation and retrieval
    - Context updates after events
    """

    def __init__(self, config: Optional[TeachingAssistantConfig] = None):
        self.config = config or TeachingAssistantConfig()
        self._contexts: Dict[str, SessionContext] = {}
        logger.info("[CONTEXT_MANAGER] Initialized")

    def get_context(self, session_id: str) -> Optional[SessionContext]:
        """Get context for a session"""
        return self._contexts.get(session_id)

    def create_context(
        self,
        session_id: str,
        user_id: str,
        student_name: Optional[str] = None,
        biography: Optional[str] = None,
        is_first_session: bool = False
    ) -> SessionContext:
        """Create a new session context"""
        context = SessionContext(
            session_id=session_id,
            user_id=user_id,
            student_name=student_name,
            biography=biography,
            is_first_session=is_first_session
        )
        self._contexts[session_id] = context
        logger.info(f"[CONTEXT_MANAGER] Created context for session {session_id}")
        return context

    def get_or_create_context(
        self,
        session_id: str,
        user_id: str,
        **kwargs
    ) -> SessionContext:
        """Get existing context or create new one"""
        if session_id in self._contexts:
            return self._contexts[session_id]
        return self.create_context(session_id, user_id, **kwargs)

    def update_context(
        self,
        session_id: str,
        user_text: Optional[str] = None,
        tutor_text: Optional[str] = None,
        emotion: Optional[str] = None,
        topic: Optional[str] = None,
        memories: Optional[List[Dict[str, Any]]] = None,
        injection: Optional[str] = None
    ):
        """Update context after an event"""
        context = self._contexts.get(session_id)
        if not context:
            logger.warning(f"[CONTEXT_MANAGER] No context for session {session_id}")
            return

        if user_text is not None:
            context.add_turn(user_text, tutor_text or "", emotion)

        if topic:
            context.add_topic(topic)

        if memories:
            context.set_retrieved_memories(memories)

        if injection:
            context.set_pending_injection(injection)

    def delete_context(self, session_id: str):
        """Delete a session context"""
        if session_id in self._contexts:
            del self._contexts[session_id]
            logger.info(f"[CONTEXT_MANAGER] Deleted context for session {session_id}")

    def get_all_sessions(self) -> List[str]:
        """Get all active session IDs"""
        return list(self._contexts.keys())


class EventProcessor:
    """
    Processes events and triggers skill execution.

    Coordinates between:
    - ContextManager (session state)
    - SkillsManager (skill execution)
    - Memory systems (retrieval/extraction)
    """

    def __init__(
        self,
        context_manager: ContextManager,
        skills_manager=None,
        config: Optional[TeachingAssistantConfig] = None
    ):
        self.context_manager = context_manager
        self.skills_manager = skills_manager
        self.config = config or TeachingAssistantConfig()
        logger.info("[EVENT_PROCESSOR] Initialized")

    def process_event(self, event: Event) -> List[str]:
        """
        Process an event and return skill-based injections.

        Args:
            event: Event to process

        Returns:
            List of instruction injections from skills
        """
        context = self.context_manager.get_context(event.session_id)

        if not context:
            logger.warning(f"[EVENT_PROCESSOR] No context for session {event.session_id}")
            return []

        # Update context based on event type
        if event.event_type == EventType.USER_MESSAGE:
            context.add_turn(
                user_text=event.user_text or "",
                tutor_text=event.tutor_text or "",
                emotion=event.detected_emotion
            )

        elif event.event_type == EventType.EMOTION_DETECTED:
            if event.detected_emotion:
                context.current_emotion = event.detected_emotion
                context.emotional_arc.append(event.detected_emotion)

        elif event.event_type == EventType.MEMORY_RETRIEVED:
            if "memories" in event.data:
                context.set_retrieved_memories(event.data["memories"])

        # Execute skills if enabled
        injections = []
        if self.skills_manager and self.config.enable_skills:
            try:
                injections = self.skills_manager.execute_skills(context)
                if injections:
                    logger.info(f"[EVENT_PROCESSOR] Skills generated {len(injections)} injections")
            except Exception as e:
                logger.error(f"[EVENT_PROCESSOR] Skill execution failed: {e}")

        return injections

    def create_event(
        self,
        session_id: str,
        user_id: str,
        event_type: EventType,
        user_text: Optional[str] = None,
        tutor_text: Optional[str] = None,
        emotion: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Create a new event"""
        return Event(
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            user_text=user_text,
            tutor_text=tutor_text,
            detected_emotion=emotion,
            data=data or {}
        )
