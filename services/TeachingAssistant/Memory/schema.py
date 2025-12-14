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
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType = MemoryType.ACADEMIC
    text: str = ""
    importance: float = 0.5
    student_id: str = ""
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.type.value,
            'text': self.text,
            'importance': self.importance,
            'student_id': self.student_id,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Memory':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=MemoryType(data.get('type', 'academic')),
            text=data.get('text', ''),
            importance=data.get('importance', 0.5),
            student_id=data.get('student_id', ''),
            session_id=data.get('session_id', ''),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )

