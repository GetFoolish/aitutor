"""
Configuration Module - TeachingAssistant configuration management
Based on v4 teaching-assistant branch implementation

Centralizes all configuration with environment variable overrides.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TeachingAssistantConfig:
    """
    Configuration for the Teaching Assistant system.

    All settings can be overridden via environment variables.
    """

    # =================================
    # LLM Provider Configuration
    # =================================
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    )
    gemini_text_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_TEXT_MODEL", "gemini-2.0-flash")
    )
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # =================================
    # Vector Database (Pinecone)
    # =================================
    pinecone_api_key: str = field(
        default_factory=lambda: os.getenv("PINECONE_API_KEY", "")
    )
    pinecone_environment: str = field(
        default_factory=lambda: os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    )
    pinecone_index_name: str = field(
        default_factory=lambda: os.getenv("PINECONE_INDEX_NAME", "student-memories")
    )
    embedding_dimension: int = field(
        default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSION", "768"))
    )

    # =================================
    # MongoDB Configuration
    # =================================
    mongodb_uri: str = field(
        default_factory=lambda: os.getenv("MONGODB_URI", "")
    )
    mongodb_db_name: str = field(
        default_factory=lambda: os.getenv("MONGODB_DB_NAME", "ai_tutor")
    )

    # =================================
    # Feature Flags
    # =================================
    enable_biographer: bool = field(
        default_factory=lambda: os.getenv("ENABLE_BIOGRAPHER", "true").lower() == "true"
    )
    enable_memory_extraction: bool = field(
        default_factory=lambda: os.getenv("ENABLE_MEMORY_EXTRACTION", "true").lower() == "true"
    )
    enable_semantic_search: bool = field(
        default_factory=lambda: os.getenv("ENABLE_SEMANTIC_SEARCH", "true").lower() == "true"
    )
    enable_skills: bool = field(
        default_factory=lambda: os.getenv("ENABLE_SKILLS", "true").lower() == "true"
    )

    # =================================
    # Session Configuration
    # =================================
    max_conversation_history: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONVERSATION_HISTORY", "50"))
    )
    deep_retrieval_interval_seconds: int = field(
        default_factory=lambda: int(os.getenv("DEEP_RETRIEVAL_INTERVAL", "180"))
    )
    session_timeout_minutes: int = field(
        default_factory=lambda: int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
    )

    # =================================
    # Memory Configuration
    # =================================
    memory_similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.92"))
    )
    memory_weight_similarity: float = field(
        default_factory=lambda: float(os.getenv("MEMORY_WEIGHT_SIMILARITY", "0.6"))
    )
    memory_weight_recency: float = field(
        default_factory=lambda: float(os.getenv("MEMORY_WEIGHT_RECENCY", "0.3"))
    )
    memory_weight_importance: float = field(
        default_factory=lambda: float(os.getenv("MEMORY_WEIGHT_IMPORTANCE", "0.1"))
    )

    # =================================
    # Injection Configuration
    # =================================
    system_instruction_prefix: str = field(
        default_factory=lambda: os.getenv(
            "SYSTEM_INSTRUCTION_PREFIX",
            "[SYSTEM INSTRUCTION - DO NOT SHOW TO STUDENT]"
        )
    )
    max_injection_length: int = field(
        default_factory=lambda: int(os.getenv("MAX_INJECTION_LENGTH", "1000"))
    )

    # =================================
    # Biographer Configuration
    # =================================
    biography_max_words: int = field(
        default_factory=lambda: int(os.getenv("BIOGRAPHY_MAX_WORDS", "500"))
    )
    biography_min_words: int = field(
        default_factory=lambda: int(os.getenv("BIOGRAPHY_MIN_WORDS", "300"))
    )

    def __post_init__(self):
        """Validate configuration after initialization"""
        # Validate weights sum to 1.0
        total_weight = (
            self.memory_weight_similarity +
            self.memory_weight_recency +
            self.memory_weight_importance
        )
        if not (0.99 <= total_weight <= 1.01):
            import logging
            logging.warning(
                f"[CONFIG] Memory weights sum to {total_weight:.3f}, not 1.0"
            )

    @property
    def has_gemini(self) -> bool:
        """Check if Gemini API key is configured"""
        return bool(self.gemini_api_key)

    @property
    def has_openai(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(self.openai_api_key)

    @property
    def has_pinecone(self) -> bool:
        """Check if Pinecone is configured"""
        return bool(self.pinecone_api_key)

    @property
    def has_mongodb(self) -> bool:
        """Check if MongoDB is configured"""
        return bool(self.mongodb_uri)

    @property
    def llm_provider(self) -> str:
        """Get the primary LLM provider"""
        if self.has_gemini:
            return "gemini"
        elif self.has_openai:
            return "openai"
        return "none"

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings/errors.

        Returns:
            List of warning/error messages
        """
        issues = []

        if not self.has_gemini and not self.has_openai:
            issues.append("ERROR: No LLM provider configured (GEMINI_API_KEY or OPENAI_API_KEY)")

        if not self.has_pinecone and self.enable_semantic_search:
            issues.append("WARNING: Semantic search enabled but PINECONE_API_KEY not set")

        if not self.has_mongodb:
            issues.append("WARNING: MONGODB_URI not set - some features may not work")

        return issues

    def to_dict(self) -> dict:
        """Convert config to dictionary (masking sensitive values)"""
        return {
            "llm_provider": self.llm_provider,
            "has_gemini": self.has_gemini,
            "has_openai": self.has_openai,
            "has_pinecone": self.has_pinecone,
            "has_mongodb": self.has_mongodb,
            "gemini_text_model": self.gemini_text_model,
            "pinecone_index_name": self.pinecone_index_name,
            "embedding_dimension": self.embedding_dimension,
            "enable_biographer": self.enable_biographer,
            "enable_memory_extraction": self.enable_memory_extraction,
            "enable_semantic_search": self.enable_semantic_search,
            "enable_skills": self.enable_skills,
        }


# Singleton instance
config = TeachingAssistantConfig()
