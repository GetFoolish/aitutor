"""
Context Builder - Intelligent context window construction for LLM prompts

Moltbot-inspired features:
- Token-aware context assembly
- Priority-based content inclusion
- Automatic summarization of old context
- Cross-session memory injection
- Biography + memories + conversation integration

This module builds the optimal LLM context by:
1. Including student biography (high priority)
2. Including retrieved memories (medium priority)
3. Including recent conversation (required)
4. Including summarized old context (if space permits)
5. Including cross-session relevant context (bonus)
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

try:
    from shared.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .conversation_store import ConversationStore, ConversationTurn, get_conversation_store


class ContextPriority(Enum):
    """Priority levels for context content"""
    CRITICAL = 1    # System prompt, current turn
    HIGH = 2        # Biography, recent conversation
    MEDIUM = 3      # Retrieved memories, injections
    LOW = 4         # Old context summaries, cross-session


@dataclass
class ContextItem:
    """A piece of context to include in the LLM prompt"""
    content: str
    token_count: int
    priority: ContextPriority
    source: str  # "biography", "memory", "conversation", "summary", "injection"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuiltContext:
    """The assembled context ready for LLM"""
    items: List[ContextItem]
    total_tokens: int
    included_sources: List[str]
    truncated_sources: List[str]
    
    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to OpenAI-style messages format"""
        messages = []
        
        # Group by source type for cleaner organization
        system_content = []
        conversation = []
        
        for item in self.items:
            if item.source in ["biography", "memory", "injection", "summary"]:
                system_content.append(item.content)
            elif item.source == "conversation":
                # Parse speaker from metadata
                speaker = item.metadata.get("speaker", "user")
                role = "assistant" if speaker == "tutor" else "user"
                conversation.append({"role": role, "content": item.content})
        
        # Build system message if we have content
        if system_content:
            messages.append({
                "role": "system",
                "content": "\n\n".join(system_content)
            })
        
        # Add conversation turns
        messages.extend(conversation)
        
        return messages
    
    def to_text(self) -> str:
        """Convert to plain text format"""
        parts = []
        for item in self.items:
            if item.source == "conversation":
                speaker = item.metadata.get("speaker", "user")
                parts.append(f"{speaker.upper()}: {item.content}")
            else:
                parts.append(item.content)
        return "\n\n".join(parts)


class ContextBuilder:
    """
    Builds optimal LLM context with Moltbot-style intelligence.
    
    Features:
    - Token budget management
    - Priority-based inclusion
    - Automatic truncation of low-priority content
    - Cross-session context retrieval
    """
    
    DEFAULT_MAX_TOKENS = 100000  # Total budget
    DEFAULT_CONVERSATION_TOKENS = 50000  # Reserved for conversation
    DEFAULT_MEMORY_TOKENS = 10000  # Budget for memories
    DEFAULT_BIOGRAPHY_TOKENS = 5000  # Budget for biography
    
    def __init__(
        self,
        max_tokens: int = None,
        conversation_budget: int = None,
        memory_budget: int = None,
        biography_budget: int = None
    ):
        self.max_tokens = max_tokens or int(os.getenv("CONTEXT_MAX_TOKENS", self.DEFAULT_MAX_TOKENS))
        self.conversation_budget = conversation_budget or int(os.getenv("CONTEXT_CONVERSATION_BUDGET", self.DEFAULT_CONVERSATION_TOKENS))
        self.memory_budget = memory_budget or int(os.getenv("CONTEXT_MEMORY_BUDGET", self.DEFAULT_MEMORY_TOKENS))
        self.biography_budget = biography_budget or int(os.getenv("CONTEXT_BIOGRAPHY_BUDGET", self.DEFAULT_BIOGRAPHY_TOKENS))
        
        self._conversation_store = None
        
        logger.info(
            f"[CONTEXT_BUILDER] Initialized with budgets: "
            f"max={self.max_tokens}, conv={self.conversation_budget}, "
            f"mem={self.memory_budget}, bio={self.biography_budget}"
        )
    
    def _get_store(self, student_id: str) -> ConversationStore:
        """Get conversation store for student"""
        return get_conversation_store(student_id)
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        store = self._get_store(None)
        return store.count_tokens(text) if store else len(text.split()) * 1.3
    
    def build_context(
        self,
        session_id: str,
        student_id: str,
        current_message: str = None,
        biography: str = None,
        memories: List[Dict[str, Any]] = None,
        injections: List[str] = None,
        include_cross_session: bool = True
    ) -> BuiltContext:
        """
        Build the optimal context for an LLM call.
        
        Args:
            session_id: Current session
            student_id: Student ID
            current_message: The current user message (if any)
            biography: Student biography text
            memories: Retrieved memories
            injections: System injections
            include_cross_session: Whether to include cross-session context
            
        Returns:
            BuiltContext with assembled content
        """
        items = []
        total_tokens = 0
        included_sources = []
        truncated_sources = []
        
        # Track remaining budget
        remaining = self.max_tokens
        
        # 1. CRITICAL: Current message (if provided)
        if current_message:
            tokens = self._count_tokens(current_message)
            items.append(ContextItem(
                content=current_message,
                token_count=tokens,
                priority=ContextPriority.CRITICAL,
                source="current_message",
                metadata={"speaker": "user"}
            ))
            remaining -= tokens
            total_tokens += tokens
            included_sources.append("current_message")
        
        # 2. HIGH: Biography (truncate if needed)
        if biography:
            bio_tokens = self._count_tokens(biography)
            if bio_tokens > self.biography_budget:
                # Truncate biography
                biography = self._truncate_to_tokens(biography, self.biography_budget)
                bio_tokens = self.biography_budget
                truncated_sources.append("biography")
            
            if bio_tokens <= remaining:
                items.append(ContextItem(
                    content=f"[STUDENT BIOGRAPHY]\n{biography}",
                    token_count=bio_tokens,
                    priority=ContextPriority.HIGH,
                    source="biography"
                ))
                remaining -= bio_tokens
                total_tokens += bio_tokens
                included_sources.append("biography")
        
        # 3. MEDIUM: Injections
        if injections:
            for injection in injections:
                inj_tokens = self._count_tokens(injection)
                if inj_tokens <= remaining:
                    items.append(ContextItem(
                        content=injection,
                        token_count=inj_tokens,
                        priority=ContextPriority.MEDIUM,
                        source="injection"
                    ))
                    remaining -= inj_tokens
                    total_tokens += inj_tokens
            if injections:
                included_sources.append("injections")
        
        # 4. MEDIUM: Retrieved memories
        if memories:
            memory_tokens_used = 0
            memory_texts = []
            
            for mem in memories:
                mem_text = mem.get("text", mem.get("memory", {}).get("text", ""))
                if not mem_text:
                    continue
                
                mem_tokens = self._count_tokens(mem_text)
                if memory_tokens_used + mem_tokens > self.memory_budget:
                    truncated_sources.append("memories")
                    break
                
                memory_texts.append(f"- {mem_text}")
                memory_tokens_used += mem_tokens
            
            if memory_texts:
                combined_memory = "[RELEVANT MEMORIES]\n" + "\n".join(memory_texts)
                combined_tokens = self._count_tokens(combined_memory)
                
                if combined_tokens <= remaining:
                    items.append(ContextItem(
                        content=combined_memory,
                        token_count=combined_tokens,
                        priority=ContextPriority.MEDIUM,
                        source="memory"
                    ))
                    remaining -= combined_tokens
                    total_tokens += combined_tokens
                    included_sources.append("memories")
        
        # 5. HIGH: Recent conversation
        store = self._get_store(student_id)
        if store and store.enabled:
            # Calculate conversation budget (use remaining space, up to limit)
            conv_budget = min(remaining, self.conversation_budget)
            
            turns, conv_tokens = store.get_session_context(
                session_id=session_id,
                max_tokens=conv_budget,
                include_summaries=True
            )
            
            if turns:
                for turn in turns:
                    items.append(ContextItem(
                        content=turn.text,
                        token_count=turn.token_count,
                        priority=ContextPriority.HIGH if not turn.is_summary else ContextPriority.LOW,
                        source="summary" if turn.is_summary else "conversation",
                        metadata={"speaker": turn.speaker, "turn": turn.turn_number}
                    ))
                
                remaining -= conv_tokens
                total_tokens += conv_tokens
                included_sources.append("conversation")
                
                if any(t.is_summary for t in turns):
                    included_sources.append("summaries")
        
        # 6. LOW: Cross-session context (if space permits and enabled)
        if include_cross_session and remaining > 1000 and current_message:
            cross_session_turns = store.get_cross_session_context(
                student_id=student_id,
                query=current_message,
                current_session_id=session_id,
                max_turns=5
            )
            
            if cross_session_turns:
                cross_text = "[RELEVANT PAST CONVERSATIONS]\n"
                cross_tokens = self._count_tokens(cross_text)
                
                for turn in cross_session_turns:
                    turn_text = f"{turn.speaker}: {turn.text}"
                    turn_tokens = self._count_tokens(turn_text)
                    
                    if cross_tokens + turn_tokens > remaining:
                        break
                    
                    cross_text += turn_text + "\n"
                    cross_tokens += turn_tokens
                
                if cross_tokens > self._count_tokens("[RELEVANT PAST CONVERSATIONS]\n"):
                    items.append(ContextItem(
                        content=cross_text,
                        token_count=cross_tokens,
                        priority=ContextPriority.LOW,
                        source="cross_session"
                    ))
                    remaining -= cross_tokens
                    total_tokens += cross_tokens
                    included_sources.append("cross_session")
        
        # Sort by priority (critical first, then high, etc.)
        items.sort(key=lambda x: x.priority.value)
        
        logger.info(
            f"[CONTEXT_BUILDER] Built context: {total_tokens} tokens, "
            f"sources={included_sources}, truncated={truncated_sources}"
        )
        
        return BuiltContext(
            items=items,
            total_tokens=total_tokens,
            included_sources=included_sources,
            truncated_sources=truncated_sources
        )
    
    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget"""
        current_tokens = self._count_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # Estimate chars per token and truncate
        chars_per_token = len(text) / current_tokens
        target_chars = int(max_tokens * chars_per_token * 0.9)  # 10% buffer
        
        truncated = text[:target_chars]
        
        # Try to end at a sentence boundary
        last_period = truncated.rfind('.')
        last_newline = truncated.rfind('\n')
        break_point = max(last_period, last_newline)
        
        if break_point > target_chars * 0.7:  # Don't lose too much
            truncated = truncated[:break_point + 1]
        
        return truncated + "..."
    
    def add_conversation_turn(
        self,
        session_id: str,
        student_id: str,
        speaker: str,
        text: str,
        emotion: str = None
    ) -> Optional[ConversationTurn]:
        """
        Add a turn to conversation history.
        
        Convenience method that delegates to ConversationStore.
        """
        store = self._get_store(student_id)
        if not store or not store.enabled:
            return None
        
        return store.add_turn(
            session_id=session_id,
            student_id=student_id,
            speaker=speaker,
            text=text,
            emotion=emotion
        )
    
    def search_history(
        self,
        query: str,
        student_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search conversation history (Moltbot grep equivalent).
        """
        store = self._get_store(student_id)
        if not store or not store.enabled:
            return []
        
        return store.search_conversations(
            query=query,
            student_id=student_id,
            limit=limit
        )
    
    def get_stats(self, student_id: str, session_id: str = None) -> Dict[str, Any]:
        """Get context/conversation statistics"""
        store = self._get_store(student_id)
        if not store or not store.enabled:
            return {}
        
        stats = store.get_student_stats(student_id)
        
        if session_id:
            stats["current_session"] = store.get_session_stats(session_id)
        
        return stats


# Singleton instance
_context_builder: Optional[ContextBuilder] = None

def get_context_builder() -> ContextBuilder:
    """Get the singleton ContextBuilder instance"""
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilder()
    return _context_builder
