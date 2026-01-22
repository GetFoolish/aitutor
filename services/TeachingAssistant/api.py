import sys
import os
import threading
import requests
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from urllib.parse import parse_qs
from sse_starlette.sse import EventSourceResponse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.TeachingAssistant.teaching_assistant import TeachingAssistant
from services.TeachingAssistant.core.context import Event
from shared.auth_middleware import get_current_user, get_user_from_token
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.cache_middleware import CacheControlMiddleware

from shared.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# Observer WebSocket Registry (for real-time feed monitoring)
# ============================================================================
# Maps session_id -> list of observer WebSocket connections
# Used by backend devs to monitor live sessions and feed data to TeachingAssistant
from typing import Dict, List
active_observers: Dict[str, List[WebSocket]] = {}

# Simple API key for observer authentication (backend devs only)
# In production, use a more robust auth mechanism
OBSERVER_API_KEY = os.getenv("OBSERVER_API_KEY", "dev-observer-key-12345")


# ============================================================================
# Lifespan Context Manager (Start/Stop Event Processing Loop)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop event processing loop AND session monitor"""
    global ta, event_processing_task, session_monitor_task
    
    # Start event processing loop
    ta.running = True
    event_processing_task = asyncio.create_task(ta.ongoing())
    logger.info("[API] ✅ Started event processing loop")
    
    # Start session credit monitoring
    from services.TeachingAssistant.session_monitor import monitor_session_credits
    session_monitor_task = asyncio.create_task(monitor_session_credits())
    logger.info("[API] ✅ Started session credit monitoring")
    
    yield
    
    # Shutdown
    logger.info("[API] 🛑 Shutting down services...")
    ta.running = False
    
    # Stop event processing
    if event_processing_task:
        event_processing_task.cancel()
        try:
            await event_processing_task
        except asyncio.CancelledError:
            pass
    
    # Stop session monitor
    if session_monitor_task:
        session_monitor_task.cancel()
        try:
            await session_monitor_task
        except asyncio.CancelledError:
            pass
    
    logger.info("[API] ✅ All services stopped")


app = FastAPI(title="Teaching Assistant API", lifespan=lifespan)

# Add timing middleware for performance monitoring (Phase 1)
app.add_middleware(UnpluggedTimingMiddleware)

# Cache Control (Phase 7)
app.add_middleware(CacheControlMiddleware)

# Cost Tracking Middleware (Phase 4) - Track API calls for cost calculation
from services.shared.cost_tracking_middleware import CostTrackingMiddleware
app.add_middleware(CostTrackingMiddleware)

# Add GZip compression middleware (Phase 7)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

# Configure CORS with secure origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

# Request timeout middleware (Phase 3)
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    # Increase timeout for token-usage endpoint (MongoDB operations can be slow)
    timeout = 60.0 if request.url.path == "/tutor/token-usage" else 30.0
    try:
        return await asyncio.wait_for(call_next(request), timeout=timeout)
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"detail": "Request timeout"}
        )

# Cache control middleware for static responses (Phase 7)
@app.middleware("http")
async def cache_control_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/health":
        response.headers["Cache-Control"] = "public, max-age=60"
    elif request.url.path.startswith("/session/info"):
        response.headers["Cache-Control"] = "private, max-age=10"
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response

# Explicit OPTIONS handler for Cloud Run compatibility (backup)
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle OPTIONS preflight requests explicitly for Cloud Run"""
    from fastapi.responses import Response
    # Use first allowed origin or * if none configured
    origin = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*"
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(ALLOWED_METHODS),
            "Access-Control-Allow-Headers": "*",
        }
    )

# Create TeachingAssistant instance (now stateless - all state in MongoDB)
ta = TeachingAssistant()

# Global tasks for event processing loop and session monitoring
event_processing_task = None
session_monitor_task = None

# DASH API URL for pre-loading questions
DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")


# ============================================================================
# Transcript Buffer for Debouncing Partial Transcripts
# ============================================================================

class TranscriptBuffer:
    """Buffer transcripts to aggregate fragments before processing"""
    def __init__(self, debounce_ms: int = 2000):
        self.buffers: Dict[str, Dict[str, str]] = {}  # session_id -> {speaker -> text}
        self.timers: Dict[str, asyncio.TimerHandle] = {}  # session_id:speaker -> timer
        self.debounce_ms = debounce_ms

    async def add(self, session_id: str, speaker: str, text: str, callback) -> bool:
        """
        Add text to buffer. Returns True if text was buffered (will be flushed later),
        False if it was sent immediately (empty buffer or no debounce needed).
        """
        key = f"{session_id}:{speaker}"

        # Initialize buffer for this session:speaker pair if needed
        if session_id not in self.buffers:
            self.buffers[session_id] = {}

        # Add text to buffer
        self.buffers[session_id][speaker] = self.buffers[session_id].get(speaker, "") + text
        buffered_text = self.buffers[session_id][speaker]

        # Cancel existing timer if any
        if key in self.timers:
            self.timers[key].cancel()
            del self.timers[key]

        # Set new timer to flush after debounce
        loop = asyncio.get_event_loop()
        self.timers[key] = loop.call_later(
            self.debounce_ms / 1000.0,
            lambda: asyncio.create_task(self._flush(session_id, speaker, callback))
        )

        return True

    async def _flush(self, session_id: str, speaker: str, callback):
        """Flush buffered text"""
        if session_id not in self.buffers or speaker not in self.buffers[session_id]:
            return

        text = self.buffers[session_id][speaker].strip()
        if text:
            await callback(text)

        # Clean up
        del self.buffers[session_id][speaker]
        key = f"{session_id}:{speaker}"
        if key in self.timers:
            del self.timers[key]

    async def flush_all(self, session_id: str, callback):
        """Flush all pending text for a session"""
        if session_id not in self.buffers:
            return

        for speaker, text in list(self.buffers[session_id].items()):
            text = text.strip()
            if text:
                await callback(text, speaker)

            # Clean up timers
            key = f"{session_id}:{speaker}"
            if key in self.timers:
                self.timers[key].cancel()
                del self.timers[key]

        del self.buffers[session_id]

    def cleanup_session(self, session_id: str):
        """Clean up buffers and timers for a session"""
        if session_id in self.buffers:
            for speaker in self.buffers[session_id].keys():
                key = f"{session_id}:{speaker}"
                if key in self.timers:
                    self.timers[key].cancel()
                    del self.timers[key]
            del self.buffers[session_id]

transcript_buffer = TranscriptBuffer(debounce_ms=2000)


# ============================================================================
# Feed-to-Event Converter
# ============================================================================

def feed_message_to_event(message: dict, session_id: str, user_id: str) -> Optional[Event]:
    """Convert WebSocket feed message to Event object"""
    msg_type = message.get("type")
    timestamp_str = message.get("timestamp")
    payload = message.get("data", {})
    
    # Parse timestamp
    if timestamp_str:
        try:
            from datetime import datetime
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).timestamp()
        except:
            timestamp = time.time()
    else:
        timestamp = time.time()
    
    # Convert based on message type
    if msg_type == "transcript":
        return Event(
            type="text",
            timestamp=timestamp,
            session_id=session_id,
            user_id=user_id,
            data={
                "speaker": payload.get("speaker", "user"),
                "text": payload.get("transcript", ""),
                "timestamp": timestamp_str
            }
        )
    elif msg_type == "audio":
        return Event(
            type="audio",
            timestamp=timestamp,
            session_id=session_id,
            user_id=user_id,
            data={
                "audio": payload.get("audio", ""),
                "timestamp": timestamp_str
            }
        )
    elif msg_type == "media":
        return Event(
            type="media",
            timestamp=timestamp,
            session_id=session_id,
            user_id=user_id,
            data={
                "media": payload.get("media", ""),
                "timestamp": timestamp_str
            }
        )
    return None


# ============================================================================
# Request/Response Models
# ============================================================================

class StartSessionRequest(BaseModel):
    assessment_mode: Optional[bool] = False  # Flag for assessment mode (no TA features)


class EndSessionRequest(BaseModel):
    interrupt_audio: bool = True
    assessment_mode: Optional[bool] = False  # Flag for assessment mode (no TA features)


class QuestionAnsweredRequest(BaseModel):
    question_id: str
    is_correct: bool


class TokenUsageRequest(BaseModel):
    promptTokenCount: int = 0
    candidatesTokenCount: int = 0
    totalTokenCount: int = 0
    cachedContentTokenCount: int = 0  # Cached tokens (90% discount)
    thoughtTokenCount: int = 0  # Thinking tokens (billed as output)
    promptTokensDetails: Optional[List[Dict[str, Any]]] = []  # Modality breakdown: [{modality: "TEXT/AUDIO/VIDEO", tokenCount: number}]


class PromptResponse(BaseModel):
    prompt: str
    session_info: dict


class FeedWebhookRequest(BaseModel):
    type: str  # "media" | "audio" | "transcript" | "combined"
    timestamp: str  # ISO 8601 timestamp
    data: dict  # Contains optional: media, audio, transcript


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "TeachingAssistant"}


# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.post("/session/start", response_model=PromptResponse)
async def start_session(http_request: Request, request: Optional[StartSessionRequest] = None):
    """Start a new tutoring session (supports both normal and assessment modes)"""
    user_id = get_current_user(http_request)
    assessment_mode = request.assessment_mode if request else False

    try:
        # STEP 1: Allocate daily free minutes if needed
        from services.PaymentService.free_minutes_handler import (
            allocate_daily_free_minutes,
            check_user_balance
        )

        # Allocate daily minutes (will only allocate if not already allocated today)
        allocate_daily_free_minutes(user_id)

        # STEP 2: Check if user has enough minutes (at least 1 minute to start)
        balances = check_user_balance(user_id)
        total_balance = balances["total"]
        mode_str = "ASSESSMENT" if assessment_mode else "NORMAL"
        logger.info(f"[SESSION_START] [{mode_str}] User {user_id[:8]}... has {total_balance} minutes available (free: {balances['free']}, paid: {balances['paid']})")

        if total_balance < 1:
            logger.warning(f"[SESSION_START] ❌ User {user_id[:8]}... has insufficient minutes: {total_balance}")
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "insufficient_minutes",
                    "message": "You've used your free 15 minutes today. Come back tomorrow or purchase a plan to continue tutoring.",
                    "balance": total_balance,
                    "required": 1
                }
            )

        # Create session in MongoDB (existing method)
        result = ta.start_session(user_id)
        session_id = result["session_info"]["session_id"]

        # STEP 3: Store credits_at_start and assessment_mode flag for session monitoring
        from managers.mongodb_manager import mongo_db
        mongo_db.sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "credits_at_start": total_balance,
                    "max_duration_minutes": total_balance,
                    "assessment_mode": assessment_mode
                }
            }
        )
        logger.info(
            f"[SESSION_START] ✅ Session {session_id[:8]}... created with "
            f"{total_balance} minutes available (mode: {mode_str})"
        )

        # CONDITIONAL: Initialize memory and context components only in normal mode
        greeting = ""
        if not assessment_mode:
            # Initialize memory and context components (new method)
            greeting = await ta.start(user_id, session_id)

            # Create session_start event
            start_event = Event(
                type="session_start",
                timestamp=time.time(),
                session_id=session_id,
                user_id=user_id,
                data={"session_id": session_id, "user_id": user_id}
            )
            ta.queue_manager.enqueue(start_event)
        else:
            logger.info(f"[SESSION_START] Skipping TA initialization for assessment mode")

        # UPDATED: Return greeting in response for immediate delivery
        # Also sent via SSE for systems that listen to instruction queue
        # This ensures backward compatibility with frontends expecting prompt in response
        session_id = result["session_id"]

        # Initialize cost tracking for this session (works for both modes)
        from services.CostTracking.cost_tracker import CostTracker
        cost_tracker = CostTracker(session_id, user_id)
        cost_tracker.start_session()

        return PromptResponse(
            prompt=greeting or "",  # Return greeting (empty in assessment mode)
            session_info=result["session_info"]
        )
    except Exception as e:
        logger.error(f"Error in start_session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _preload_questions_background(user_id: str, token: str):
    """Background function to pre-load questions for next session"""
    try:
        # Call DASH API to get 5 questions for next session
        dash_response = requests.get(
            f"{DASH_API_URL}/api/questions/5",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if dash_response.status_code == 200:
            preloaded_questions = dash_response.json()
            # Extract question IDs
            question_ids = [
                q.get('dash_metadata', {}).get('dash_question_id', '')
                for q in preloaded_questions
                if q.get('dash_metadata', {}).get('dash_question_id')
            ]

            if question_ids:
                # Store in MongoDB user profile
                from managers.mongodb_manager import mongo_db
                mongo_db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"preloaded_question_ids": question_ids}}
                )
                logger.info(f"[PRELOAD] Stored {len(question_ids)} question IDs for next session (user: {user_id})")
    except Exception as e:
        # Don't fail session end if pre-loading fails
        logger.error(f"[PRELOAD] Failed to pre-load questions: {e}")


@app.post("/session/end", response_model=PromptResponse)
async def end_session(http_request: Request, request: Optional[EndSessionRequest] = None):
    """End the current tutoring session (supports both normal and assessment modes)"""
    user_id = get_current_user(http_request)
    assessment_mode = request.assessment_mode if request else False

    try:
        # Get active session for user
        session = ta.get_active_session(user_id)
        if not session:
            return PromptResponse(
                prompt="",
                session_info={'session_active': False, 'user_id': user_id}
            )

        session_id = session["session_id"]

        # Check if this session was created in assessment mode (fallback to request param)
        session_assessment_mode = session.get("assessment_mode", assessment_mode)
        mode_str = "ASSESSMENT" if session_assessment_mode else "NORMAL"

        # CONDITIONAL: End session with memory consolidation only in normal mode
        closing = ""
        if not session_assessment_mode:
            # End session with memory consolidation (new method)
            closing = await ta.end(user_id, session_id)
        else:
            logger.info(f"[SESSION_END] Skipping TA cleanup for assessment mode")

        # Session end event is NO LONGER needed here because we called ta.end() directly above
        # Queuing it would cause the event loop to call ta.end() a second time!
        # end_event = Event(
        #     type="session_end",
        #     timestamp=time.time(),
        #     session_id=session_id,
        #     user_id=user_id,
        #     data={"session_id": session_id, "user_id": user_id}
        # )
        # ta.queue_manager.enqueue(end_event)

        # Get session summary (existing method for stats - works for both modes)
        result = ta.end_session(session_id)

        # Finalize cost tracking for this session (works for both modes)
        try:
            from services.CostTracking.cost_tracker import CostTracker
            cost_tracker = CostTracker(session_id, user_id)
            cost_tracker.end_session()
        except Exception as cost_error:
            logger.error(f"[COST_TRACKING] Failed to finalize costs: {cost_error}", exc_info=True)

        # CONDITIONAL: Pre-load next session questions only in normal mode
        if not session_assessment_mode:
            try:
                auth_header = http_request.headers.get("Authorization", "")
                if not auth_header:
                    auth_header = http_request.headers.get("authorization", "")

                token = ""
                if auth_header.startswith("Bearer "):
                    token = auth_header.replace("Bearer ", "", 1)
                elif auth_header.startswith("bearer "):
                    token = auth_header.replace("bearer ", "", 1)

                if token and len(token) > 0:
                    preload_thread = threading.Thread(
                        target=_preload_questions_background,
                        args=(user_id, token),
                        daemon=True
                    )
                    preload_thread.start()
            except Exception as e:
                logger.error(f"[PRELOAD] Failed to start pre-loading thread: {e}")

        logger.info(f"[SESSION_END] ✅ [{mode_str}] Session {session_id[:8]}... ended successfully")

        # Return closing message directly (also sent via SSE) - empty in assessment mode
        return PromptResponse(
            prompt=closing or result["prompt"],  # Use memory-aware closing or fallback (empty in assessment)
            session_info=result["session_info"]
        )
    except Exception as e:
        logger.error(f"Error in end_session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question/answered")
def record_question(http_request: Request, request: QuestionAnsweredRequest):
    """Record a question answer"""
    user_id = get_current_user(http_request)
    try:
        session = ta.get_active_session(user_id)
        if not session:
            raise HTTPException(status_code=404, detail="No active session")

        ta.record_question_answered(
            session["session_id"],
            request.question_id,
            request.is_correct
        )
        return {"status": "recorded", "session_info": ta.get_session_info(session["session_id"])}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in record_question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tutor/token-usage")
async def record_tutor_token_usage(http_request: Request, request: TokenUsageRequest):
    """
    Record token usage from tutor service (Gemini Live API)
    
    IMPORTANT: In Live API, promptTokenCount is CUMULATIVE (total so far, not incremental).
    We need to calculate deltas by comparing with last recorded values.
    """
    try:
        user_id = get_current_user(http_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user from token: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        # Get active session for this user
        session = ta.get_active_session(user_id)
        if not session:
            logger.debug(f"[TOKEN_USAGE] No active session for user {user_id}")
            return {"status": "no_session"}
        
        session_id = session["session_id"]
        
        # Get current session cost data to calculate deltas
        from managers.mongodb_manager import mongo_db
        from datetime import datetime, timezone
        
        # Use async MongoDB operation to avoid blocking event loop
        current_session = await asyncio.to_thread(
            mongo_db.session_costs.find_one,
            {"session_id": session_id},
            {"api_calls.tutor_api": 1}  # Only fetch needed fields for performance
        )
        
        # Get last cumulative values (if they exist)
        last_prompt_tokens = 0
        last_candidates_tokens = 0
        last_total_tokens = 0
        last_cached_tokens = 0
        last_thought_tokens = 0
        
        if current_session:
            tutor_data = current_session.get("api_calls", {}).get("tutor_api", {})
            last_prompt_tokens = tutor_data.get("last_cumulative_prompt_tokens", 0)
            last_candidates_tokens = tutor_data.get("last_cumulative_candidates_tokens", 0)
            last_total_tokens = tutor_data.get("last_cumulative_total_tokens", 0)
            last_cached_tokens = tutor_data.get("last_cumulative_cached_tokens", 0)
            last_thought_tokens = tutor_data.get("last_cumulative_thought_tokens", 0)
        
        # Calculate deltas (new tokens since last update)
        # Note: In Live API, these are cumulative, so we subtract last values
        delta_prompt_tokens = max(0, request.promptTokenCount - last_prompt_tokens)
        delta_candidates_tokens = max(0, request.candidatesTokenCount - last_candidates_tokens)
        delta_total_tokens = max(0, request.totalTokenCount - last_total_tokens)
        delta_cached_tokens = max(0, request.cachedContentTokenCount - last_cached_tokens)
        delta_thought_tokens = max(0, request.thoughtTokenCount - last_thought_tokens)
        
        # Calculate fresh (non-cached) prompt tokens
        # Fresh tokens = total prompt tokens - cached tokens
        fresh_prompt_tokens = max(0, request.promptTokenCount - request.cachedContentTokenCount)
        last_fresh_prompt_tokens = max(0, last_prompt_tokens - last_cached_tokens)
        delta_fresh_prompt_tokens = max(0, fresh_prompt_tokens - last_fresh_prompt_tokens)
        
        # Parse modality breakdown for accurate pricing
        # Note: promptTokensDetails may be cumulative or per-turn
        # We'll track it and calculate deltas if needed
        current_text_tokens = 0
        current_audio_tokens = 0
        current_video_tokens = 0
        
        if request.promptTokensDetails:
            for detail in request.promptTokensDetails:
                modality = detail.get("modality", "").upper()
                token_count = detail.get("tokenCount", 0) or 0
                if modality == "TEXT":
                    current_text_tokens += token_count
                elif modality == "AUDIO":
                    current_audio_tokens += token_count
                elif modality == "VIDEO":
                    current_video_tokens += token_count
        
        # Get last modality values (if they exist) to calculate deltas
        last_text_tokens = 0
        last_audio_tokens = 0
        last_video_tokens = 0
        
        if current_session:
            tutor_data = current_session.get("api_calls", {}).get("tutor_api", {})
            last_text_tokens = tutor_data.get("last_cumulative_text_tokens", 0)
            last_audio_tokens = tutor_data.get("last_cumulative_audio_tokens", 0)
            last_video_tokens = tutor_data.get("last_cumulative_video_tokens", 0)
        
        # Calculate modality deltas (assuming cumulative, but will work if per-turn too)
        # If per-turn, deltas will equal current values; if cumulative, deltas will be the difference
        delta_text_tokens = max(0, current_text_tokens - last_text_tokens)
        delta_audio_tokens = max(0, current_audio_tokens - last_audio_tokens)
        delta_video_tokens = max(0, current_video_tokens - last_video_tokens)
        
        # Use deltas for incrementing (works for both cumulative and per-turn)
        text_tokens = delta_text_tokens
        audio_tokens = delta_audio_tokens
        video_tokens = delta_video_tokens
        
        # Store detailed token usage record
        token_usage_record = {
            "timestamp": datetime.now(timezone.utc),
            # Cumulative values (as received from API)
            "cumulative_prompt_tokens": request.promptTokenCount,
            "cumulative_candidates_tokens": request.candidatesTokenCount,
            "cumulative_total_tokens": request.totalTokenCount,
            "cumulative_cached_tokens": request.cachedContentTokenCount,
            "cumulative_thought_tokens": request.thoughtTokenCount,
            # Delta values (new tokens since last update)
            "delta_prompt_tokens": delta_prompt_tokens,
            "delta_candidates_tokens": delta_candidates_tokens,
            "delta_total_tokens": delta_total_tokens,
            "delta_cached_tokens": delta_cached_tokens,
            "delta_thought_tokens": delta_thought_tokens,
            "delta_fresh_prompt_tokens": delta_fresh_prompt_tokens,
            # Modality breakdown (delta values)
            "text_tokens": text_tokens,  # Delta
            "audio_tokens": audio_tokens,  # Delta
            "video_tokens": video_tokens,  # Delta
            "prompt_tokens_details": request.promptTokensDetails,  # Full details from API
            # Cumulative modality values (for reference)
            "cumulative_text_tokens": current_text_tokens,
            "cumulative_audio_tokens": current_audio_tokens,
            "cumulative_video_tokens": current_video_tokens
        }
        
        # Update session_costs with deltas (incremental) and latest cumulative values
        update_operation = {
            "$push": {
                "tutor_token_usage": token_usage_record
            },
            "$inc": {
                "api_calls.tutor_api.count": 1,
                # Increment by deltas (new tokens)
                "api_calls.tutor_api.prompt_tokens": delta_fresh_prompt_tokens,  # Only fresh tokens
                "api_calls.tutor_api.cached_content_tokens": delta_cached_tokens,  # Cached tokens separately
                "api_calls.tutor_api.output_tokens": delta_candidates_tokens,  # Output tokens
                "api_calls.tutor_api.thinking_tokens": delta_thought_tokens,  # Thinking tokens
                "api_calls.tutor_api.total_tokens": delta_total_tokens,
                # Modality-based tracking
                "api_calls.tutor_api.text_input_tokens": text_tokens,
                "api_calls.tutor_api.audio_input_tokens": audio_tokens,
                "api_calls.tutor_api.video_input_tokens": video_tokens
            },
            "$set": {
                # Store latest cumulative values for next delta calculation
                "api_calls.tutor_api.last_cumulative_prompt_tokens": request.promptTokenCount,
                "api_calls.tutor_api.last_cumulative_candidates_tokens": request.candidatesTokenCount,
                "api_calls.tutor_api.last_cumulative_total_tokens": request.totalTokenCount,
                "api_calls.tutor_api.last_cumulative_cached_tokens": request.cachedContentTokenCount,
                "api_calls.tutor_api.last_cumulative_thought_tokens": request.thoughtTokenCount,
                # Store latest modality values for delta calculation
                "api_calls.tutor_api.last_cumulative_text_tokens": current_text_tokens,
                "api_calls.tutor_api.last_cumulative_audio_tokens": current_audio_tokens,
                "api_calls.tutor_api.last_cumulative_video_tokens": current_video_tokens
            }
        }
        
        # Use async MongoDB operation to avoid blocking event loop
        await asyncio.to_thread(
            mongo_db.session_costs.update_one,
            {"session_id": session_id},
            update_operation,
            upsert=True
        )
        
        # Log token usage details
        logger.info(
            f"[TOKEN_USAGE] Session {session_id[:8]}... | "
            f"Cumulative: prompt={request.promptTokenCount}, candidates={request.candidatesTokenCount}, "
            f"total={request.totalTokenCount}, cached={request.cachedContentTokenCount}, "
            f"thought={request.thoughtTokenCount} | "
            f"Deltas: prompt={delta_fresh_prompt_tokens}, cached={delta_cached_tokens}, "
            f"output={delta_candidates_tokens}, thought={delta_thought_tokens} | "
            f"Modality: text={text_tokens}, audio={audio_tokens}, video={video_tokens}"
        )
        
        return {"status": "recorded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording token usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record token usage: {str(e)}")


@app.get("/session/info")
def get_session_info(http_request: Request):
    """Get current session info"""
    user_id = get_current_user(http_request)
    session = ta.get_active_session(user_id)
    if not session:
        return {"session_active": False, "user_id": user_id}
    return ta.get_session_info(session["session_id"])


@app.post("/conversation/turn")
def record_conversation_turn(http_request: Request):
    """Record a conversation turn"""
    user_id = get_current_user(http_request)
    try:
        session = ta.get_active_session(user_id)
        if not session:
            # If session is already closed (race condition with session end), just ignore
            return {"status": "ignored", "reason": "no_active_session"}

        ta.record_conversation_turn(session["session_id"])
        return {"status": "recorded"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in record_conversation_turn: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/inactivity/check", response_model=PromptResponse)
def check_inactivity(http_request: Request):
    """Check for inactivity and return prompt if needed"""
    user_id = get_current_user(http_request)
    try:
        session = ta.get_active_session(user_id)
        if not session:
            return PromptResponse(prompt="", session_info={"session_active": False})

        prompt = ta.check_inactivity(session["session_id"])
        session_info = ta.get_session_info(session["session_id"])
        return PromptResponse(prompt=prompt or "", session_info=session_info)
    except Exception as e:
        logger.error(f"Error in check_inactivity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket Endpoint (Frontend → Backend feed streaming)
# ============================================================================

@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    """WebSocket endpoint for streaming audio/video/transcript from frontend"""
    # 1. Extract and validate JWT from query parameter
    query_params = parse_qs(websocket.scope["query_string"].decode())
    token = query_params.get("token", [None])[0]

    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    user_info = get_user_from_token(token)
    if not user_info:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = user_info["user_id"]

    # 2. Get active session and check if it's still active
    session = ta.get_active_session(user_id)
    if not session or not session.get("is_active"):
        await websocket.close(code=1008, reason="Session not active or ended")
        logger.info(f"[WS] Rejected connection - no active session for user {user_id}")
        return

    session_id = session["session_id"]

    # 3. Accept connection and update status
    await websocket.accept()
    ta.session_manager.set_connection_status(session_id, websocket=True)
    logger.info(f"[WS] WebSocket connected for session {session_id}")
    
    # 4. Register WebSocket for session monitoring
    from services.TeachingAssistant.session_monitor import register_websocket, unregister_websocket
    register_websocket(session_id, websocket)

    try:
        # 5. Message handling loop
        while True:
            # Check if session was force-ended
            session = ta.session_manager.get_session_by_id(session_id)
            if not session or not session.get("is_active"):
                # Session ended - close connection
                close_reason = "Session ended"
                if session and session.get("force_ended"):
                    close_reason = f"Session ended: {session.get('force_end_reason', 'credits exceeded')}"
                await websocket.close(code=1000, reason=close_reason)
                logger.info(f"[WS] Closing - {close_reason}")
                break
            
            data = await websocket.receive_json()

            # Update activity timestamp
            ta.session_manager.update_activity(session_id)

            # Process message based on type
            msg_type = data.get("type")
            timestamp = data.get("timestamp")
            payload = data.get("data", {})

            if msg_type == "audio":
                await process_audio(session_id, payload.get("audio"), timestamp)
            elif msg_type == "media":
                await process_media(session_id, payload.get("media"), timestamp)
            elif msg_type == "transcript":
                speaker = payload.get("speaker", "tutor")
                await process_transcript(session_id, payload.get("transcript"), timestamp, speaker)
                # Record conversation turn for transcripts
                ta.record_conversation_turn(session_id)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"[WS] WebSocket disconnected for session {session_id}")
        transcript_buffer.cleanup_session(session_id)
        ta.session_manager.set_connection_status(session_id, websocket=False)
    except Exception as e:
        logger.error(f"[WS] WebSocket error for session {session_id}: {e}")
        transcript_buffer.cleanup_session(session_id)
        ta.session_manager.set_connection_status(session_id, websocket=False)
    finally:
        # 6. Unregister WebSocket
        unregister_websocket(session_id)


async def broadcast_to_observers(session_id: str, message: dict):
    """Broadcast a message to all observers watching this session"""
    if session_id not in active_observers:
        return

    observers = active_observers[session_id]
    if not observers:
        return

    # Send to all observers concurrently, remove disconnected ones
    disconnected = []
    for ws in observers:
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.debug(f"[OBSERVER] Failed to send to observer: {e}")
            disconnected.append(ws)

    # Clean up disconnected observers
    for ws in disconnected:
        if ws in active_observers[session_id]:
            active_observers[session_id].remove(ws)


async def process_audio(session_id: str, audio_base64: str, timestamp: str):
    """Process incoming audio data and broadcast to observers"""
    # Get user_id from session
    session = ta.session_manager.get_session_by_id(session_id)
    if not session:
        return
    
    user_id = session["user_id"]
    
    # Create event from feed message
    event = feed_message_to_event(
        {
            "type": "audio",
            "timestamp": timestamp,
            "data": {"audio": audio_base64}
        },
        session_id,
        user_id
    )
    
    if event:
        # Enqueue event for processing
        ta.queue_manager.enqueue(event)
    
    # Broadcast to observers (keep existing functionality)
    logger.debug(f"[AUDIO] Session {session_id}: received audio at {timestamp}")

    await broadcast_to_observers(session_id, {
        "type": "audio",
        "timestamp": timestamp,
        "data": {"audio": audio_base64}
    })


async def process_media(session_id: str, media_base64: str, timestamp: str):
    """Process incoming media (video frames) and broadcast to observers"""
    # Get user_id from session
    session = ta.session_manager.get_session_by_id(session_id)
    if not session:
        return
    
    user_id = session["user_id"]
    
    # Create event from feed message
    event = feed_message_to_event(
        {
            "type": "media",
            "timestamp": timestamp,
            "data": {"media": media_base64}
        },
        session_id,
        user_id
    )
    
    if event:
        # Enqueue event for processing
        ta.queue_manager.enqueue(event)
    
    # Broadcast to observers (keep existing functionality)
    logger.debug(f"[MEDIA] Session {session_id}: received frame at {timestamp}")

    await broadcast_to_observers(session_id, {
        "type": "media",
        "timestamp": timestamp,
        "data": {"media": media_base64}
    })


async def process_transcript(session_id: str, transcript: str, timestamp: str, speaker: str = "tutor"):
    """Process incoming transcript and broadcast to observers"""
    # Get user_id from session
    session = ta.session_manager.get_session_by_id(session_id)
    if not session:
        return

    user_id = session["user_id"]

    # Define callback for when buffered transcript is ready
    async def on_transcript_ready(buffered_text: str):
        # Create event from feed message with buffered text
        event = feed_message_to_event(
            {
                "type": "transcript",
                "timestamp": timestamp,
                "data": {
                    "transcript": buffered_text,
                    "speaker": speaker
                }
            },
            session_id,
            user_id
        )

        if event:
            # Enqueue event for processing
            ta.queue_manager.enqueue(event)

        # Log aggregated transcript
        speaker_label = "USER" if speaker == "user" else "TUTOR"
        logger.debug(f"[TRANSCRIPT] Session {session_id} [{speaker_label}]: {buffered_text[:100] if buffered_text else 'empty'}...")

        # Broadcast to observers
        await broadcast_to_observers(session_id, {
            "type": "transcript",
            "timestamp": timestamp,
            "data": {"transcript": buffered_text, "speaker": speaker}
        })

    # Add to buffer (will be flushed after debounce)
    await transcript_buffer.add(session_id, speaker, transcript, on_transcript_ready)


# ============================================================================
# SSE Endpoint (Backend → Frontend instruction delivery)
# ============================================================================

@app.get("/sse/instructions")
async def sse_instructions(request: Request, token: str = None):
    """SSE endpoint for pushing instructions to frontend"""
    # Validate token (passed as query param for SSE)
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    user_info = get_user_from_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = user_info["user_id"]

    # Get active session
    session = ta.get_active_session(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    session_id = session["session_id"]
    ta.session_manager.set_connection_status(session_id, sse=True)
    logger.info(f"[SSE] SSE connected for session {session_id}")

    async def event_generator():
        try:
            keepalive_counter = 0
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Check for pending instructions in MongoDB
                instructions = ta.session_manager.get_pending_instructions(session_id)

                for instruction in instructions:
                    yield {
                        "event": "instruction",
                        "id": instruction["instruction_id"],
                        "data": instruction["text"]
                    }
                    # Mark as delivered
                    ta.session_manager.mark_instruction_delivered(
                        session_id,
                        instruction["instruction_id"]
                    )

                # Check for inactivity and generate prompt if needed
                # This replaces the background thread approach
                ta.check_inactivity(session_id)

                # Send keepalive every 30 seconds (6 * 5 second intervals)
                keepalive_counter += 1
                if keepalive_counter >= 6:
                    yield {"event": "keepalive", "data": ""}
                    keepalive_counter = 0

                # Poll interval
                await asyncio.sleep(5)

        finally:
            ta.session_manager.set_connection_status(session_id, sse=False)
            logger.info(f"[SSE] SSE disconnected for session {session_id}")

    # Fix CORS headers for SSE - ensure proper origin handling
    origin = request.headers.get("origin")
    # Validate origin against allowed origins
    if origin and origin in ALLOWED_ORIGINS:
        allowed_origin = origin
    else:
        # Fallback: use first allowed origin or "*" for development
        allowed_origin = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*"
    
    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Headers": "Cache-Control",
        "Access-Control-Expose-Headers": "*"
    }
    
    return EventSourceResponse(event_generator(), headers=headers)


# ============================================================================
# Instruction Push Endpoint (Backend → Frontend via SSE)
# ============================================================================

class InstructionRequest(BaseModel):
    instruction: str
    session_id: Optional[str] = None  # Optional - if not provided, uses user's active session


@app.post("/session/instruction")
def push_instruction(request: InstructionRequest, http_request: Request):
    """
    Push an instruction to the tutor via SSE.

    The instruction will be delivered to the frontend via SSE and sent to Gemini.
    Can be called by:
    - Authenticated user (uses their active session)
    - Backend system with session_id specified
    """
    user_id = get_current_user(http_request)

    try:
        # Get session - either from request or user's active session
        if request.session_id:
            session = ta.session_manager.get_session_by_id(request.session_id)
        else:
            session = ta.get_active_session(user_id)

        if not session:
            raise HTTPException(status_code=404, detail="No active session found")

        session_id = session["session_id"]

        # Add system prompt prefix so tutor knows it's an instruction
        SYSTEM_PROMPT_PREFIX = "[SYSTEM INSTRUCTION]"
        full_instruction = f"{SYSTEM_PROMPT_PREFIX}\n{request.instruction}"

        # Push to session's instruction queue
        instruction_id = ta.session_manager.push_instruction(session_id, full_instruction)

        # Log the instruction content
        truncated_instruction = request.instruction[:150] + "..." if len(request.instruction) > 150 else request.instruction
        logger.info(f"[INSTRUCTION CREATED] {instruction_id}: {truncated_instruction}")

        return {
            "success": True,
            "instruction_id": instruction_id,
            "session_id": session_id,
            "message": "Instruction queued for delivery via SSE"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pushing instruction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/instruction/admin")
def push_instruction_admin(request: InstructionRequest, api_key: str = None):
    """
    Admin endpoint to push instruction to any session.
    Requires observer API key authentication.
    session_id is required for this endpoint.
    """
    if api_key != OBSERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required for admin endpoint")

    try:
        session = ta.session_manager.get_session_by_id(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")

        # Add system prompt prefix
        SYSTEM_PROMPT_PREFIX = "[SYSTEM INSTRUCTION]"
        full_instruction = f"{SYSTEM_PROMPT_PREFIX}\n{request.instruction}"

        # Push instruction
        instruction_id = ta.session_manager.push_instruction(request.session_id, full_instruction)

        # Log the instruction content
        truncated_instruction = request.instruction[:150] + "..." if len(request.instruction) > 150 else request.instruction
        logger.info(f"[INSTRUCTION CREATED/ADMIN] {instruction_id}: {truncated_instruction}")

        return {
            "success": True,
            "instruction_id": instruction_id,
            "session_id": request.session_id,
            "message": "Instruction queued for delivery via SSE"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pushing admin instruction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Observer WebSocket Endpoint (Backend devs monitoring live sessions)
# ============================================================================

@app.get("/sessions/active")
def list_active_sessions(api_key: str = None):
    """
    List all active sessions (for backend devs to choose which to observe)
    Requires API key authentication
    """
    if api_key != OBSERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    sessions = ta.session_manager.list_active_sessions()
    return {
        "sessions": [
            {
                "session_id": s["session_id"],
                "user_id": s["user_id"],
                "started_at": s["started_at"].isoformat() if s.get("started_at") else None,
                "websocket_connected": s.get("websocket_connected", False),
                "sse_connected": s.get("sse_connected", False),
                "questions_answered": s.get("questions_answered_this_session", 0)
            }
            for s in sessions
        ]
    }


@app.websocket("/ws/feed/observe")
async def websocket_observe(websocket: WebSocket):
    """
    Observer WebSocket endpoint for backend devs to monitor live sessions.

    Query params:
        - api_key: Observer API key for authentication
        - session_id: The session to observe (required)

    Receives: audio, media, transcript messages as they flow through the producer
    """
    # 1. Extract query parameters
    query_params = parse_qs(websocket.scope["query_string"].decode())
    api_key = query_params.get("api_key", [None])[0]
    session_id = query_params.get("session_id", [None])[0]

    # 2. Validate API key
    if api_key != OBSERVER_API_KEY:
        await websocket.close(code=4001, reason="Invalid API key")
        return

    # 3. Validate session_id
    if not session_id:
        await websocket.close(code=4002, reason="Missing session_id")
        return

    # 4. Verify session exists
    session = ta.session_manager.get_session_by_id(session_id)
    if not session:
        await websocket.close(code=4003, reason="Session not found")
        return

    # 5. Accept connection and register as observer
    await websocket.accept()

    if session_id not in active_observers:
        active_observers[session_id] = []
    active_observers[session_id].append(websocket)

    observer_count = len(active_observers[session_id])
    logger.info(f"[OBSERVER] Observer connected for session {session_id} (total: {observer_count})")

    # Send initial session info
    await websocket.send_json({
        "type": "session_info",
        "data": {
            "session_id": session_id,
            "user_id": session.get("user_id"),
            "started_at": session.get("started_at").isoformat() if session.get("started_at") else None,
            "websocket_connected": session.get("websocket_connected", False),
            "message": "Observer connected. Waiting for feed data..."
        }
    })

    try:
        # 6. Keep connection alive and handle any observer commands
        while True:
            try:
                # Wait for messages (ping/pong or commands)
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)

                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "keepalive"})
                except:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[OBSERVER] Error: {e}")
    finally:
        # Clean up
        if session_id in active_observers and websocket in active_observers[session_id]:
            active_observers[session_id].remove(websocket)
            remaining = len(active_observers[session_id])
            logger.info(f"[OBSERVER] Observer disconnected from session {session_id} (remaining: {remaining})")


# ============================================================================
# Legacy Endpoints (kept for backward compatibility during migration)
# These can be removed after frontend is fully migrated to WebSocket/SSE
# ============================================================================

@app.post("/webhook/feed")
def receive_feed(http_request: Request, request: FeedWebhookRequest):
    """
    LEGACY: POST-based feed webhook
    Will be replaced by WebSocket /ws/feed
    """
    user_id = get_current_user(http_request)
    try:
        logger.debug(f"[FEED] Received {request.type} from user {user_id} at {request.timestamp}")
        return {"status": "received", "type": request.type}
    except Exception as e:
        logger.error(f"Error in receive_feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/send_instruction_to_tutor", response_model=PromptResponse)
def send_instruction_to_tutor(http_request: Request):
    """
    LEGACY: POST-based instruction polling
    Will be replaced by SSE /sse/instructions
    """
    user_id = get_current_user(http_request)
    try:
        session = ta.get_active_session(user_id)
        if not session:
            return PromptResponse(prompt="", session_info={"session_active": False})

        session_id = session["session_id"]

        # Check for pending instructions
        instructions = ta.session_manager.get_pending_instructions(session_id)
        if instructions:
            instruction = instructions[0]
            ta.session_manager.mark_instruction_delivered(session_id, instruction["instruction_id"])

            # Log the instruction being sent to tutor
            truncated_instruction = instruction["text"][:150] + "..." if len(instruction["text"]) > 150 else instruction["text"]
            logger.info(f"[INSTRUCTION → TUTOR] {truncated_instruction}")

            return PromptResponse(
                prompt=instruction["text"],
                session_info=ta.get_session_info(session_id)
            )

        return PromptResponse(prompt="", session_info=ta.get_session_info(session_id))
    except Exception as e:
        logger.error(f"Error in send_instruction_to_tutor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Include Cost Tracking API routes (Phase 4)
from services.CostTracking.api import router as cost_router
app.include_router(cost_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("TEACHING_ASSISTANT_PORT", "8002")))
    uvicorn.run(app, host="0.0.0.0", port=port)
