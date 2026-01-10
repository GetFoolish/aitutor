"""
TeachingAssistant Service - v5 Cognitive Memory Pipeline

This service provides an AI tutoring system with:
- Living Biography system (narrative student profiles)
- Semantic memory search (Pinecone vector database)
- Memory extraction from conversations
- Skills-based instruction injection
- WebSocket/SSE real-time communication
"""

from .teaching_assistant import TeachingAssistant
from .greeting_handler import GreetingHandler
from .session_manager import SessionManager
from .skills_manager import SkillsManager

# Core modules
from .core import (
    BiographerAgent,
    biographer_agent,
    BiographyMemoryExtractor,
    biography_memory_extractor,
    Event,
    EventType,
    SessionContext,
    TeachingAssistantConfig,
    config,
    EventProcessor,
    ContextManager,
)

# Memory modules
from .Memory import (
    Memory,
    MemoryType,
    MemoryStore,
    MemoryConfig,
    MemoryRetriever,
    MemoryExtractor,
    get_embeddings_batch,
    get_query_embedding,
)

# Skills
from .skills import (
    Skill,
    GreetingSkill,
    EmotionResponseSkill,
    MemoryInjectionSkill,
    DEFAULT_SKILLS,
)

# Handlers
from .handlers import InjectionManager

__all__ = [
    # Main classes
    'TeachingAssistant',
    'GreetingHandler',
    'SessionManager',
    'SkillsManager',
    # Core
    'BiographerAgent',
    'biographer_agent',
    'BiographyMemoryExtractor',
    'biography_memory_extractor',
    'Event',
    'EventType',
    'SessionContext',
    'TeachingAssistantConfig',
    'config',
    'EventProcessor',
    'ContextManager',
    # Memory
    'Memory',
    'MemoryType',
    'MemoryStore',
    'MemoryConfig',
    'MemoryRetriever',
    'MemoryExtractor',
    'get_embeddings_batch',
    'get_query_embedding',
    # Skills
    'Skill',
    'GreetingSkill',
    'EmotionResponseSkill',
    'MemoryInjectionSkill',
    'DEFAULT_SKILLS',
    # Handlers
    'InjectionManager',
]
