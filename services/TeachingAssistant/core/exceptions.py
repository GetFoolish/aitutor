"""
Custom exceptions for TeachingAssistant service.
"""


class TAError(Exception):
    """Base exception for TeachingAssistant service"""


class DatabaseConnectionError(TAError):
    """Raised when database connection fails"""


class LLMGenerationError(TAError):
    """Raised when LLM generation fails"""


class VectorStoreError(TAError):
    """Raised when vector store operations fail"""


class MemoryRetrievalError(VectorStoreError):
    """Raised when memory retrieval fails"""


class MemoryConsolidationError(VectorStoreError):
    """Raised when memory consolidation fails"""


class SessionError(TAError):
    """Raised when session operations fail"""


class SessionNotFoundError(SessionError):
    """Raised when session is not found"""


class SessionAlreadyActiveError(SessionError):
    """Raised when trying to create a session when one is already active"""


class FileOperationError(TAError):
    """Raised when file operations fail"""


class ConfigurationError(TAError):
    """Raised when configuration is invalid"""


class ContextError(TAError):
    """Raised when context operations fail"""
