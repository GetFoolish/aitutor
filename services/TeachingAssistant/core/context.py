from dataclasses import dataclass, field
from typing import Optional, List, Set, Dict
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
        """Parse and validate WebSocket message into Event"""
        import logging
        import hashlib
        import json
        logger = logging.getLogger(__name__)
        
        # Validate required fields
        required_fields = ['type', 'data']
        for field in required_fields:
            if field not in message:
                error_msg = f"Missing required field '{field}' in message: {message}"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
        
        # Validate data fields
        data = message.get('data', {})
        required_data_fields = ['session_id', 'user_id']
        for field in required_data_fields:
            if field not in data:
                error_msg = f"Missing required data field '{field}' in message: {message}"
                logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
        
        # Validate message_id and checksum if present
        message_id = message.get('message_id')
        checksum = message.get('checksum')
        if message_id and checksum:
            # Verify checksum (must match server's calculation - without checksum field, no sort_keys)
            try:
                message_copy = {k: v for k, v in message.items() if k != 'checksum'}
                message_json = json.dumps(message_copy, separators=(',', ':'), ensure_ascii=False, sort_keys=False)
                expected_checksum = hashlib.sha256(message_json.encode('utf-8')).hexdigest()
                if checksum != expected_checksum:
                    logger.warning(
                        f"⚠️ Message {message_id} checksum mismatch - possible corruption. "
                        f"Expected: {expected_checksum[:16]}..., Got: {checksum[:16]}..."
                    )
            except Exception as e:
                logger.warning(f"⚠️ Failed to verify checksum for message {message_id}: {e}")
        
        # Parse timestamp
        timestamp_str = data.get('timestamp') or message.get('server_timestamp')
        if timestamp_str:
            try:
                from datetime import datetime
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse timestamp '{timestamp_str}': {e}, using current time")
                timestamp = time.time()
        else:
            timestamp = time.time()
        
        # Log message receipt
        if message_id:
            sequence = message.get('sequence', 'N/A')
            logger.debug(
                f"📥 Received message {message_id} (type: {message.get('type')}, "
                f"seq: {sequence}, session: {data.get('session_id')})"
            )
        
        return cls(
            type=message['type'],
            timestamp=timestamp,
            session_id=data['session_id'],
            user_id=data['user_id'],
            data=data
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
    
    # Accumulate text per speaker until speaker changes
    _current_turn_buffer: Dict[str, str] = field(default_factory=lambda: {'speaker': None, 'text': '', 'timestamp': None})

    last_activity_time: float = field(default_factory=time.time)
    last_question_time: Optional[float] = None
    questions_attempted: int = 0

    last_retrieval_time: Optional[float] = None
    injected_memory_ids: Set[str] = field(default_factory=set)

    has_audio: bool = False
    has_video: bool = False

    def add_turn(self, speaker: str, text: str, timestamp: float):
        # Normalize text - remove extra whitespace
        text = text.strip()
        if not text:
            return
        
        # IMPORTANT: server.js already sends COMPLETE turns (accumulated chunks)
        # So we should store each turn directly, not accumulate again
        # Only accumulate if same speaker sends multiple complete turns (shouldn't happen with server.js)
        
        # Check if this is a duplicate turn before storing
        is_duplicate = False
        if self.conversation_turns:
            last_turn = self.conversation_turns[-1]
            # Check if same speaker, same text, and very close timestamp (< 1 second)
            if (last_turn.get('speaker') == speaker and 
                last_turn.get('text') == text and
                abs(last_turn.get('timestamp', 0) - timestamp) < 1.0):
                is_duplicate = True
        
        # If speaker changed, save the previous speaker's buffered turn (if any)
        if self._current_turn_buffer['speaker'] is not None and self._current_turn_buffer['speaker'] != speaker:
            if self._current_turn_buffer['text']:
                previous_turn = {
                    'speaker': self._current_turn_buffer['speaker'],
                    'text': self._current_turn_buffer['text'],
                    'timestamp': self._current_turn_buffer['timestamp']
                }
                # Check for duplicate before appending
                prev_is_duplicate = False
                if self.conversation_turns:
                    last_turn = self.conversation_turns[-1]
                    if (last_turn.get('speaker') == previous_turn['speaker'] and 
                        last_turn.get('text') == previous_turn['text'] and
                        abs(last_turn.get('timestamp', 0) - previous_turn['timestamp']) < 1.0):
                        prev_is_duplicate = True
                
                if not prev_is_duplicate:
                    self.conversation_turns.append(previous_turn)
        
        # Store the current turn directly (server.js already sent complete turn)
        if not is_duplicate:
            turn = {
                'speaker': speaker,
                'text': text,
                'timestamp': timestamp
            }
            self.conversation_turns.append(turn)
            
            if len(self.conversation_turns) > self.MAX_CONVERSATION_HISTORY:
                self.conversation_turns = self.conversation_turns[-self.MAX_CONVERSATION_HISTORY:]
        
        # Update buffer for next turn (in case of same speaker multiple turns)
        self._current_turn_buffer['speaker'] = speaker
        self._current_turn_buffer['text'] = text
        self._current_turn_buffer['timestamp'] = timestamp
        
        # Update last speaker and text for memory extraction
        if speaker == 'user':
            self.last_user_text = text
            self.turn_count += 1
            self.last_user_turn_time = timestamp
            self.last_activity_time = timestamp
        elif speaker == 'adam':
            self.last_adam_text = text
            self.last_adam_turn_time = timestamp
            self.last_activity_time = timestamp
        
        self.last_speaker = speaker
    
    def flush_current_turn(self):
        """Flush the current turn buffer to conversation_turns (called at session end)"""
        if self._current_turn_buffer['speaker'] and self._current_turn_buffer['text']:
            turn = {
                'speaker': self._current_turn_buffer['speaker'],
                'text': self._current_turn_buffer['text'],
                'timestamp': self._current_turn_buffer['timestamp']
            }
            self.conversation_turns.append(turn)
            
            # Update last speaker and text based on what was flushed
            speaker = self._current_turn_buffer['speaker']
            text = self._current_turn_buffer['text']
            timestamp = self._current_turn_buffer['timestamp']
            
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
            
            if len(self.conversation_turns) > self.MAX_CONVERSATION_HISTORY:
                self.conversation_turns = self.conversation_turns[-self.MAX_CONVERSATION_HISTORY:]
            
            # Reset buffer
            self._current_turn_buffer = {'speaker': None, 'text': '', 'timestamp': None}

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

