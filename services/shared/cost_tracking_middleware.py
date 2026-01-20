"""
Cost Tracking Middleware - Automatically tracks API calls for cost calculation
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt
from managers.mongodb_manager import mongo_db
from shared.jwt_config import JWT_SECRET, JWT_ALGORITHM
from shared.logging_config import get_logger

logger = get_logger(__name__)


class CostTrackingMiddleware(BaseHTTPMiddleware):
    """
    Track API calls for cost calculation.

    How it works:
    1. Extract user_id from JWT token in Authorization header
    2. Look up active session for that user in MongoDB
    3. Determine which API was called from the request path
    4. Increment API call counter for that session in session_costs collection
    5. Pass request through to actual endpoint handler
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only track specific API endpoints that incur costs
        if not self._should_track(request.url.path):
            return await call_next(request)

        # Extract user_id from JWT token
        user_id = self._extract_user_id(request)
        if not user_id:
            return await call_next(request)

        # Get active session for this user from MongoDB
        session = mongo_db.sessions.find_one({
            "user_id": user_id,
            "is_active": True
        })

        if not session:
            # No active session, just pass through
            return await call_next(request)

        # Determine which API type was called
        api_type = self._determine_api_type(request.url.path)

        # Call the actual endpoint
        response = await call_next(request)

        # After endpoint completes, increment API call count in session_costs
        try:
            mongo_db.session_costs.update_one(
                {"session_id": session["session_id"]},
                {"$inc": {f"api_calls.{api_type}.count": 1}},
                upsert=True  # Create record if doesn't exist
            )
            logger.debug(f"[COST_TRACKING] Tracked {api_type} call for session {session['session_id']}")
        except Exception as e:
            logger.error(f"[COST_TRACKING] Failed to track API call: {e}")

        return response

    def _should_track(self, path: str) -> bool:
        """Check if this endpoint should be tracked for cost"""
        tracked_paths = [
            "/assistant/",           # TeachingAssistant API calls
            "/question/answered",    # Question submission (counts as API call)
        ]
        return any(path.startswith(p) for p in tracked_paths)

    def _extract_user_id(self, request: Request) -> str:
        """Extract user_id from JWT token in Authorization header"""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")  # "sub" is the user_id in our JWT
            return user_id
        except Exception as e:
            logger.debug(f"[COST_TRACKING] Failed to extract user_id from token: {e}")
            return None

    def _determine_api_type(self, path: str) -> str:
        """Determine which API type was called based on path"""
        if "/assistant/" in path:
            return "teaching_assistant"
        elif "/question/answered" in path:
            return "tutor_api"
        else:
            return "dash_api"
