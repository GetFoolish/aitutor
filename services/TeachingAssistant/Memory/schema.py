"""
Memory Schema - v4 dataclass definitions for Memory system
Based on the v4 teaching-assistant branch implementation

Supports deduplication tracking with counter, first_epoch, last_epoch
"""

import uuid
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class MemoryType(str, Enum):
    """Types of memories that can be extracted from conversations"""
    ACADEMIC = "academic"
    PERSONAL = "personal"
    PREFERENCE = "preference"
    CONTEXT = "context"
    EMOTIONAL = "emotional"
    COMMITMENT = "commitment"


@dataclass
class Memory:
    """
    Memory dataclass with deduplication support.

    Attributes:
        id: Unique identifier for the memory
        student_id: ID of the student this memory belongs to
        session_id: ID of the session where memory was extracted
        type: Type of memory (academic, personal, etc.)
        text: The actual memory content
        importance: Importance score (0.0-1.0)
        timestamp: When the memory was created
        counter: Number of times this memory has been reinforced (dedup)
        first_epoch: Unix timestamp when memory was first created
        last_epoch: Unix timestamp when memory was last seen/reinforced
        metadata: Additional metadata (emotion, valence, category, etc.)
    """
    student_id: str
    session_id: str
    type: MemoryType
    text: str
    importance: float = 0.5
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    counter: int = 1  # Deduplication counter
    first_epoch: float = field(default_factory=time.time)
    last_epoch: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure type is MemoryType enum"""
        if isinstance(self.type, str):
            self.type = MemoryType(self.type)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "session_id": self.session_id,
            "type": self.type.value,
            "text": self.text,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "counter": self.counter,
            "first_epoch": self.first_epoch,
            "last_epoch": self.last_epoch,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create Memory from dictionary"""
        # Handle timestamp parsing
        timestamp = data.get("timestamp", datetime.utcnow())
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()

        # Handle memory type
        mem_type = data.get("type", "personal")
        if isinstance(mem_type, str):
            try:
                mem_type = MemoryType(mem_type)
            except ValueError:
                mem_type = MemoryType.PERSONAL

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            student_id=data.get("student_id", ""),
            session_id=data.get("session_id", ""),
            type=mem_type,
            text=data.get("text", ""),
            importance=float(data.get("importance", 0.5)),
            timestamp=timestamp,
            counter=int(data.get("counter", 1)),
            first_epoch=float(data.get("first_epoch", time.time())),
            last_epoch=float(data.get("last_epoch", time.time())),
            metadata=data.get("metadata", {}),
        )

    def merge_with(self, other: "Memory") -> "Memory":
        """
        Merge this memory with another (for deduplication).
        Keeps the higher importance and increments counter.
        """
        return Memory(
            id=self.id,  # Keep original ID
            student_id=self.student_id,
            session_id=other.session_id,  # Use latest session
            type=self.type,
            text=other.text,  # Use latest text version
            importance=max(self.importance, other.importance),
            timestamp=other.timestamp,  # Use latest timestamp
            counter=self.counter + 1,
            first_epoch=self.first_epoch,  # Keep original first_epoch
            last_epoch=time.time(),  # Update last_epoch
            metadata={**self.metadata, **other.metadata},  # Merge metadata
        )


@dataclass
class MemorySearchResult:
    """Result from memory search with scoring details"""
    memory: Memory
    vector_similarity: float
    recency_score: float = 0.0
    importance_score: float = 0.0
    final_score: float = 0.0

    @property
    def score(self) -> float:
        """Alias for final_score for backward compatibility"""
        return self.final_score
