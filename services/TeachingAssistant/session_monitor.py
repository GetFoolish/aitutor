"""
Session Monitor - Real-time monitoring of tutoring sessions
Automatically disconnects sessions when credits are exhausted
"""
import asyncio
from datetime import datetime
from managers.mongodb_manager import mongo_db
from shared.logging_config import get_logger

logger = get_logger(__name__)

# Grace period: allow 30 seconds over limit for graceful shutdown
GRACE_PERIOD_SECONDS = 30

# Global registry for active WebSocket connections (populated from api.py)
active_feed_websockets = {}


async def monitor_session_credits():
    """
    Background task to monitor and auto-end sessions when credits run out.
    Runs continuously while the application is alive.
    """
    logger.info("[SESSION_MONITOR] 🚀 Started session credit monitoring")
    
    while True:
        try:
            # Find all active sessions
            active_sessions = list(mongo_db.sessions.find(
                {"is_active": True},
                {
                    "session_id": 1,
                    "user_id": 1,
                    "started_at": 1,
                    "credits_at_start": 1,
                    "force_ended": 1  # Check if already force-ended
                }
            ))
            
            now = datetime.utcnow()
            
            for session in active_sessions:
                try:
                    # Skip if already force-ended
                    if session.get("force_ended"):
                        continue
                    
                    session_id = session["session_id"]
                    user_id = session["user_id"]
                    started_at = session["started_at"]
                    credits_at_start = session.get("credits_at_start", 0)
                    
                    # Calculate current session duration
                    duration_seconds = (now - started_at).total_seconds()
                    duration_minutes = duration_seconds / 60
                    
                    # Check if duration exceeds available credits (with grace period)
                    credits_limit_seconds = (credits_at_start * 60) + GRACE_PERIOD_SECONDS
                    
                    if duration_seconds >= credits_limit_seconds:
                        logger.warning(
                            f"[SESSION_MONITOR] ⏱️ Session {session_id[:8]}... exceeded credits! "
                            f"Duration: {duration_minutes:.1f} min, Limit: {credits_at_start} min. "
                            f"Sending disconnect signal..."
                        )
                        
                        # Send disconnect signal to frontend via WebSocket
                        await send_disconnect_signal(session_id, user_id, "credits_exceeded")
                    
                except Exception as session_error:
                    logger.error(
                        f"[SESSION_MONITOR] ❌ Error processing session {session.get('session_id', 'unknown')}: "
                        f"{session_error}"
                    )
                    continue
            
        except Exception as e:
            logger.error(f"[SESSION_MONITOR] ❌ Error in monitoring loop: {e}", exc_info=True)
        
        # Check every 30 seconds
        await asyncio.sleep(30)


async def send_disconnect_signal(session_id: str, user_id: str, reason: str):
    """
    Send disconnect signal to frontend via Feed WebSocket.
    The frontend will then disconnect the Gemini tutor and show notification.
    
    Args:
        session_id: Session ID
        user_id: User ID
        reason: Reason for disconnect (for logging and frontend display)
    """
    try:
        # Mark session as force-ended first (prevents repeated signals)
        mongo_db.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "force_ended": True,
                    "force_end_reason": reason,
                    "force_ended_at": datetime.utcnow()
                }
            }
        )
        
        # Get the WebSocket connection for this session from global registry
        websocket = active_feed_websockets.get(session_id)
        
        if websocket:
            # Send disconnect message to frontend
            disconnect_message = {
                "type": "disconnect",
                "reason": reason,
                "message": "Your tutoring session has ended because you've used all available minutes.",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                await websocket.send_json(disconnect_message)
                logger.info(
                    f"[SESSION_MONITOR] ✅ Sent disconnect signal to session {session_id[:8]}... "
                    f"Reason: {reason}"
                )
            except Exception as ws_error:
                logger.error(
                    f"[SESSION_MONITOR] ❌ Failed to send disconnect via WebSocket: {ws_error}"
                )
        else:
            logger.warning(
                f"[SESSION_MONITOR] ⚠️ No active WebSocket for session {session_id[:8]}... "
                f"Session will be ended on next API call"
            )
        
        # Also end the session in the backend (for cleanup)
        # This will deduct minutes when session_end is called
        mongo_db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"is_active": False, "ended_at": datetime.utcnow()}}
        )
        
    except Exception as e:
        logger.error(
            f"[SESSION_MONITOR] ❌ Error sending disconnect signal for session {session_id}: {e}",
            exc_info=True
        )


def register_websocket(session_id: str, websocket):
    """Register a WebSocket connection for a session"""
    active_feed_websockets[session_id] = websocket
    logger.debug(f"[SESSION_MONITOR] Registered WebSocket for session {session_id[:8]}...")


def unregister_websocket(session_id: str):
    """Unregister a WebSocket connection for a session"""
    if session_id in active_feed_websockets:
        del active_feed_websockets[session_id]
        logger.debug(f"[SESSION_MONITOR] Unregistered WebSocket for session {session_id[:8]}...")

