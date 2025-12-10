from dataclasses import dataclass, field
from typing import Optional, List, Set
import time


@dataclass
class Event:
    type: str
    timestamp: float
    session_id: str
    user_id: str
    data: dict

    @classmethod
    def from_websocket(cls, message: dict) -> 'Event':
        timestamp_str = message.get('data', {}).get('timestamp')
        if timestamp_str:
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
            except:
                timestamp = time.time()
        else:
            timestamp = time.time()

        return cls(
            type=message['type'],
            timestamp=timestamp,
            session_id=message['data']['session_id'],
            user_id=message['data']['user_id'],
            data=message['data']
        )


@dataclass
class SessionContext:
    session_id: str
    user_id: str
    start_time: float

    turn_count: int = 0
    current_speaker: Optional[str] = None
    last_speaker: Optional[str] = None
    last_user_turn_time: Optional[float] = None
    last_adam_turn_time: Optional[float] = None
    last_user_text: Optional[str] = None
    last_adam_text: Optional[str] = None

    conversation_turns: List[dict] = field(default_factory=list)
    MAX_CONVERSATION_HISTORY: int = 50

    last_activity_time: float = field(default_factory=time.time)
    last_question_time: Optional[float] = None
    questions_attempted: int = 0

    last_retrieval_time: Optional[float] = None
    injected_memory_ids: Set[str] = field(default_factory=set)

    has_audio: bool = False
    has_video: bool = False

    def add_turn(self, speaker: str, text: str, timestamp: float):
        turn = {
            'speaker': speaker,
            'text': text,
            'timestamp': timestamp
        }
        self.conversation_turns.append(turn)

        if len(self.conversation_turns) > self.MAX_CONVERSATION_HISTORY:
            self.conversation_turns = self.conversation_turns[-self.MAX_CONVERSATION_HISTORY:]

        self.last_speaker = speaker
        if speaker == 'user':
            self.turn_count += 1
            self.last_user_turn_time = timestamp
            self.last_user_text = text
            self.last_activity_time = timestamp
        elif speaker == 'adam':
            self.last_adam_turn_time = timestamp
            self.last_adam_text = text
            self.last_activity_time = timestamp

    @property
    def is_user_turn(self) -> bool:
        return self.current_speaker == 'user' or \
               (self.last_speaker == 'user' and self.last_user_turn_time and
                (time.time() - self.last_user_turn_time) < 2.0)

    @property
    def is_adam_turn(self) -> bool:
        return self.current_speaker == 'adam' or \
               (self.last_speaker == 'adam' and self.last_adam_turn_time and
                (time.time() - self.last_adam_turn_time) < 2.0)

    @property
    def time_since_activity(self) -> float:
        return time.time() - self.last_activity_time

    def recent_turns(self, n: int = 10) -> List[dict]:
        return self.conversation_turns[-n:]

    def get_user_turns(self) -> List[dict]:
        return [t for t in self.conversation_turns if t['speaker'] == 'user']

    def get_adam_turns(self) -> List[dict]:
        return [t for t in self.conversation_turns if t['speaker'] == 'adam']


class SessionState:
    def __init__(self):
        self.sessions: dict = {}

    def is_active(self, session_id: str) -> bool:
        return session_id in self.sessions and not self.sessions[session_id].get('ended', False)

    def is_ended(self, session_id: str) -> bool:
        return session_id in self.sessions and self.sessions[session_id].get('ended', False)

    def start_session(self, session_id: str, user_id: str, start_time: float):
        self.sessions[session_id] = {
            'user_id': user_id,
            'start_time': start_time,
            'ended': False
        }

    def end_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id]['ended'] = True

