"""
Shared logging configuration for all services
Provides structured, consistent logging across the application
"""
import logging
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for development/console output
    """
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BLUE = '\033[34m'
    RED = '\033[31m'

    def format(self, record: logging.LogRecord) -> str:
        # Make a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)
        color = self.COLORS.get(record_copy.levelname, self.RESET)
        record_copy.levelname = f"{color}{record_copy.levelname}{self.RESET}"

        # Color specific message tags
        message = record_copy.getMessage()
        if '[CONVERSATION]' in message:
            message = message.replace('[CONVERSATION]', f'{self.BLUE}[CONVERSATION]{self.RESET}')
        if '[INSTRUCTION → TUTOR]' in message or '[INSTRUCTION' in message:
            message = message.replace('[INSTRUCTION → TUTOR]', f'{self.RED}[INSTRUCTION → TUTOR]{self.RESET}')
            message = message.replace('[INSTRUCTION CREATED]', f'{self.RED}[INSTRUCTION CREATED]{self.RESET}')
            message = message.replace('[INSTRUCTION CREATED/ADMIN]', f'{self.RED}[INSTRUCTION CREATED/ADMIN]{self.RESET}')

        record_copy.msg = message
        record_copy.args = ()

        formatted_message = super().format(record_copy)

        # Sanitize for console encoding on Windows to prevent UnicodeEncodeError
        # This ensures that non-printable characters (like Hindi) don't crash the console
        if sys.platform == 'win32' and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
            try:
                return formatted_message.encode(sys.stdout.encoding, 'replace').decode(sys.stdout.encoding)
            except Exception:
                pass

        return formatted_message


def setup_logger(
    name: str,
    level: str = "INFO",
    structured: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup a logger with consistent configuration
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use JSON structured logging (for production)
        log_file: Optional path to log file (relative to project root or absolute)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Choose formatter based on environment
    if structured:
        formatter = StructuredFormatter()
        console_formatter = formatter
        file_formatter = formatter
    else:
        # Use colored format for BOTH file and console (no timestamps)
        file_formatter = ColoredFormatter(
            '%(levelname)-8s | %(message)s | %(filename)s:%(lineno)d'
        )
        # Use colored format for console (no timestamps, cleaner for interactive use)
        console_formatter = ColoredFormatter(
            '%(levelname)s | %(message)s | %(filename)s:%(lineno)d'
        )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_file is specified
    if log_file:
        try:
            # Determine project root (this file is in aitutor/shared/, so parent.parent.parent is aitutor/)
            # We want logs to be in aitutor/logs/, so use the aitutor directory as base
            current_file = Path(__file__).resolve()
            # aitutor/shared/logging_config.py -> aitutor/
            aitutor_root = current_file.parent.parent
            
            # If log_file is absolute, use it as-is; otherwise make it relative to aitutor root
            if os.path.isabs(log_file):
                log_path = Path(log_file)
            else:
                log_path = aitutor_root / log_file
            
            # Create logs directory if it doesn't exist
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file handler with append mode and immediate flushing
            class ImmediateFlushFileHandler(logging.FileHandler):
                """File handler that flushes after each emit"""
                def emit(self, record):
                    super().emit(record)
                    self.flush()
            
            file_handler = ImmediateFlushFileHandler(log_path, mode='a', encoding='utf-8')
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(file_formatter)
            
            logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, log to console but don't crash
            # Use a temporary logger since the main one might not be set up yet
            temp_logger = logging.getLogger("logging_config")
            temp_logger.warning(f"Failed to setup file logging to {log_file}: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Convenience function for getting a logger
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with default configuration
    
    Automatically detects service-specific log files based on logger name:
    - services.TeachingAssistant.* -> logs/teaching_assistant.log
    - services.DashSystem.* -> logs/dash_api.log
    - services.AuthService.* -> logs/auth_service.log
    - services.SherlockEDApi.* -> logs/sherlocked_exam.log
    
    Usage:
        from shared.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Message")
    """
    level = os.getenv("LOG_LEVEL", "INFO")
    structured = os.getenv("ENVIRONMENT", "development") == "production"
    
    # Determine log file based on logger name
    log_file = None
    if "TeachingAssistant" in name:
        log_file = "logs/teaching_assistant.log"
    elif "DashSystem" in name or "dash_api" in name:
        log_file = "logs/dash_api.log"
    elif "AuthService" in name or "auth_api" in name:
        log_file = "logs/auth_service.log"
    elif "SherlockEDApi" in name or "sherlocked" in name.lower():
        log_file = "logs/sherlocked_exam.log"
    
    return setup_logger(name, level, structured, log_file)
