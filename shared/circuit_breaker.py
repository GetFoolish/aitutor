"""
Circuit Breaker Pattern Implementation
Prevents cascading failures by failing fast when external services are down.
"""
import time
from enum import Enum
from typing import Callable, Any
from functools import wraps
import asyncio


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Phase 3: Add strict timeouts, retries, and circuit breakers for external dependencies
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 30.0,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
            else:
                raise Exception(f"Circuit breaker OPEN for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
            else:
                raise Exception(f"Circuit breaker OPEN for {func.__name__}")
        
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )
            self._on_success()
            return result
        except (self.expected_exception, asyncio.TimeoutError) as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Reset failure count on successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Increment failure count and open circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_failure_time = time.time()
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time
        }


def circuit_breaker(
    failure_threshold: int = 5,
    timeout: float = 30.0,
    recovery_timeout: float = 60.0
):
    """
    Decorator for circuit breaker pattern.
    
    Usage:
        @circuit_breaker(failure_threshold=3, timeout=10.0)
        async def call_external_api():
            ...
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        timeout=timeout,
        recovery_timeout=recovery_timeout
    )
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)
        return wrapper
    return decorator


# Pre-configured circuit breakers for common services
gemini_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout=30.0,
    recovery_timeout=60.0
)

database_breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=10.0,
    recovery_timeout=30.0
)

external_api_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout=15.0,
    recovery_timeout=45.0
)
