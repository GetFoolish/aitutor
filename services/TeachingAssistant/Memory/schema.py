from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


class MemoryType(Enum):
    ACADEMIC = "academic"
    PERSONAL = "personal"
    PREFERENCE = "preference"
    CONTEXT = "context"


@dataclass
class Memory:
    """
    Represents a student memory with deduplication and recency tracking.
    
    Attributes:
        id: Unique identifier for the memory
        type: Category of memory (academic, personal, preference, context)
        text: The actual memory content
        importance: Importance score (0.0 to 1.0) set by LLM during extraction
        student_id: ID of the student this memory belongs to
        session_id: ID of the session where memory was created
        timestamp: When the memory was created (ISO format)
        metadata: Additional metadata (emotion, topic, etc.)
        counter: Number of times this memory was reinforced (for deduplication)
        first_epoch: Unix timestamp when memory was first created
        last_epoch: Unix timestamp when memory was last reinforced/seen
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType = MemoryType.ACADEMIC
    text: str = ""
    importance: float = 0.5
    student_id: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Deduplication and recency tracking fields
    counter: int = 1
    first_epoch: float = field(default_factory=lambda: datetime.now().timestamp())
    last_epoch: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> dict:
        """Convert Memory object to dictionary for serialization."""
        return {
            'id': self.id,
            'type': self.type.value,
            'text': self.text,
            'importance': self.importance,
            'student_id': self.student_id,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'counter': self.counter,
            'first_epoch': self.first_epoch,
            'last_epoch': self.last_epoch
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        """
        Create Memory object from dictionary.
        
        Args:
            data: Dictionary containing memory fields
            
        Returns:
            Memory object
        """
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=MemoryType(data.get('type', 'academic')),
            text=data.get('text', ''),
            importance=data.get('importance', 0.5),
            student_id=data.get('student_id', ''),
            session_id=data.get('session_id', ''),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            metadata=data.get('metadata', {}),
            counter=data.get('counter', 1),
            first_epoch=data.get('first_epoch', datetime.now().timestamp()),
            last_epoch=data.get('last_epoch', datetime.now().timestamp())
        )

