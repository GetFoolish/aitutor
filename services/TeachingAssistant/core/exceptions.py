"""
Custom exceptions for TeachingAssistant service.
"""


class TAError(Exception):
    """Base exception for TeachingAssistant service"""
    pass


class DatabaseConnectionError(TAError):
    """Raised when database connection fails"""
    pass


class LLMGenerationError(TAError):
    """Raised when LLM generation fails"""
    pass


class VectorStoreError(TAError):
    """Raised when vector store operations fail"""
    pass


class MemoryRetrievalError(VectorStoreError):
    """Raised when memory retrieval fails"""
    pass


class MemoryConsolidationError(VectorStoreError):
    """Raised when memory consolidation fails"""
    pass


class SessionError(TAError):
    """Raised when session operations fail"""
    pass


class SessionNotFoundError(SessionError):
    """Raised when session is not found"""
    pass


class SessionAlreadyActiveError(SessionError):
    """Raised when trying to create a session when one is already active"""
    pass


class FileOperationError(TAError):
    """Raised when file operations fail"""
    pass


class ConfigurationError(TAError):
    """Raised when configuration is invalid"""
    pass


class ContextError(TAError):
    """Raised when context operations fail"""
    pass
