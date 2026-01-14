"""
LiveKit Token Endpoint - Add this to api.py

Add this endpoint after the /session/info endpoint to provide LiveKit connection info
for the frontend to receive Hedra avatar video.
"""

from fastapi import HTTPException, Request
from livekit import api
import os

@app.get("/session/livekit-token")
def get_livekit_token(http_request: Request):
    """Get LiveKit access token for frontend to connect and receive avatar video"""
    try:
        user_id = get_current_user(http_request)
        session = ta.get_active_session(user_id)
        if not session:
            raise HTTPException(status_code=404, detail="No active session")
        
        # Get LiveKit configuration
        livekit_url = os.getenv("LIVEKIT_URL", "")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY", "")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET", "")
        
        if not all([livekit_url, livekit_api_key, livekit_api_secret]):
            raise HTTPException(
                status_code=500,
                detail="LiveKit configuration missing. Check LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET"
            )
        
        # Generate room name based on session_id (must match what agent uses)
        # The agent creates rooms, so we need to use a consistent naming scheme
        # Typically: room name = session_id or user_id
        room_name = session["session_id"]  # or use user_id if agent uses that
        
        # Create access token for frontend to join the room
        token = api.AccessToken(livekit_api_key, livekit_api_secret) \
            .with_identity(f"user-{user_id}") \
            .with_name(f"Student-{user_id}") \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=False,  # Frontend only subscribes to avatar video
                can_subscribe=True,
            )).to_jwt()
        
        logger.info(f"[LiveKit] Generated token for user {user_id}, room {room_name}")
        
        return {
            "token": token,
            "url": livekit_url,
            "room_name": room_name,
        }
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="LiveKit Python SDK not installed. Install with: pip install livekit-api"
        )
    except Exception as e:
        logger.error(f"Error generating LiveKit token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate LiveKit token: {str(e)}")
