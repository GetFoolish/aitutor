"""
Models for TeachingAssistant v5 - Cognitive Memory Pipeline

This module contains Pydantic models for:
- Student: Living Biography and academic journey
- Session: Conversation tracking and emotional arc
- Memory: Individual facts for semantic search
"""

from .student import (
    Student,
    StudentCreate,
    StudentUpdate,
    Biography,
    BiographyVersion,
    OnboardingData,
    AcademicJourney,
    Milestone,
    StudentStatistics,
)

from .session import (
    Session,
    SessionCreate,
    SessionEndResponse,
    SessionSummary,
    ConversationTurn,
    Instruction,
    Speaker,
)

from .memory import (
    Memory,
    MemoryCreate,
    MemoryType,
    MemoryMetadata,
    MemorySearchResult,
    ExtractedMemories,
)

__all__ = [
    # Student models
    "Student",
    "StudentCreate",
    "StudentUpdate",
    "Biography",
    "BiographyVersion",
    "OnboardingData",
    "AcademicJourney",
    "Milestone",
    "StudentStatistics",
    # Session models
    "Session",
    "SessionCreate",
    "SessionEndResponse",
    "SessionSummary",
    "ConversationTurn",
    "Instruction",
    "Speaker",
    # Memory models
    "Memory",
    "MemoryCreate",
    "MemoryType",
    "MemoryMetadata",
    "MemorySearchResult",
    "ExtractedMemories",
]
