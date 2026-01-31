"""
Conversation Store - MongoDB-based conversation history with full-text search

Moltbot-inspired improvements:
- Full conversation history storage (like JSONL but in MongoDB)
- Full-text search across all sessions
- Token counting and auto-compaction
- Rolling summarization for old context
- Cross-session conversation retrieval

Features:
- Store every turn with metadata
- Full-text search index for grep-like queries
- Automatic summarization when context exceeds threshold
- Retrieve conversation snippets from any session
"""

import os
import time
import tiktoken
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from dotenv import load_dotenv
load_dotenv()

# Try to use shared logging config
try:
    from shared.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Try Gemini for summarization
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Try MongoDB
try:
    from pymongo import MongoClient, TEXT
    from pymongo.errors import OperationFailure
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False


class CompactionMode(str, Enum):
    """Compaction strategies (Moltbot-inspired)"""
    OFF = "off"              # No compaction, keep everything
    SAFEGUARD = "safeguard"  # Only compact when approaching limit
    AGGRESSIVE = "aggressive" # Actively summarize old content


@dataclass
class CompactionConfig:
    """Configuration for context window management"""
    mode: CompactionMode = CompactionMode.SAFEGUARD
    max_tokens: int = 100000          # Max tokens before compaction triggers
    target_tokens: int = 50000        # Target after compaction
    preserve_recent_turns: int = 10   # Always keep last N turns verbatim
    summarize_chunk_size: int = 20    # Turns to summarize at once
    
    def __post_init__(self):
        self.mode = CompactionMode(os.getenv("COMPACTION_MODE", "safeguard"))
        self.max_tokens = int(os.getenv("COMPACTION_MAX_TOKENS", "100000"))
        self.target_tokens = int(os.getenv("COMPACTION_TARGET_TOKENS", "50000"))
        self.preserve_recent_turns = int(os.getenv("COMPACTION_PRESERVE_RECENT", "10"))


@dataclass
class ConversationTurn:
    """A single conversation turn with metadata"""
    session_id: str
    student_id: str
    speaker: str  # "student", "tutor", "system"
    text: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    turn_number: int = 0
    emotion: Optional[str] = None
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For compaction
    is_summary: bool = False
    summarizes_turns: List[int] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "student_id": self.student_id,
            "speaker": self.speaker,
            "text": self.text,
            "timestamp": self.timestamp,
            "turn_number": self.turn_number,
            "emotion": self.emotion,
            "token_count": self.token_count,
            "metadata": self.metadata,
            "is_summary": self.is_summary,
            "summarizes_turns": self.summarizes_turns,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        return cls(
            session_id=data.get("session_id", ""),
            student_id=data.get("student_id", ""),
            speaker=data.get("speaker", ""),
            text=data.get("text", ""),
            timestamp=data.get("timestamp", datetime.utcnow()),
            turn_number=data.get("turn_number", 0),
            emotion=data.get("emotion"),
            token_count=data.get("token_count", 0),
            metadata=data.get("metadata", {}),
            is_summary=data.get("is_summary", False),
            summarizes_turns=data.get("summarizes_turns", []),
        )


