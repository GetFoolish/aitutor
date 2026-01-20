"""
Decorators for error handling and retry logic.
"""
import asyncio
import functools
import logging
from typing import Type, Tuple, Optional, Callable, Any

from .exceptions import TAError

logger = logging.getLogger(__name__)

def with_retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,), 
    retries: int = 3, 
    delay: float = 1.0, 
    backoff: float = 2.0,
    fallback: Optional[Callable] = None
):
    """
    Decorator to retry async functions on specific exceptions.
    
    Args:
        exceptions: Tuple of exceptions to catch
        retries: Number of retry attempts
        delay: Initial delay between retries
        backoff: Multiplier for delay after each failure
        fallback: Optional callable to execute if all retries fail
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries:
                        logger.error(f"Function {func.__name__} failed after {retries} retries: {e}")
                        if fallback:
                            return fallback(*args, **kwargs)
                        raise
                    
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt+1}/{retries}): {e}. Retrying in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

class CircuitBreaker:
    """
    Simple circuit breaker pattern for external service calls.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def allow_request(self) -> bool:
        if self.state == "OPEN":
            import time
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                return True
            return False
        return True

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        import time
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPENED after {self.failures} failures")

def with_circuit_breaker(circuit_breaker: CircuitBreaker, fallback_return: Any = None):
    """
    Decorator to protect external calls with a circuit breaker.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not circuit_breaker.allow_request():
                logger.warning(f"Circuit breaker OPEN. Skipping call to {func.__name__}")
                return fallback_return
            
            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                logger.error(f"Call to {func.__name__} failed: {e}")
                raise
        return wrapper
    return decorator
