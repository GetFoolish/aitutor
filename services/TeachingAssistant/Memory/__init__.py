"""
Memory Module - v4 Memory System integrated with v5 Cognitive Pipeline
Handles vector storage, retrieval, extraction, embeddings, and conversation history.

v1-memory additions (Moltbot-inspired):
- ConversationStore: Full conversation history with search and compaction
- ContextBuilder: Intelligent context window management
"""

from .schema import Memory, MemoryType
from .embeddings import get_embeddings_batch, get_query_embedding
from .vector_store import MemoryStore, MemoryConfig
from .retriever import MemoryRetriever
from .extractor import MemoryExtractor

# New Moltbot-inspired modules
from .conversation_store import (
    ConversationStore,
    ConversationTurn,
    CompactionMode,
    CompactionConfig,
    get_conversation_store,
)
from .context_builder import (
    ContextBuilder,
    ContextItem,
    ContextPriority,
    BuiltContext,
    get_context_builder,
)

__all__ = [
    # Original exports
    "Memory",
    "MemoryType",
    "get_embeddings_batch",
    "get_query_embedding",
    "MemoryStore",
    "MemoryConfig",
    "MemoryRetriever",
    "MemoryExtractor",
    # New conversation/context exports
    "ConversationStore",
    "ConversationTurn",
    "CompactionMode",
    "CompactionConfig",
    "get_conversation_store",
    "ContextBuilder",
    "ContextItem",
    "ContextPriority",
    "BuiltContext",
    "get_context_builder",
]
