"""
Memory Model - Individual facts extracted from conversations
Based on the Cognitive Memory Pipeline architecture
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    """Type of memory extracted from conversation"""
    PERSONAL = "personal"      # Personal facts (interests, family, events)
    ACADEMIC = "academic"      # Academic progress, breakthroughs, struggles
    EMOTIONAL = "emotional"    # Emotional patterns, reactions
    CONTEXT = "context"        # Contextual information (time, location, events)
    COMMITMENT = "commitment"  # Promises or commitments made


class MemoryMetadata(BaseModel):
    """Additional metadata for a memory"""
    emotion: Optional[str] = None
    topic: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_turn_index: Optional[int] = None  # Index in conversation
    tags: List[str] = Field(default_factory=list)


class Memory(BaseModel):
    """
    Individual memory extracted from a conversation.

    Memories are:
    - Stored in MongoDB for structured queries
    - Embedded and stored in Pinecone for semantic search
    - Used by the Biographer Agent to update biography
    """
    id: str = Field(alias="_id")
    student_id: str
    session_id: str

    # Core memory content
    type: MemoryType
    text: str = Field(description="The memory content")
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score (0-1)"
    )

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: MemoryMetadata = Field(default_factory=MemoryMetadata)

    # For Pinecone sync
    embedding_synced: bool = False
    pinecone_id: Optional[str] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemoryCreate(BaseModel):
    """Model for creating a new memory"""
    student_id: str
    session_id: str
    type: MemoryType
    text: str
    importance: float = 0.5
    metadata: Optional[MemoryMetadata] = None


class MemorySearchResult(BaseModel):
    """Result from semantic memory search"""
    memory: Memory
    similarity_score: float


class ExtractedMemories(BaseModel):
    """Container for memories extracted from a conversation"""
    memories: List[MemoryCreate]
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
