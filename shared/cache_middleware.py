"""
Cache Control Middleware for FastAPI
Adds appropriate Cache-Control headers to API responses
Phase 7: Infrastructure & Scale
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add Cache-Control headers based on route patterns
    
    Cache Strategy:
    - Static content (images, CSS, JS): 1 year with immutable
    - Health checks: 60 seconds
    - User-specific data: no-cache (must revalidate)
    - Public API data: short cache (5-10 seconds)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        path = request.url.path
        status = response.status_code

        # Never cache error responses
        if status >= 400:
            response.headers["Cache-Control"] = "no-store"
            return response

        # Static assets - long-term cache
        if any(path.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.jpeg', '.svg', '.woff', '.woff2']):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        # Health check - short cache
        elif path == "/health":
            response.headers["Cache-Control"] = "public, max-age=60"

        # Session info - private, short cache
        elif "/session/info" in path:
            response.headers["Cache-Control"] = "private, max-age=10"

        # Question endpoints - private, no cache (user-specific, authenticated)
        elif "/api/questions" in path and request.method == "GET":
            response.headers["Cache-Control"] = "private, no-store"

        # Assessment endpoints - never cache
        elif "/assessment/" in path:
            response.headers["Cache-Control"] = "no-store"

        # User profile data - private, must revalidate
        elif "/auth/me" in path or "/api/user" in path:
            response.headers["Cache-Control"] = "private, no-cache, must-revalidate"

        # Default: no cache for dynamic content
        else:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        # Add Vary header for proper cache key generation
        if "Cache-Control" in response.headers:
            response.headers["Vary"] = "Accept-Encoding, Authorization"

        return response
