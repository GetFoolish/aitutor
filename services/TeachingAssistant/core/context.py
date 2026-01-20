from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict
import time
import re


@dataclass
class Event:
    type: str
    timestamp: float
    session_id: str
    user_id: str
    data: dict

@dataclass
class SessionContext:
    session_id: str
    user_id: str
    start_time: float
    
    # Maximum turns to keep in memory (full history saved to MongoDB)
    MAX_TURNS: int = 50

    turn_count: int = 0
    current_speaker: Optional[str] = None
    last_speaker: Optional[str] = None
    last_user_turn_time: Optional[float] = None
    last_adam_turn_time: Optional[float] = None
    last_user_text: Optional[str] = None
    last_adam_text: Optional[str] = None

    conversation_turns: List[dict] = field(default_factory=list)

    last_activity_time: float = field(default_factory=time.time)
    last_question_time: Optional[float] = None
    questions_attempted: int = 0

    last_retrieval_time: Optional[float] = None
    injected_memory_ids: Set[str] = field(default_factory=set)

    has_audio: bool = False
    has_video: bool = False
    is_dirty: bool = False

    def add_turn(self, speaker: str, text: str, timestamp: float):
        """
        Add a logical conversation turn.
        This method is called from the server AFTER it has already merged streaming chunks
        into a full utterance, so we:
        - avoid saving tiny partial tokens,
        - merge with the previous turn if the same speaker continues speaking quickly,
        - and keep last_* fields in sync for memory extraction.
        """
        # Normalize text - strip, drop noise markers, collapse spaces
        text = (text or "").strip()
        # Remove explicit noise markers used by ASR
        text = text.replace("<noise>", "").strip()
        # Collapse multiple internal spaces
        text = re.sub(r"\s+", " ", text)
        if not text:
            return

        # If last turn is same speaker, always merge instead of appending
        if self.conversation_turns:
            last_turn = self.conversation_turns[-1]
            # Hard de-duplication: if exact same speaker/text, skip
            if last_turn.get("speaker") == speaker and last_turn.get("text") == text:
                return
            if last_turn.get("speaker") == speaker:
                # Merge text with a space
                merged_text = f"{last_turn.get('text', '')} {text}".strip()
                last_turn["text"] = merged_text
                last_turn["timestamp"] = timestamp
                text = merged_text  # for last_* fields below
            else:
                # Different speaker or sufficiently separated -> append new turn
                self.conversation_turns.append(
                    {"speaker": speaker, "text": text, "timestamp": timestamp}
                )
        else:
            # First turn in conversation
            self.conversation_turns.append(
                {"speaker": speaker, "text": text, "timestamp": timestamp}
            )
        
        # Implement rolling window - keep only last MAX_TURNS turns in memory
        if len(self.conversation_turns) > self.MAX_TURNS:
            self.conversation_turns = self.conversation_turns[-self.MAX_TURNS:]

        # Update last speaker and text for memory extraction
        if speaker == "user":
            self.last_user_text = text
            self.turn_count += 1
            self.last_user_turn_time = timestamp
            self.last_activity_time = timestamp
        elif speaker in ("adam", "tutor"):
            # Treat both internal names as the AI side
            self.last_adam_text = text
            self.last_adam_turn_time = timestamp
            self.last_activity_time = timestamp

        self.last_speaker = speaker
    
    def flush_current_turn(self):
        """Flush the current turn buffer to conversation_turns (called at session end)"""
        # No-op: turns are already merged in add_turn, no buffer needed
        pass

    @property
    def time_since_activity(self) -> float:
        return time.time() - self.last_activity_time

    def to_mongodb_dict(self) -> dict:
        """Convert context to MongoDB document format"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "turn_count": self.turn_count,
            "current_speaker": self.current_speaker,
            "last_speaker": self.last_speaker,
            "last_user_turn_time": self.last_user_turn_time,
            "last_adam_turn_time": self.last_adam_turn_time,
            "last_user_text": self.last_user_text,
            "last_adam_text": self.last_adam_text,
            "conversation_turns": self.conversation_turns,  # Save all turns to MongoDB
            "last_activity_time": self.last_activity_time,
            "last_question_time": self.last_question_time,
            "questions_attempted": self.questions_attempted,
            "last_retrieval_time": self.last_retrieval_time,
            "injected_memory_ids": list(self.injected_memory_ids),  # Convert set to list
            "has_audio": self.has_audio,
            "has_video": self.has_video,
        }

    @classmethod
    def from_mongodb_dict(cls, data: dict) -> 'SessionContext':
        """Create context from MongoDB document"""
        context = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            start_time=data.get("start_time", time.time())
        )
        context.turn_count = data.get("turn_count", 0)
        context.current_speaker = data.get("current_speaker")
        context.last_speaker = data.get("last_speaker")
        context.last_user_turn_time = data.get("last_user_turn_time")
        context.last_adam_turn_time = data.get("last_adam_turn_time")
        context.last_user_text = data.get("last_user_text")
        context.last_adam_text = data.get("last_adam_text")
        context.conversation_turns = data.get("conversation_turns", [])
        context.last_activity_time = data.get("last_activity_time", time.time())
        context.last_question_time = data.get("last_question_time")
        context.questions_attempted = data.get("questions_attempted", 0)
        context.last_retrieval_time = data.get("last_retrieval_time")
        context.injected_memory_ids = set(data.get("injected_memory_ids", []))  # Convert list to set
        context.has_audio = data.get("has_audio", False)
        context.has_video = data.get("has_video", False)
        return context

