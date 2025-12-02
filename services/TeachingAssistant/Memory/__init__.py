from .schema import Memory, MemoryType
from .vector_store import MemoryStore
from .extractor import MemoryExtractor
from .retriever import MemoryRetriever, MemoryRetrievalWatcher
from .consolidator import (
    SessionClosingCache,
    OpeningContextCache,
    MemoryConsolidator,
    ConversationWatcher
    # run_memory_watcher  # COMMENTED: File polling disabled - function is commented out in consolidator.py
)

__all__ = [
    'Memory',
    'MemoryType',
    'MemoryStore',
    'MemoryExtractor',
    'MemoryRetriever',
    'MemoryRetrievalWatcher',
    'SessionClosingCache',
    'OpeningContextCache',
    'MemoryConsolidator',
    'ConversationWatcher',
    # 'run_memory_watcher',  # COMMENTED: File polling disabled
]
