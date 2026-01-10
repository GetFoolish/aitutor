"""
Core modules for TeachingAssistant v5 - Cognitive Memory Pipeline

This module contains:
- BiographerAgent: Generates and updates Living Biographies
- BiographyMemoryExtractor: Extracts facts from conversations for biography
- Context: Event and SessionContext dataclasses
- Config: TeachingAssistant configuration
- EventProcessor: Event processing and skill coordination
"""

from .biographer import BiographerAgent, biographer_agent
from .memory_extractor import MemoryExtractor as BiographyMemoryExtractor
from .memory_extractor import memory_extractor as biography_memory_extractor
from .context import Event, EventType, SessionContext
from .config import TeachingAssistantConfig, config
from .event_processor import EventProcessor, ContextManager

__all__ = [
    # Biographer
    "BiographerAgent",
    "biographer_agent",
    # Memory Extraction (for biography)
    "BiographyMemoryExtractor",
    "biography_memory_extractor",
    # Context
    "Event",
    "EventType",
    "SessionContext",
    # Config
    "TeachingAssistantConfig",
    "config",
    # Event Processing
    "EventProcessor",
    "ContextManager",
]
