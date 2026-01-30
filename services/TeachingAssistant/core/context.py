"""
Context Module - Event and Session Context definitions
Based on v4 teaching-assistant branch implementation

Provides dataclasses for managing session state and events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class EventType(str, Enum):
    """Types of events that can occur in a session"""
    USER_MESSAGE = "user_message"
    TUTOR_MESSAGE = "tutor_message"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    MEMORY_RETRIEVED = "memory_retrieved"
    BIOGRAPHY_UPDATED = "biography_updated"
    SKILL_TRIGGERED = "skill_triggered"
    EMOTION_DETECTED = "emotion_detected"
    BREAKTHROUGH = "breakthrough"


@dataclass
class Event:
    """
    Represents an event in the tutoring session.

    Events are processed by the EventProcessor and can trigger
    skill execution or state updates.
    """
    session_id: str
    user_id: str
    event_type: EventType
    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    data: Dict[str, Any] = field(default_factory=dict)

    # User message specific
    user_text: Optional[str] = None
    tutor_text: Optional[str] = None

    # Emotion tracking
    detected_emotion: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)


@dataclass
class SessionContext:
    """
    Context object for a tutoring session.

    Maintains session state and is passed to skills for execution.
    Updated by the ContextManager after each event.
    """
    session_id: str
    user_id: str
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())

    # Conversation state
    turn_count: int = 0
    last_user_text: str = ""
    last_tutor_text: str = ""
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Student info (from biography/profile)
    student_name: Optional[str] = None
    biography: Optional[str] = None
    interests: List[str] = field(default_factory=list)
    learning_preferences: Dict[str, Any] = field(default_factory=dict)

    # Emotional state
    current_emotion: Optional[str] = None
    emotional_arc: List[str] = field(default_factory=list)

    # Academic state
    topics_covered: List[str] = field(default_factory=list)
    current_topic: Optional[str] = None
    difficulty_level: Optional[str] = None

    # Retrieval state
    retrieved_memories: List[Dict[str, Any]] = field(default_factory=list)
    pending_injection: Optional[str] = None

    # Session metadata
    is_first_session: bool = False
    last_session_date: Optional[datetime] = None

    def add_turn(self, user_text: str, tutor_text: str = "", emotion: Optional[str] = None):
        """Add a conversation turn to the context"""
        self.turn_count += 1
        self.last_user_text = user_text
        self.last_tutor_text = tutor_text

        turn = {
            "turn": self.turn_count,
            "user": user_text,
            "tutor": tutor_text,
            "timestamp": datetime.utcnow().isoformat()
        }
        if emotion:
            turn["emotion"] = emotion
            self.current_emotion = emotion
            self.emotional_arc.append(emotion)

        self.conversation_history.append(turn)

    def get_recent_turns(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get the last n conversation turns"""
        return self.conversation_history[-n:] if self.conversation_history else []

    def set_student_info(
        self,
        name: Optional[str] = None,
        biography: Optional[str] = None,
        interests: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ):
        """Update student information in context"""
        if name:
            self.student_name = name
        if biography:
            self.biography = biography
        if interests:
            self.interests = interests
        if preferences:
            self.learning_preferences = preferences

    def add_topic(self, topic: str):
        """Add a topic to the session"""
        if topic and topic not in self.topics_covered:
            self.topics_covered.append(topic)
        self.current_topic = topic

    def set_retrieved_memories(self, memories: List[Dict[str, Any]]):
        """Set retrieved memories for potential injection"""
        self.retrieved_memories = memories

    def set_pending_injection(self, injection: str):
        """Set a pending instruction injection"""
        self.pending_injection = injection

    def clear_pending_injection(self) -> Optional[str]:
        """Get and clear the pending injection"""
        injection = self.pending_injection
        self.pending_injection = None
        return injection

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "turn_count": self.turn_count,
            "student_name": self.student_name,
            "current_emotion": self.current_emotion,
            "emotional_arc": self.emotional_arc,
            "topics_covered": self.topics_covered,
            "current_topic": self.current_topic,
            "is_first_session": self.is_first_session,
            "has_biography": bool(self.biography),
            "has_pending_injection": bool(self.pending_injection),
        }
