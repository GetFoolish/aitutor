"""
Database modules for TeachingAssistant v5 - Cognitive Memory Pipeline

This module contains:
- StudentManager: MongoDB operations for student data
- MongoDBMemoryStore: Vector search for memories (replaces Pinecone)
"""

from .student_manager import StudentManager

__all__ = [
    "StudentManager",
]
