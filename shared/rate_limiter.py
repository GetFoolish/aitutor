"""
Rate limiting middleware for FastAPI services

Implements a sliding window rate limiter with multiple tiers:
- Per-user rate limiting for authenticated requests
- Per-IP rate limiting for unauthenticated/anonymous requests
- Configurable limits and time windows

Rate limiting uses in-memory storage with automatic cleanup.
For production with multiple instances, consider Redis-based rate limiting.
"""
import time
from collections import defaultdict
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from threading import Lock
from fastapi import Request, HTTPException
from shared.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    # Maximum requests per time window
    max_requests: int
    # Time window in seconds
    window_seconds: int
    # Time to keep rate limit records after last request (for cleanup)
    cleanup_after_seconds: int = 3600


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter with per-user and per-IP tracking

    Uses a sliding window algorithm for accurate rate limiting.
    Automatically cleans up old entries to prevent memory leaks.
    """

    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter

        Args:
            config: Rate limit configuration
        """
        self.config = config
        # Store timestamps of requests: {identifier: [timestamp1, timestamp2, ...]}
        self.request_history: Dict[str, list] = defaultdict(list)
        # Lock for thread-safe operations
        self.lock = Lock()
        # Track last cleanup time
        self.last_cleanup = time.time()
        # Cleanup interval (run cleanup every 5 minutes)
        self.cleanup_interval = 300

    def _cleanup_old_entries(self):
        """Remove old entries from request history to prevent memory leaks"""
        current_time = time.time()

        # Only cleanup periodically
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        with self.lock:
            cutoff_time = current_time - self.config.cleanup_after_seconds
            identifiers_to_remove = []

            for identifier, timestamps in self.request_history.items():
                # Remove timestamps older than cleanup threshold
                self.request_history[identifier] = [
                    ts for ts in timestamps if ts > cutoff_time
                ]

                # If no recent requests, mark identifier for removal
                if not self.request_history[identifier]:
                    identifiers_to_remove.append(identifier)

            # Remove identifiers with no recent requests
            for identifier in identifiers_to_remove:
                del self.request_history[identifier]

            self.last_cleanup = current_time

            if identifiers_to_remove:
                logger.debug(f"[RATE-LIMIT] Cleaned up {len(identifiers_to_remove)} inactive rate limit entries")

    def check_rate_limit(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed under rate limit

        Args:
            identifier: Unique identifier (user_id or IP address)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            - is_allowed: True if request should be allowed
            - retry_after_seconds: If blocked, seconds until next request allowed
        """
        current_time = time.time()
        window_start = current_time - self.config.window_seconds

        with self.lock:
            # Get request history for this identifier
            timestamps = self.request_history[identifier]

            # Remove timestamps outside the current window
            recent_timestamps = [ts for ts in timestamps if ts > window_start]

            # Check if under limit
            if len(recent_timestamps) < self.config.max_requests:
                # Add current request timestamp
                recent_timestamps.append(current_time)
                self.request_history[identifier] = recent_timestamps

                # Trigger cleanup if needed
                self._cleanup_old_entries()

                return True, None
            else:
                # Rate limit exceeded - calculate retry time
                oldest_timestamp = min(recent_timestamps)
                retry_after = int(oldest_timestamp + self.config.window_seconds - current_time) + 1

                logger.warning(
                    f"[RATE-LIMIT] Rate limit exceeded for {identifier}: "
                    f"{len(recent_timestamps)}/{self.config.max_requests} requests in "
                    f"{self.config.window_seconds}s window"
                )

                return False, retry_after

    def get_usage_stats(self, identifier: str) -> Dict:
        """
        Get current rate limit usage stats for an identifier

        Args:
            identifier: Unique identifier (user_id or IP address)

        Returns:
            Dictionary with usage statistics
        """
        current_time = time.time()
        window_start = current_time - self.config.window_seconds

        with self.lock:
            timestamps = self.request_history.get(identifier, [])
            recent_timestamps = [ts for ts in timestamps if ts > window_start]

            return {
                "requests_in_window": len(recent_timestamps),
                "max_requests": self.config.max_requests,
                "window_seconds": self.config.window_seconds,
                "remaining": max(0, self.config.max_requests - len(recent_timestamps)),
                "reset_at": int(min(recent_timestamps, default=current_time) + self.config.window_seconds)
            }


# Global rate limiter instances for different tiers
# These can be configured based on environment variables or service requirements

# Strict rate limit for file uploads (resource-intensive)
UPLOAD_RATE_LIMITER = SlidingWindowRateLimiter(
    RateLimitConfig(
        max_requests=10,      # 10 uploads
        window_seconds=300,   # per 5 minutes
        cleanup_after_seconds=3600
    )
)

# Moderate rate limit for AI assistance (API costs)
ASSIST_RATE_LIMITER = SlidingWindowRateLimiter(
    RateLimitConfig(
        max_requests=30,      # 30 questions
        window_seconds=60,    # per minute
        cleanup_after_seconds=3600
    )
)

# Lenient rate limit for general API calls (list, get, delete)
GENERAL_RATE_LIMITER = SlidingWindowRateLimiter(
    RateLimitConfig(
        max_requests=100,     # 100 requests
        window_seconds=60,    # per minute
        cleanup_after_seconds=3600
    )
)


def get_client_identifier(request: Request, user_id: Optional[str] = None) -> str:
    """
    Get unique identifier for rate limiting

    Prefers user_id for authenticated requests, falls back to IP address.

    Args:
        request: FastAPI request object
        user_id: User ID from authentication (if available)

    Returns:
        Unique identifier string
    """
    if user_id:
        return f"user:{user_id}"

    # Get IP address from various headers (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, use the first one
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.headers.get("X-Real-IP") or request.client.host

    return f"ip:{ip}"


def check_rate_limit(
    request: Request,
    rate_limiter: SlidingWindowRateLimiter,
    user_id: Optional[str] = None
):
    """
    Check rate limit and raise HTTPException if exceeded

    Args:
        request: FastAPI request object
        rate_limiter: Rate limiter instance to use
        user_id: User ID from authentication (if available)

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    identifier = get_client_identifier(request, user_id)
    is_allowed, retry_after = rate_limiter.check_rate_limit(identifier)

    if not is_allowed:
        logger.warning(
            f"[RATE-LIMIT] Blocked request from {identifier} - "
            f"retry after {retry_after}s"
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )
