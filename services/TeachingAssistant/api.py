import sys
import os

# ============================================================================
# Load Environment Variables FIRST (CRITICAL for Biographer and Memory system)
# ============================================================================
from dotenv import load_dotenv
from pathlib import Path

# Get project root (2 levels up: api.py -> TeachingAssistant -> services -> root)
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
_env_path = _project_root / '.env'

# Load .env file explicitly
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)
    print(f"[API] Loaded environment variables from: {_env_path}")
else:
    print(f"[API] WARNING: .env file not found at: {_env_path}")
    load_dotenv()  # Try to load from current directory as fallback

# Continue with other imports...
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
from shared.auth_middleware import get_current_user, get_user_from_token
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.cache_middleware import CacheControlMiddleware

# v4+v5 Cognitive Memory Pipeline imports
from services.TeachingAssistant.core.config import TeachingAssistantConfig, config as ta_config
from services.TeachingAssistant.core.context import SessionContext, Event, EventType
from services.TeachingAssistant.core.event_processor import EventProcessor, ContextManager
from services.TeachingAssistant.Memory.vector_store import MemoryStore
from services.TeachingAssistant.Memory.retriever import MemoryRetriever
from services.TeachingAssistant.Memory.extractor import MemoryExtractor
from services.TeachingAssistant.skills_manager import SkillsManager
from services.TeachingAssistant.handlers.injection_manager import InjectionManager

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

# Global task for event processing loop (v4 improvement)
event_processing_task = None


# ============================================================================
# Lifespan Context Manager (Start/Stop Event Processing Loop) - v4 improvement
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop event processing loop"""
    global ta, event_processing_task

    # Start event processing loop if TeachingAssistant has ongoing method
    if hasattr(ta, 'running') and hasattr(ta, 'ongoing'):
        ta.running = True
        event_processing_task = asyncio.create_task(ta.ongoing())
        logger.info("[API] Started event processing loop")

    yield

    # Shutdown
    logger.info("[API] Shutting down event processing loop...")
    if hasattr(ta, 'running'):
        ta.running = False
    if event_processing_task:
        event_processing_task.cancel()
        try:
            await event_processing_task
        except asyncio.CancelledError:
            pass
    logger.info("[API] Event processing loop stopped")


app = FastAPI(title="Teaching Assistant API", lifespan=lifespan)

# Add timing middleware for performance monitoring (Phase 1)
app.add_middleware(UnpluggedTimingMiddleware)

# Cache Control (Phase 7)
app.add_middleware(CacheControlMiddleware)

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
    try:
        return await asyncio.wait_for(call_next(request), timeout=30.0)
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

# ============================================================================
# v4+v5 Cognitive Memory Pipeline Components
# ============================================================================

# Initialize context manager for session state
context_manager = ContextManager(config=ta_config)

# Initialize skills manager with default skills
skills_manager = SkillsManager(config=ta_config, load_defaults=True)

# Initialize event processor
event_processor = EventProcessor(
    context_manager=context_manager,
    skills_manager=skills_manager,
    config=ta_config
)

# Initialize injection manager
injection_manager = InjectionManager(
    session_manager=ta.session_manager,
    config=ta_config
)

# Per-user memory stores and retrievers (initialized on session start)
user_memory_stores: Dict[str, MemoryStore] = {}
user_memory_retrievers: Dict[str, MemoryRetriever] = {}

# Memory extractor (singleton)
memory_extractor = MemoryExtractor()

logger.info("[API] v4+v5 Cognitive Memory Pipeline initialized")

# DASH API URL for pre-loading questions
DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")


# ============================================================================
# Feed-to-Event Converter (v4 improvement)
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
            type=EventType.TEXT,
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
            type=EventType.AUDIO,
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
            type=EventType.MEDIA,
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
    pass  # user_id now comes from JWT


class EndSessionRequest(BaseModel):
    interrupt_audio: bool = True


class QuestionAnsweredRequest(BaseModel):
    question_id: str
    is_correct: bool


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
def start_session(http_request: Request, request: Optional[StartSessionRequest] = None):
    """Start a new tutoring session"""
    user_id = get_current_user(http_request)
    try:
        result = ta.start_session(user_id)
        return PromptResponse(
            prompt=result["prompt"],
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
def end_session(http_request: Request, request: Optional[EndSessionRequest] = None):
    """End the current tutoring session"""
    user_id = get_current_user(http_request)
    try:
        # Get active session for user
        session = ta.get_active_session(user_id)
        if not session:
            return PromptResponse(
                prompt="",
                session_info={'session_active': False, 'user_id': user_id}
            )

        result = ta.end_session(session["session_id"])

        # Pre-load next session questions in background (non-blocking)
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

        return PromptResponse(
            prompt=result["prompt"],
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
            raise HTTPException(status_code=404, detail="No active session")

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

    # 2. Get active session
    session = ta.get_active_session(user_id)
    if not session:
        await websocket.close(code=4002, reason="No active session")
        return

    session_id = session["session_id"]

    # 3. Accept connection and update status
    await websocket.accept()
    ta.session_manager.set_connection_status(session_id, websocket=True)
    logger.info(f"[WS] WebSocket connected for session {session_id}")

    try:
        # 4. Message handling loop
        while True:
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
        ta.session_manager.set_connection_status(session_id, websocket=False)
    except Exception as e:
        logger.error(f"[WS] WebSocket error for session {session_id}: {e}")
        ta.session_manager.set_connection_status(session_id, websocket=False)


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
    # TODO: Implement audio analysis
    logger.debug(f"[AUDIO] Session {session_id}: received audio at {timestamp}")

    # Broadcast to observers
    await broadcast_to_observers(session_id, {
        "type": "audio",
        "timestamp": timestamp,
        "data": {"audio": audio_base64}
    })


async def process_media(session_id: str, media_base64: str, timestamp: str):
    """Process incoming media (video frames) and broadcast to observers"""
    # TODO: Implement media analysis
    logger.debug(f"[MEDIA] Session {session_id}: received frame at {timestamp}")

    # Broadcast to observers
    await broadcast_to_observers(session_id, {
        "type": "media",
        "timestamp": timestamp,
        "data": {"media": media_base64}
    })


def _get_or_create_memory_components(user_id: str) -> tuple:
    """Get or create memory store and retriever for a user"""
    global user_memory_stores, user_memory_retrievers

    if user_id not in user_memory_stores:
        try:
            store = MemoryStore(user_id=user_id)
            user_memory_stores[user_id] = store
            user_memory_retrievers[user_id] = MemoryRetriever(store)
            logger.info(f"[MEMORY] Created memory components for user {user_id}")
        except Exception as e:
            logger.error(f"[MEMORY] Failed to create memory components: {e}")
            return None, None

    return user_memory_stores.get(user_id), user_memory_retrievers.get(user_id)


def _initialize_session_context(session_id: str, user_id: str, student_name: str = None, biography: str = None) -> SessionContext:
    """Initialize session context with student info"""
    context = context_manager.get_or_create_context(
        session_id=session_id,
        user_id=user_id,
        student_name=student_name,
        biography=biography,
        is_first_session=(biography is None or biography == "")
    )

    # Inject biography context if available
    if biography and ta_config.enable_biographer:
        injection_manager.inject_biography_context(
            session_id=session_id,
            biography=biography,
            student_name=student_name
        )

    return context


async def process_transcript(session_id: str, transcript: str, timestamp: str, speaker: str = "tutor"):
    """Process incoming transcript with memory integration"""
    speaker_label = "USER" if speaker == "user" else "TUTOR"
    logger.debug(f"[TRANSCRIPT] Session {session_id} [{speaker_label}]: {transcript[:100] if transcript else 'empty'}...")

    # Broadcast to observers
    await broadcast_to_observers(session_id, {
        "type": "transcript",
        "timestamp": timestamp,
        "data": {"transcript": transcript, "speaker": speaker}
    })

    # Get session info for user_id
    session = ta.session_manager.get_session_by_id(session_id)
    if not session:
        return

    user_id = session.get("user_id")
    if not user_id:
        return

    # Store conversation turn in session for biography generation
    speaker_name = "student" if speaker == "user" else "adam"
    ta.session_manager.add_conversation_turn(
        session_id=session_id,
        speaker=speaker_name,
        text=transcript
    )
    logger.debug(f"[TRANSCRIPT] Stored turn: {speaker_name} in session {session_id}")

    # Get or create memory components
    memory_store, memory_retriever = _get_or_create_memory_components(user_id)

    # Update context
    context = context_manager.get_context(session_id)
    if context:
        if speaker == "user":
            context.last_user_text = transcript
        else:
            context.last_tutor_text = transcript

    # Process user turns for memory retrieval
    if speaker == "user" and memory_retriever and ta_config.enable_semantic_search:
        try:
            # Trigger memory retrieval
            memory_retriever.on_user_turn(
                session_id=session_id,
                user_id=user_id,
                user_text=transcript,
                timestamp=time.time(),
                tutor_text=context.last_tutor_text if context else ""
            )

            # Check for memory injection
            injection = memory_retriever.get_memory_injection(session_id)
            if injection:
                # Queue instruction for SSE delivery
                instruction_id = ta.session_manager.push_instruction(session_id, injection)
                logger.info(f"[MEMORY] Injected memory context for session {session_id}")

        except Exception as e:
            logger.error(f"[MEMORY] Memory retrieval error: {e}")

    # Execute skills based on updated context
    if context and ta_config.enable_skills:
        try:
            event = Event(
                session_id=session_id,
                user_id=user_id,
                event_type=EventType.USER_MESSAGE if speaker == "user" else EventType.TUTOR_MESSAGE,
                user_text=transcript if speaker == "user" else None,
                tutor_text=transcript if speaker == "tutor" else None
            )

            injections = event_processor.process_event(event)

            for inj in injections:
                ta.session_manager.push_instruction(session_id, inj)
                logger.info(f"[SKILLS] Generated instruction for session {session_id}")

        except Exception as e:
            logger.error(f"[SKILLS] Error executing skills: {e}")


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

    return EventSourceResponse(event_generator())


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

        logger.info(f"[INSTRUCTION] Pushed instruction {instruction_id} to session {session_id}")

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

        logger.info(f"[INSTRUCTION/ADMIN] Pushed instruction {instruction_id} to session {request.session_id}")

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
            return PromptResponse(
                prompt=instruction["text"],
                session_info=ta.get_session_info(session_id)
            )

        return PromptResponse(prompt="", session_info=ta.get_session_info(session_id))
    except Exception as e:
        logger.error(f"Error in send_instruction_to_tutor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# v5 Cognitive Memory Pipeline Endpoints
# ============================================================================

class MemorySearchRequest(BaseModel):
    query: str
    top_k: int = 10
    memory_type: Optional[str] = None


class MemoryExtractionRequest(BaseModel):
    exchanges: List[Dict[str, str]]  # List of {student: "...", tutor: "..."}


@app.get("/memory/stats")
def get_memory_stats(http_request: Request):
    """Get memory system statistics for the current user"""
    user_id = get_current_user(http_request)
    try:
        memory_store, _ = _get_or_create_memory_components(user_id)
        if not memory_store:
            return {"enabled": False, "error": "Memory system not available"}

        stats = memory_store.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search")
def search_memories(http_request: Request, request: MemorySearchRequest):
    """Search for similar memories"""
    user_id = get_current_user(http_request)
    try:
        memory_store, _ = _get_or_create_memory_components(user_id)
        if not memory_store:
            raise HTTPException(status_code=503, detail="Memory system not available")

        from services.TeachingAssistant.Memory.schema import MemoryType
        mem_type = None
        if request.memory_type:
            try:
                mem_type = MemoryType(request.memory_type)
            except ValueError:
                pass

        results = memory_store.search(
            query=request.query,
            student_id=user_id,
            mem_type=mem_type,
            top_k=request.top_k
        )

        return {
            "query": request.query,
            "results": [
                {
                    "text": r["memory"].text,
                    "type": r["memory"].type.value,
                    "importance": r["memory"].importance,
                    "score": r["score"],
                    "timestamp": r["memory"].timestamp.isoformat() if hasattr(r["memory"].timestamp, 'isoformat') else r["memory"].timestamp
                }
                for r in results
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/extract")
def extract_memories(http_request: Request, request: MemoryExtractionRequest):
    """Extract memories from conversation exchanges"""
    user_id = get_current_user(http_request)
    try:
        session = ta.get_active_session(user_id)
        session_id = session["session_id"] if session else "manual-extraction"

        result = memory_extractor.extract_memories_batch(
            student_id=user_id,
            session_id=session_id,
            exchanges=request.exchanges
        )

        # Save extracted memories to vector store
        memory_store, _ = _get_or_create_memory_components(user_id)
        if memory_store and result["memories"]:
            saved_count = memory_store.save_memories_batch(result["memories"])
            logger.info(f"[MEMORY] Saved {saved_count} memories for user {user_id}")

        return {
            "memories_extracted": len(result["memories"]),
            "emotions_detected": result["emotions"],
            "breakthroughs": result["breakthroughs"],
            "unfinished_topics": result["unfinished_topics"],
            "memories": [
                {
                    "text": m.text,
                    "type": m.type.value,
                    "importance": m.importance,
                    "emotion": m.metadata.get("emotion")
                }
                for m in result["memories"]
            ]
        }
    except Exception as e:
        logger.error(f"Error extracting memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/student/biography")
def get_student_biography(http_request: Request):
    """Get current student biography"""
    user_id = get_current_user(http_request)
    try:
        biography = ta.get_student_biography(user_id)
        return {
            "user_id": user_id,
            "biography": biography,
            "has_biography": bool(biography)
        }
    except Exception as e:
        logger.error(f"Error getting biography: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/skills/info")
def get_skills_info():
    """Get information about registered skills"""
    return skills_manager.get_info()


@app.get("/config/info")
def get_config_info():
    """Get current configuration (non-sensitive values)"""
    return {
        "config": ta_config.to_dict(),
        "validation": ta_config.validate()
    }


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("TEACHING_ASSISTANT_PORT", "8002")))
    uvicorn.run(app, host="0.0.0.0", port=port)
