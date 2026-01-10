"""
Database modules for TeachingAssistant v5 - Cognitive Memory Pipeline

This module contains:
- PineconeClient: Semantic vector search for memories
- StudentManager: MongoDB operations for student data
"""

from .pinecone_client import PineconeClient, pinecone_client
from .student_manager import StudentManager

__all__ = [
    "PineconeClient",
    "pinecone_client",
    "StudentManager",
]
