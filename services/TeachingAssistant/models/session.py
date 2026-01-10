"""
Session Model - Enhanced session tracking with conversation logs
Based on the Cognitive Memory Pipeline architecture
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class Speaker(str, Enum):
    """Who is speaking in the conversation"""
    ADAM = "adam"
    STUDENT = "student"
    SYSTEM = "system"


class ConversationTurn(BaseModel):
    """A single turn in the conversation"""
    speaker: Speaker
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    emotion: Optional[str] = None  # Detected emotion for this turn
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Instruction(BaseModel):
    """System instruction queued for delivery"""
    instruction_id: str
    text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    delivered: bool = False
    delivered_at: Optional[datetime] = None


class SessionSummary(BaseModel):
    """AI-generated summary of the session"""
    summary_text: str
    topics_covered: List[str] = Field(default_factory=list)
    key_moments: List[str] = Field(default_factory=list)
    emotional_arc: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """
    Enhanced session document for MongoDB.

    Key additions for cognitive memory:
    - Full conversation log with timestamps and emotions
    - Emotional arc tracking across the session
    - Key moments identification
    - AI-generated session summary
    """
    id: str = Field(alias="_id")
    session_id: str
    student_id: str
    user_id: str  # Maps to auth user_id

    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    is_active: bool = True

    # Conversation tracking - NEW for v5
    conversation: List[ConversationTurn] = Field(default_factory=list)
    emotional_arc: List[str] = Field(default_factory=list)
    topics_covered: List[str] = Field(default_factory=list)
    key_moments: List[str] = Field(default_factory=list)

    # Question tracking
    questions_answered: int = 0
    questions_correct: int = 0

    # Session summary - generated at end
    session_summary: Optional[SessionSummary] = None

    # System state
    pending_instructions: List[Instruction] = Field(default_factory=list)
    websocket_connected: bool = False
    sse_connected: bool = False

    # Activity tracking
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    last_conversation_turn: datetime = Field(default_factory=datetime.utcnow)
    last_question_submission: Optional[datetime] = None
    inactivity_prompt_sent: bool = False

    # Expiration for TTL index
    expires_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SessionCreate(BaseModel):
    """Model for creating a new session"""
    student_id: str
    user_id: str


class SessionEndResponse(BaseModel):
    """Response when ending a session"""
    session_id: str
    duration_minutes: float
    questions_answered: int
    questions_correct: int
    topics_covered: List[str]
    emotional_arc: List[str]
    summary: Optional[str] = None
