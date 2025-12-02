from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class MemoryType(str, Enum):
    ACADEMIC = "academic"
    PERSONAL = "personal"
    PREFERENCE = "preference"
    CONTEXT = "context"


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    student_id: str
    type: MemoryType
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }

    def to_dict(self) -> Dict[str, Any]:
        clean_metadata = {k: v for k, v in self.metadata.items() if v is not None}
        data = {
            'id': self.id,
            'student_id': self.student_id,
            'type': self.type.value,
            'text': self.text,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'importance': self.importance,
            'metadata': clean_metadata
        }
        if self.session_id:
            data['session_id'] = self.session_id
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].rstrip('Z'))
        if isinstance(data.get('type'), str):
            data['type'] = MemoryType(data['type'])
        return cls(**data)


class ExtractedMemory(BaseModel):
    type: MemoryType
    text: str
    importance: float = 0.5
    metadata: Dict[str, Any] = Field(default_factory=dict)
