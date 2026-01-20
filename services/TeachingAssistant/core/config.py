"""
Configuration Management for TeachingAssistant
Centralized configuration with environment variable support.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TeachingAssistantConfig:
    """
    Centralized configuration for TeachingAssistant service.
    All settings can be overridden via environment variables.
    """
    
    # ============================================================================
    # Paths Configuration
    # ============================================================================
    base_data_path: Path = field(default_factory=lambda: Path("services/TeachingAssistant/Memory/data"))
    
    # ============================================================================
    # Session Management
    # ============================================================================
    session_sync_interval: float = 1.0  # Seconds between session cache refreshes
    context_sync_interval: float = 1.0  # Seconds between context DB syncs
    inactivity_threshold: int = 60  # Seconds before considering session inactive
    grace_period: int = 60  # Seconds grace period after session start
    
    # ============================================================================
    # Memory Management
    # ============================================================================
    memory_retrieval_debounce: float = 5.0  # Seconds between memory retrievals
    
    # ============================================================================
    # Event Processing
    # ============================================================================
    event_batch_size: int = 5  # Maximum events to process in one batch
    
    # ============================================================================
    # Thread Pool Configuration
    # ============================================================================
    io_thread_pool_workers: int = 4  # Workers for blocking I/O operations
    thread_name_prefix: str = "ta_io"
    
    # ============================================================================
    # Circuit Breaker Settings
    # ============================================================================
    llm_failure_threshold: int = 5  # Failures before opening circuit
    llm_recovery_timeout: float = 60.0  # Seconds before attempting recovery
    vector_store_failure_threshold: int = 5
    vector_store_recovery_timeout: float = 60.0
    
    # ============================================================================
    # Retry Configuration
    # ============================================================================
    default_retry_attempts: int = 3
    default_retry_delay: float = 1.0
    default_retry_backoff: float = 2.0
    
    # ============================================================================
    # File Names
    # ============================================================================
    opening_retrieval_file: str = "TA-opening-retrieval.json"
    closing_retrieval_file: str = "TA-closing-retrieval.json"
    
    # ============================================================================
    # System Prompts
    # ============================================================================
    system_prompt_prefix: str = "[SYSTEM PROMPT FOR ADAM]"
    system_instruction_prefix: str = "[SYSTEM INSTRUCTION]"
    
    @classmethod
    def from_env(cls) -> 'TeachingAssistantConfig':
        """
        Load configuration from environment variables.
        Environment variables should be prefixed with TA_
        """
        config = cls()
        
        # Override from environment variables if present
        if env_val := os.getenv('TA_BASE_DATA_PATH'):
            config.base_data_path = Path(env_val)
        
        if env_val := os.getenv('TA_SESSION_SYNC_INTERVAL'):
            config.session_sync_interval = float(env_val)
            
        if env_val := os.getenv('TA_CONTEXT_SYNC_INTERVAL'):
            config.context_sync_interval = float(env_val)
            
        if env_val := os.getenv('TA_INACTIVITY_THRESHOLD'):
            config.inactivity_threshold = int(env_val)
            
        if env_val := os.getenv('TA_GRACE_PERIOD'):
            config.grace_period = int(env_val)
            
        if env_val := os.getenv('TA_MEMORY_RETRIEVAL_DEBOUNCE'):
            config.memory_retrieval_debounce = float(env_val)
            
        if env_val := os.getenv('TA_EVENT_BATCH_SIZE'):
            config.event_batch_size = int(env_val)
            
        if env_val := os.getenv('TA_IO_THREAD_POOL_WORKERS'):
            config.io_thread_pool_workers = int(env_val)
            
        if env_val := os.getenv('TA_LLM_FAILURE_THRESHOLD'):
            config.llm_failure_threshold = int(env_val)
            
        if env_val := os.getenv('TA_LLM_RECOVERY_TIMEOUT'):
            config.llm_recovery_timeout = float(env_val)
            
        if env_val := os.getenv('TA_DEFAULT_RETRY_ATTEMPTS'):
            config.default_retry_attempts = int(env_val)
            
        if env_val := os.getenv('TA_DEFAULT_RETRY_DELAY'):
            config.default_retry_delay = float(env_val)
        
        return config
    
    def get_user_data_path(self, user_id: str) -> Path:
        """Get the data directory path for a specific user"""
        return self.base_data_path / user_id
    
    def get_memory_path(self, user_id: str) -> Path:
        """Get the memory directory path for a specific user"""
        return self.base_data_path / user_id / "memory" / "TeachingAssistant"
    
    def get_conversations_path(self, user_id: str) -> Path:
        """Get the conversations directory path for a specific user"""
        return self.base_data_path / user_id / "conversations"
    
    def get_opening_retrieval_path(self, user_id: str) -> Path:
        """Get the opening retrieval file path for a specific user"""
        return self.get_memory_path(user_id) / self.opening_retrieval_file
    
    def get_closing_retrieval_path(self, user_id: str) -> Path:
        """Get the closing retrieval file path for a specific user"""
        return self.get_memory_path(user_id) / self.closing_retrieval_file
