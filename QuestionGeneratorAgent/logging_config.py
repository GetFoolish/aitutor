"""
Logging Configuration for Question Bank Generator

Provides consistent logging across all modules with configurable verbosity.
"""

import logging
import sys
from typing import Optional
from datetime import datetime


# Color codes for terminal output
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.GRAY,
        logging.INFO: Colors.CYAN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.MAGENTA,
    }

    def format(self, record):
        # Add color based on level
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]

        # Build message
        level_name = record.levelname.ljust(8)
        module_name = record.name.split('.')[-1].ljust(20)

        formatted = (
            f"{Colors.GRAY}{timestamp}{Colors.RESET} "
            f"{color}{level_name}{Colors.RESET} "
            f"{Colors.BLUE}{module_name}{Colors.RESET} "
            f"{record.getMessage()}"
        )

        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class DebugLogger:
    """
    Debug logger with context tracking and performance timing.

    Usage:
        logger = get_logger(__name__)
        logger.debug("Processing question", question_id="abc123")

        with logger.timer("generation"):
            # ... do work ...
    """

    def __init__(self, name: str, level: int = logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self._context = {}

        # Add handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(ColoredFormatter())
            self.logger.addHandler(handler)

    def set_context(self, **kwargs):
        """Set persistent context that will be included in all log messages."""
        self._context.update(kwargs)

    def clear_context(self):
        """Clear all context."""
        self._context = {}

    def _format_extras(self, kwargs: dict) -> str:
        """Format extra key-value pairs for logging."""
        all_extras = {**self._context, **kwargs}
        if not all_extras:
            return ""
        parts = [f"{k}={v}" for k, v in all_extras.items()]
        return f" [{', '.join(parts)}]"

    def debug(self, msg: str, **kwargs):
        self.logger.debug(f"{msg}{self._format_extras(kwargs)}")

    def info(self, msg: str, **kwargs):
        self.logger.info(f"{msg}{self._format_extras(kwargs)}")

    def warning(self, msg: str, **kwargs):
        self.logger.warning(f"{msg}{self._format_extras(kwargs)}")

    def error(self, msg: str, **kwargs):
        self.logger.error(f"{msg}{self._format_extras(kwargs)}")

    def critical(self, msg: str, **kwargs):
        self.logger.critical(f"{msg}{self._format_extras(kwargs)}")

    def exception(self, msg: str, **kwargs):
        self.logger.exception(f"{msg}{self._format_extras(kwargs)}")

    class Timer:
        """Context manager for timing operations."""
        def __init__(self, logger: 'DebugLogger', operation: str):
            self.logger = logger
            self.operation = operation
            self.start_time = None

        def __enter__(self):
            self.start_time = datetime.now()
            self.logger.debug(f"Starting: {self.operation}")
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if exc_type:
                self.logger.error(
                    f"Failed: {self.operation}",
                    elapsed_sec=f"{elapsed:.3f}",
                    error=str(exc_val)
                )
            else:
                self.logger.debug(
                    f"Completed: {self.operation}",
                    elapsed_sec=f"{elapsed:.3f}"
                )
            return False

    def timer(self, operation: str) -> Timer:
        """Create a timer context manager."""
        return self.Timer(self, operation)


# Global logger instances cache
_loggers = {}


def get_logger(name: str, level: Optional[int] = None) -> DebugLogger:
    """
    Get or create a logger for the given module name.

    Args:
        name: Module name (usually __name__)
        level: Optional logging level override

    Returns:
        DebugLogger instance
    """
    if name not in _loggers:
        _loggers[name] = DebugLogger(name, level or logging.DEBUG)
    return _loggers[name]


def set_global_level(level: int):
    """Set logging level for all loggers."""
    for logger in _loggers.values():
        logger.logger.setLevel(level)


def enable_debug():
    """Enable debug logging globally."""
    set_global_level(logging.DEBUG)


def enable_info():
    """Set info level logging globally."""
    set_global_level(logging.INFO)


def disable_logging():
    """Disable all logging."""
    set_global_level(logging.CRITICAL + 1)
