"""
Retry and error handling utilities for external API calls
Provides decorators and utilities for resilient service calls
"""
import time
import functools
from typing import Callable, TypeVar, Any, Optional
from shared.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function with exponential backoff
    
    Args:
        retries: Number of retry attempts
        backoff_factor: Multiplier for wait time between retries
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
    
    Example:
        @retry_with_backoff(retries=3, backoff_factor=2)
        def call_external_api():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == retries - 1:
                        # Last attempt failed, raise the exception
                        logger.error(
                            f"{func.__name__} failed after {retries} attempts",
                            exc_info=True
                        )
                        raise
                    
                    # Calculate wait time with exponential backoff
                    wait_time = backoff_factor ** attempt
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{retries}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(wait_time)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def safe_execute(
    func: Callable[..., T],
    default: Optional[T] = None,
    log_errors: bool = True
) -> Optional[T]:
    """
    Safely execute a function and return default value on error
    
    Args:
        func: Function to execute
        default: Default value to return on error
        log_errors: Whether to log errors
    
    Returns:
        Function result or default value
    
    Example:
        result = safe_execute(lambda: risky_operation(), default=[])
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
        return default


class RetryableError(Exception):
    """Exception that should trigger a retry"""


class NonRetryableError(Exception):
    """Exception that should NOT trigger a retry"""


# Specific retry decorators for common use cases

def retry_on_network_error(retries: int = 3):
    """Retry on network-related errors"""
    import requests
    return retry_with_backoff(
        retries=retries,
        exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException,
        )
    )


def retry_on_database_error(retries: int = 3):
    """Retry on database-related errors"""
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    return retry_with_backoff(
        retries=retries,
        exceptions=(
            ConnectionFailure,
            ServerSelectionTimeoutError,
        )
    )


def retry_on_api_error(retries: int = 3):
    """Retry on API call errors"""
    return retry_with_backoff(
        retries=retries,
        exceptions=(
            RetryableError,
            ConnectionError,
            TimeoutError,
        )
    )


# Context manager for graceful error handling

class ErrorHandler:
    """
    Context manager for graceful error handling
    
    Example:
        with ErrorHandler("Processing user data"):
            process_user_data()
    """
    def __init__(
        self,
        operation: str,
        raise_on_error: bool = False,
        default_return: Any = None
    ):
        self.operation = operation
        self.raise_on_error = raise_on_error
        self.default_return = default_return
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            logger.error(
                f"Error during {self.operation}: {str(exc_val)}",
                exc_info=True
            )
            
            if self.raise_on_error:
                return False  # Re-raise the exception
            
            return True  # Suppress the exception
        
        return True