class ConversationStore:
    """
    MongoDB-based conversation store with Moltbot-style features.
    
    Key capabilities:
    - Full conversation history in MongoDB (searchable)
    - Token counting with tiktoken
    - Auto-compaction when context exceeds limits
    - Full-text search across all sessions
    - Cross-session conversation retrieval
    """
    
    def __init__(self, student_id: str = None):
        self.student_id = student_id
        self.config = CompactionConfig()
        self.enabled = False
        
        # Token counter (using cl100k_base for GPT-4/Claude compatibility)
        try:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._tokenizer = None
            logger.warning("[CONVERSATION_STORE] tiktoken not available, using word-based estimation")
        
        # Gemini for summarization
        self._gemini_client = None
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key and GEMINI_AVAILABLE:
            try:
                self._gemini_client = genai.Client(api_key=gemini_key)
                self._gemini_model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
            except Exception as e:
                logger.warning(f"[CONVERSATION_STORE] Gemini init failed: {e}")
        
        # MongoDB
        if not MONGODB_AVAILABLE:
            logger.error("[CONVERSATION_STORE] pymongo not available")
            return
        
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            logger.error("[CONVERSATION_STORE] MONGODB_URI not set")
            return
        
        try:
            self.client = MongoClient(mongodb_uri)
            self.db_name = os.getenv("MONGODB_DB_NAME", "ai_tutor")
            self.db = self.client[self.db_name]
            self.collection = self.db.conversation_history
            self._ensure_indexes()
            self.enabled = True
            logger.info(f"[CONVERSATION_STORE] Initialized (mode={self.config.mode.value})")
        except Exception as e:
            logger.error(f"[CONVERSATION_STORE] Init failed: {e}")
    
    def _ensure_indexes(self):
        """Create indexes for efficient queries"""
        try:
            # Standard indexes
            self.collection.create_index("student_id")
            self.collection.create_index("session_id")
            self.collection.create_index([("student_id", 1), ("session_id", 1)])
            self.collection.create_index([("student_id", 1), ("timestamp", -1)])
            self.collection.create_index("turn_number")
            
            # Full-text search index (Moltbot grep equivalent)
            try:
                self.collection.create_index([("text", TEXT)])
                logger.info("[CONVERSATION_STORE] Full-text search index created")
            except OperationFailure:
                logger.warning("[CONVERSATION_STORE] Full-text index already exists")
            
            logger.info("[CONVERSATION_STORE] Indexes ensured")
        except Exception as e:
            logger.error(f"[CONVERSATION_STORE] Index creation failed: {e}")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text (Moltbot-style token awareness)"""
        if not text:
            return 0
        if self._tokenizer:
            return len(self._tokenizer.encode(text))
        # Fallback: rough word-based estimate
        return len(text.split()) * 1.3
    
    def add_turn(
        self,
        session_id: str,
        speaker: str,
        text: str,
        student_id: str = None,
        emotion: str = None,
        metadata: Dict[str, Any] = None
    ) -> ConversationTurn:
        """
        Add a conversation turn and check for compaction.
        
        Args:
            session_id: Current session
            speaker: "student", "tutor", or "system"
            text: The message text
            student_id: Student ID (uses self.student_id if not provided)
            emotion: Detected emotion
            metadata: Additional metadata
            
        Returns:
            The created ConversationTurn
        """
        if not self.enabled:
            return None
        
        student_id = student_id or self.student_id
        if not student_id:
            logger.error("[CONVERSATION_STORE] No student_id provided")
            return None
        
        # Get next turn number for this session
        last_turn = self.collection.find_one(
            {"session_id": session_id},
            sort=[("turn_number", -1)]
        )
        turn_number = (last_turn.get("turn_number", 0) + 1) if last_turn else 1
        
        # Create turn
        turn = ConversationTurn(
            session_id=session_id,
            student_id=student_id,
            speaker=speaker,
            text=text,
            turn_number=turn_number,
            emotion=emotion,
            token_count=self.count_tokens(text),
            metadata=metadata or {},
        )
        
        # Insert
        self.collection.insert_one(turn.to_dict())
        logger.debug(f"[CONVERSATION_STORE] Added turn {turn_number} ({speaker}): {text[:50]}...")
        
        # Check if compaction needed
        if self.config.mode != CompactionMode.OFF:
            self._maybe_compact(student_id, session_id)
        
        return turn
    
    def get_session_context(
        self,
        session_id: str,
        max_tokens: int = None,
        include_summaries: bool = True
    ) -> Tuple[List[ConversationTurn], int]:
        """
        Get conversation context for a session, respecting token limits.
        
        Moltbot-style: Returns recent turns + summaries of older context.
        
        Args:
            session_id: Session to get context for
            max_tokens: Maximum tokens to return (uses config default if not specified)
            include_summaries: Whether to include summarized context
            
        Returns:
            Tuple of (turns, total_token_count)
        """
        if not self.enabled:
            return [], 0
        
        max_tokens = max_tokens or self.config.target_tokens
        
        # Get all turns for session, sorted by turn number
        cursor = self.collection.find(
            {"session_id": session_id}
        ).sort("turn_number", 1)
        
        all_turns = [ConversationTurn.from_dict(doc) for doc in cursor]
        
        if not all_turns:
            return [], 0
        
        # If within limits, return everything
        total_tokens = sum(t.token_count for t in all_turns)
        if total_tokens <= max_tokens:
            return all_turns, total_tokens
        
        # Need to trim - keep summaries + recent turns
        result = []
        token_count = 0
        
        # First, add any summary turns
        if include_summaries:
            summaries = [t for t in all_turns if t.is_summary]
            for s in summaries:
                result.append(s)
                token_count += s.token_count
        
        # Then add recent non-summary turns (from the end)
        non_summaries = [t for t in all_turns if not t.is_summary]
        for turn in reversed(non_summaries):
            if token_count + turn.token_count > max_tokens:
                break
            result.insert(len([t for t in result if t.is_summary]), turn)
            token_count += turn.token_count
        
        # Sort by turn number
        result.sort(key=lambda t: t.turn_number)
        
        return result, token_count
    
    def search_conversations(
        self,
        query: str,
        student_id: str = None,
        session_id: str = None,
        limit: int = 20,
        days_back: int = None
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across conversations (Moltbot grep equivalent).
        
        Args:
            query: Search query
            student_id: Filter by student (uses self.student_id if not provided)
            session_id: Filter by specific session
            limit: Max results
            days_back: Only search conversations from last N days
            
        Returns:
            List of matching turns with context
        """
        if not self.enabled:
            return []
        
        student_id = student_id or self.student_id
        
        # Build filter
        filter_dict = {}
        if student_id:
            filter_dict["student_id"] = student_id
        if session_id:
            filter_dict["session_id"] = session_id
        if days_back:
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            filter_dict["timestamp"] = {"$gte": cutoff}
        
        # Full-text search
        filter_dict["$text"] = {"$search": query}
        
        try:
            cursor = self.collection.find(
                filter_dict,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            results = []
            for doc in cursor:
                results.append({
                    "session_id": doc.get("session_id"),
                    "turn_number": doc.get("turn_number"),
                    "speaker": doc.get("speaker"),
                    "text": doc.get("text"),
                    "timestamp": doc.get("timestamp"),
                    "score": doc.get("score", 0),
                })
            
            logger.info(f"[CONVERSATION_STORE] Search found {len(results)} results for '{query}'")
            return results
            
        except OperationFailure as e:
            logger.error(f"[CONVERSATION_STORE] Search failed: {e}")
            # Fallback to regex search
            return self._regex_search(query, student_id, session_id, limit)
    
    def _regex_search(
        self,
        query: str,
        student_id: str,
        session_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback regex search when full-text not available"""
        import re
        
        filter_dict = {"text": {"$regex": re.escape(query), "$options": "i"}}
        if student_id:
            filter_dict["student_id"] = student_id
        if session_id:
            filter_dict["session_id"] = session_id
        
        cursor = self.collection.find(filter_dict).limit(limit)
        
        return [{
            "session_id": doc.get("session_id"),
            "turn_number": doc.get("turn_number"),
            "speaker": doc.get("speaker"),
            "text": doc.get("text"),
            "timestamp": doc.get("timestamp"),
            "score": 1.0,
        } for doc in cursor]
    
    def get_cross_session_context(
        self,
        student_id: str,
        query: str,
        current_session_id: str = None,
        max_turns: int = 10
    ) -> List[ConversationTurn]:
        """
        Retrieve relevant conversation snippets from past sessions.
        
        Moltbot-style cross-session memory: search past conversations
        and return relevant context.
        
        Args:
            student_id: Student to search for
            query: Context query (current topic/question)
            current_session_id: Exclude this session
            max_turns: Maximum turns to return
            
        Returns:
            List of relevant turns from past sessions
        """
        # Search for relevant conversations
        search_results = self.search_conversations(
            query=query,
            student_id=student_id,
            limit=max_turns * 2  # Get more to filter
        )
        
        # Filter out current session
        if current_session_id:
            search_results = [
                r for r in search_results 
                if r.get("session_id") != current_session_id
            ]
        
        # Get full turns with surrounding context
        turns = []
        seen_sessions = set()
        
        for result in search_results[:max_turns]:
            session_id = result.get("session_id")
            turn_number = result.get("turn_number")
            
            # Get a few turns of context around the match
            context_cursor = self.collection.find({
                "session_id": session_id,
                "turn_number": {
                    "$gte": max(1, turn_number - 1),
                    "$lte": turn_number + 1
                }
            }).sort("turn_number", 1)
            
            for doc in context_cursor:
                turn = ConversationTurn.from_dict(doc)
                if turn.session_id not in seen_sessions or turn.turn_number == turn_number:
                    turns.append(turn)
            
            seen_sessions.add(session_id)
        
        logger.info(f"[CONVERSATION_STORE] Retrieved {len(turns)} cross-session turns")
        return turns[:max_turns]
    
    def _maybe_compact(self, student_id: str, session_id: str):
        """Check if compaction is needed and perform it"""
        if self.config.mode == CompactionMode.OFF:
            return
        
        # Count total tokens in session
        pipeline = [
            {"$match": {"session_id": session_id, "is_summary": False}},
            {"$group": {"_id": None, "total": {"$sum": "$token_count"}}}
        ]
        result = list(self.collection.aggregate(pipeline))
        total_tokens = result[0]["total"] if result else 0
        
        if total_tokens < self.config.max_tokens:
            return
        
        logger.info(f"[CONVERSATION_STORE] Compaction triggered: {total_tokens} tokens > {self.config.max_tokens}")
        self._compact_session(session_id)
    
    def _compact_session(self, session_id: str):
        """
        Compact old conversation turns into summaries.
        
        Moltbot-style compaction: summarize old turns while preserving
        recent context and important information.
        """
        if not self._gemini_client:
            logger.warning("[CONVERSATION_STORE] No LLM available for summarization")
            return
        
        # Get all non-summary turns
        turns = list(self.collection.find({
            "session_id": session_id,
            "is_summary": False
        }).sort("turn_number", 1))
        
        if len(turns) <= self.config.preserve_recent_turns:
            return
        
        # Turns to summarize (all except recent ones)
        turns_to_summarize = turns[:-self.config.preserve_recent_turns]
        
        # Summarize in chunks
        for i in range(0, len(turns_to_summarize), self.config.summarize_chunk_size):
            chunk = turns_to_summarize[i:i + self.config.summarize_chunk_size]
            self._summarize_chunk(session_id, chunk)
    
    def _summarize_chunk(self, session_id: str, turns: List[Dict]):
        """Summarize a chunk of turns into a single summary turn"""
        if not turns:
            return
        
        # Format turns for summarization
        conversation_text = "\n".join([
            f"{t['speaker'].upper()}: {t['text']}"
            for t in turns
        ])
        
        prompt = f"""Summarize this tutoring conversation segment concisely.
Preserve:
- Key academic concepts discussed
- Student's understanding/struggles
- Important personal details mentioned
- Emotional context

Conversation:
{conversation_text}

Write a brief summary (2-3 sentences) that captures the essential context for future reference."""

        try:
            response = self._gemini_client.models.generate_content(
                model=self._gemini_model,
                contents=prompt,
                config={'temperature': 0.3, 'max_output_tokens': 300}
            )
            summary_text = response.text.strip()
            
            # Get turn numbers being summarized
            turn_numbers = [t["turn_number"] for t in turns]
            min_turn = min(turn_numbers)
            
            # Create summary turn
            summary = {
                "session_id": session_id,
                "student_id": turns[0]["student_id"],
                "speaker": "system",
                "text": f"[SUMMARY of turns {min_turn}-{max(turn_numbers)}]: {summary_text}",
                "timestamp": datetime.utcnow(),
                "turn_number": min_turn - 0.5,  # Place before the summarized turns
                "token_count": self.count_tokens(summary_text),
                "is_summary": True,
                "summarizes_turns": turn_numbers,
                "metadata": {"compaction_time": datetime.utcnow().isoformat()}
            }
            
            # Insert summary
            self.collection.insert_one(summary)
            
            # Delete original turns
            self.collection.delete_many({
                "session_id": session_id,
                "turn_number": {"$in": turn_numbers},
                "is_summary": False
            })
            
            logger.info(
                f"[CONVERSATION_STORE] Compacted {len(turns)} turns into summary "
                f"({sum(t['token_count'] for t in turns)} → {summary['token_count']} tokens)"
            )
            
        except Exception as e:
            logger.error(f"[CONVERSATION_STORE] Summarization failed: {e}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        if not self.enabled:
            return {}
        
        pipeline = [
            {"$match": {"session_id": session_id}},
            {"$group": {
                "_id": None,
                "total_turns": {"$sum": 1},
                "total_tokens": {"$sum": "$token_count"},
                "summary_count": {"$sum": {"$cond": ["$is_summary", 1, 0]}},
                "speakers": {"$addToSet": "$speaker"}
            }}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        if not result:
            return {"total_turns": 0, "total_tokens": 0}
        
        return {
            "total_turns": result[0].get("total_turns", 0),
            "total_tokens": result[0].get("total_tokens", 0),
            "summary_count": result[0].get("summary_count", 0),
            "speakers": result[0].get("speakers", []),
        }
    
    def get_student_stats(self, student_id: str = None) -> Dict[str, Any]:
        """Get statistics across all sessions for a student"""
        if not self.enabled:
            return {}
        
        student_id = student_id or self.student_id
        
        pipeline = [
            {"$match": {"student_id": student_id}},
            {"$group": {
                "_id": "$session_id",
                "turns": {"$sum": 1},
                "tokens": {"$sum": "$token_count"},
                "first_turn": {"$min": "$timestamp"},
                "last_turn": {"$max": "$timestamp"}
            }},
            {"$group": {
                "_id": None,
                "total_sessions": {"$sum": 1},
                "total_turns": {"$sum": "$turns"},
                "total_tokens": {"$sum": "$tokens"},
                "first_session": {"$min": "$first_turn"},
                "last_session": {"$max": "$last_turn"}
            }}
        ]
        
        result = list(self.collection.aggregate(pipeline))
        if not result:
            return {"total_sessions": 0, "total_turns": 0, "total_tokens": 0}
        
        return {
            "total_sessions": result[0].get("total_sessions", 0),
            "total_turns": result[0].get("total_turns", 0),
            "total_tokens": result[0].get("total_tokens", 0),
            "first_session": result[0].get("first_session"),
            "last_session": result[0].get("last_session"),
        }


# Singleton factory
_stores: Dict[str, ConversationStore] = {}

def get_conversation_store(student_id: str = None) -> ConversationStore:
    """Get or create a ConversationStore for a student"""
    key = student_id or "_default"
    if key not in _stores:
        _stores[key] = ConversationStore(student_id)
    return _stores[key]
