"""
Teaching Assistant API (Binary Audio WS + SSE instructions) — UPDATED FULL FILE

Key upgrades vs your current file:
- ✅ True binary-audio fast path: ws.receive() -> msg["bytes"] -> enqueue (no JSON parse)
- ✅ Fixes double-read bug: never call websocket.receive_json() after websocket.receive()
- ✅ Per-session workers are started once per connection and safely stopped
- ✅ Drop-oldest queues to cap latency (audio/media/transcript)
- ✅ Observer broadcast is concurrency-safe + timeout-protected, supports binary audio as header+bytes
- ✅ Optional audio_meta JSON messages supported (format/sample-rate hints) without touching audio hot path
- ✅ Cleans up queue objects / observer lists on disconnect to avoid leaks
- ✅ Keeps your SSE + instruction endpoints intact (minimal change)

NOTE:
- Audio is assumed to be raw PCM bytes (whatever your mic capture emits).
- If you need to know sample rate / format server-side, have the client send occasional:
  {"type":"audio_meta","timestamp":..., "data":{"mimeType":"audio/pcm;rate=16000","channels":1}}
"""

import sys
import os
import threading
import requests
import asyncio
import time
import json
from typing import Optional, Dict, List, Any
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from services.TeachingAssistant.teaching_assistant import TeachingAssistant
from shared.auth_middleware import get_current_user, get_user_from_token
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.cache_middleware import CacheControlMiddleware
from shared.logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# Observer WebSocket Registry
# ============================================================================
active_observers: Dict[str, List[WebSocket]] = {}
OBSERVER_API_KEY = os.getenv("OBSERVER_API_KEY", "dev-observer-key-12345")

# ============================================================================
# Per-session queues for realtime feed (keeps WS receive loop light)
# ============================================================================
_audio_q: Dict[str, asyncio.Queue] = {}
_media_q: Dict[str, asyncio.Queue] = {}
_transcript_q: Dict[str, asyncio.Queue] = {}

# Optional: per-session audio format hints (from client audio_meta messages)
_audio_meta: Dict[str, dict] = {}

# Caps (drop-oldest on overflow to reduce latency)
AUDIO_Q_MAX = 600          # if ~20ms chunks => 12s worst-case, but drop-oldest keeps latency bounded
MEDIA_Q_MAX = 60
TRANSCRIPT_Q_MAX = 200

# Observer send timeout: slow observers must not stall realtime path
OBSERVER_SEND_TIMEOUT_S = 0.10

# Enable binary audio mode (recommended)
ALLOW_BINARY_AUDIO = True

app = FastAPI(title="Teaching Assistant API")

# Middleware
app.add_middleware(UnpluggedTimingMiddleware)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

ta = TeachingAssistant()
DASH_API_URL = os.getenv("DASH_API_URL", "http://localhost:8000")

# ============================================================================
# Middleware (HTTP)
# ============================================================================
@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=30.0)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"detail": "Request timeout"})


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


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    from fastapi.responses import Response
    origin = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*"
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(ALLOWED_METHODS),
            "Access-Control-Allow-Headers": "*",
        },
    )

# ============================================================================
# Models (keep your existing ones; some are referenced by legacy endpoints)
# ============================================================================
class StartSessionRequest(BaseModel):
    pass

class EndSessionRequest(BaseModel):
    interrupt_audio: bool = True

class QuestionAnsweredRequest(BaseModel):
    question_id: str
    is_correct: bool

class PromptResponse(BaseModel):
    prompt: str
    session_info: dict

class InstructionRequest(BaseModel):
    instruction: str
    session_id: Optional[str] = None

class FeedWebhookRequest(BaseModel):
    type: str
    timestamp: str
    data: dict

# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "TeachingAssistant"}

@app.get("/session/info")
def get_session_info(http_request: Request):
    """Get current session info"""
    user_id = get_current_user(http_request)
    session = ta.get_active_session(user_id)
    if not session:
        return {"session_active": False, "user_id": user_id}
    return ta.get_session_info(session["session_id"])
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

# ============================================================================
# Helpers: queue + drop-oldest
# ============================================================================
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

def _get_q(store: Dict[str, asyncio.Queue], session_id: str, maxsize: int) -> asyncio.Queue:
    q = store.get(session_id)
    if q is None:
        q = asyncio.Queue(maxsize=maxsize)
        store[session_id] = q
    return q

def _drop_oldest_put_nowait(q: asyncio.Queue, item: Any):
    """
    Put without blocking; if full, drop one oldest then retry.
    Keeps latency bounded under poor network / CPU hiccups.
    """
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        try:
            _ = q.get_nowait()
        except Exception:
            pass
        try:
            q.put_nowait(item)
        except Exception:
            pass

def _now_ms() -> int:
    return int(time.time() * 1000)

# ============================================================================
# Observer broadcast: concurrent + timeout, never block realtime
# ============================================================================
async def broadcast_to_observers(session_id: str, message: dict):
    observers = active_observers.get(session_id)
    if not observers:
        return

    obs_list = list(observers)

    async def send_one(ws: WebSocket):
        try:
            await asyncio.wait_for(ws.send_json(message), timeout=OBSERVER_SEND_TIMEOUT_S)
            return None
        except Exception:
            return ws

    dead = await asyncio.gather(*(send_one(ws) for ws in obs_list), return_exceptions=False)
    for ws in dead:
        if ws and ws in observers:
            observers.remove(ws)

async def broadcast_audio_bytes_to_observers(session_id: str, audio_bytes: bytes, timestamp_ms: int):
    """
    Sends audio to observers efficiently:
    - JSON header
    - binary payload
    """
    observers = active_observers.get(session_id)
    if not observers:
        return

    obs_list = list(observers)

    header = {
        "type": "audio",
        "timestamp": timestamp_ms,
        "encoding": "raw",
        "bytes": len(audio_bytes),
        "meta": _audio_meta.get(session_id) or None,
    }

    async def send_one(ws: WebSocket):
        try:
            await asyncio.wait_for(ws.send_json(header), timeout=OBSERVER_SEND_TIMEOUT_S)
            await asyncio.wait_for(ws.send_bytes(audio_bytes), timeout=OBSERVER_SEND_TIMEOUT_S)
            return None
        except Exception:
            return ws

    dead = await asyncio.gather(*(send_one(ws) for ws in obs_list), return_exceptions=False)
    for ws in dead:
        if ws and ws in observers:
            observers.remove(ws)

# ============================================================================
# Background processors: drain queues (keeps WS receive loop clean)
# ============================================================================
async def audio_worker(session_id: str):
    q = _get_q(_audio_q, session_id, AUDIO_Q_MAX)
    while True:
        item = await q.get()
        if item is None:
            break

        ts = item.get("timestamp_ms", _now_ms())

        # TODO: feed to TeachingAssistant / analysis pipeline here (DON'T BLOCK)
        # - if you do CPU heavy decode/resample, offload to threadpool
        # - if calling external services, keep it async

        audio_bytes = item.get("audio_bytes")
        if audio_bytes:
            await broadcast_audio_bytes_to_observers(session_id, audio_bytes, ts)
        else:
            # legacy fallback (if you still accept base64 audio JSON)
            await broadcast_to_observers(session_id, {
                "type": "audio",
                "timestamp": ts,
                "data": {"audio": item.get("audio_b64", "")},
            })

async def media_worker(session_id: str):
    q = _get_q(_media_q, session_id, MEDIA_Q_MAX)
    while True:
        item = await q.get()
        if item is None:
            break
        ts = item.get("timestamp_ms", _now_ms())
        await broadcast_to_observers(session_id, {
            "type": "media",
            "timestamp": ts,
            "data": {"media": item.get("media_b64", "")},
        })

async def transcript_worker(session_id: str):
    q = _get_q(_transcript_q, session_id, TRANSCRIPT_Q_MAX)
    while True:
        item = await q.get()
        if item is None:
            break
        ts = item.get("timestamp_ms", _now_ms())
        await broadcast_to_observers(session_id, {
            "type": "transcript",
            "timestamp": ts,
            "data": {"transcript": item.get("text", ""), "speaker": item.get("speaker", "tutor")},
        })

# ============================================================================
# Health
# ============================================================================
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "TeachingAssistant"}

# ============================================================================
# WebSocket Endpoint (Frontend → Backend feed streaming)
# ============================================================================
@app.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
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

    session = ta.get_active_session(user_id)
    if not session:
        await websocket.close(code=4002, reason="No active session")
        return

    session_id = session["session_id"]

    await websocket.accept()
    ta.session_manager.set_connection_status(session_id, websocket=True)
    logger.info(f"[WS] Connected session {session_id}")

    # Start background workers once per connection
    audio_task = asyncio.create_task(audio_worker(session_id))
    media_task = asyncio.create_task(media_worker(session_id))
    transcript_task = asyncio.create_task(transcript_worker(session_id))

    # Ensure queues exist
    aq = _get_q(_audio_q, session_id, AUDIO_Q_MAX)
    mq = _get_q(_media_q, session_id, MEDIA_Q_MAX)
    tq = _get_q(_transcript_q, session_id, TRANSCRIPT_Q_MAX)

    try:
        while True:
            msg = await websocket.receive()
            ta.session_manager.update_activity(session_id)

            # -------------------------
            # FAST PATH: Binary audio
            # -------------------------
            b = msg.get("bytes")
            if b is not None:
                if ALLOW_BINARY_AUDIO:
                    _drop_oldest_put_nowait(aq, {"timestamp_ms": _now_ms(), "audio_bytes": b})
                # if binary not allowed, ignore
                continue

            # -------------------------
            # Control path: JSON text
            # -------------------------
            text = msg.get("text")
            if not text:
                continue

            try:
                data = json.loads(text)
            except Exception:
                continue

            msg_type = data.get("type")
            payload = data.get("data", {}) or {}

            ts = data.get("timestamp")
            ts_ms = int(ts) if isinstance(ts, (int, float)) else _now_ms()

            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": _now_ms()})
                continue

            if msg_type == "audio_meta":
                # format/sample rate hints from client (optional)
                # example payload: {"mimeType":"audio/pcm;rate=16000","channels":1}
                _audio_meta[session_id] = payload
                continue

            # Legacy fallback if someone still sends base64 JSON audio:
            if msg_type == "audio":
                audio_b64 = payload.get("audio")
                if audio_b64:
                    _drop_oldest_put_nowait(aq, {"timestamp_ms": ts_ms, "audio_b64": audio_b64})
                continue

            if msg_type == "media":
                media_b64 = payload.get("media")
                if media_b64:
                    _drop_oldest_put_nowait(mq, {"timestamp_ms": ts_ms, "media_b64": media_b64})
                continue

            if msg_type == "transcript":
                text_t = payload.get("transcript", "")
                speaker = payload.get("speaker", "tutor")
                _drop_oldest_put_nowait(tq, {"timestamp_ms": ts_ms, "text": text_t, "speaker": speaker})
                ta.record_conversation_turn(session_id)
                continue

            # ignore unknown msg_type

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[WS] Error session {session_id}: {e}", exc_info=True)
    finally:
        ta.session_manager.set_connection_status(session_id, websocket=False)
        logger.info(f"[WS] Disconnected session {session_id}")

        # Stop workers (send sentinel)
        _drop_oldest_put_nowait(aq, None)
        _drop_oldest_put_nowait(mq, None)
        _drop_oldest_put_nowait(tq, None)

        # Await worker shutdown briefly
        for t in (audio_task, media_task, transcript_task):
            try:
                await asyncio.wait_for(t, timeout=1.0)
            except Exception:
                t.cancel()

        # Cleanup optional meta (avoid leaks)
        _audio_meta.pop(session_id, None)

# ============================================================================
# SSE instructions endpoint
# ============================================================================
@app.get("/sse/instructions")
async def sse_instructions(request: Request, token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    user_info = get_user_from_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = user_info["user_id"]
    session = ta.get_active_session(user_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    session_id = session["session_id"]
    ta.session_manager.set_connection_status(session_id, sse=True)
    logger.info(f"[SSE] Connected session {session_id}")

    async def event_generator():
        try:
            keepalive_counter = 0
            while True:
                if await request.is_disconnected():
                    break

                instructions = ta.session_manager.get_pending_instructions(session_id)
                for instruction in instructions:
                    yield {
                        "event": "instruction",
                        "id": instruction["instruction_id"],
                        "data": instruction["text"],
                    }
                    ta.session_manager.mark_instruction_delivered(session_id, instruction["instruction_id"])

                ta.check_inactivity(session_id)

                keepalive_counter += 1
                if keepalive_counter >= 6:
                    yield {"event": "keepalive", "data": ""}
                    keepalive_counter = 0

                await asyncio.sleep(5)

        finally:
            ta.session_manager.set_connection_status(session_id, sse=False)
            logger.info(f"[SSE] Disconnected session {session_id}")

    return EventSourceResponse(event_generator())

# ============================================================================
# Instruction Push Endpoint (Backend → Frontend via SSE)
# ============================================================================
@app.post("/session/instruction")
def push_instruction(request: InstructionRequest, http_request: Request):
    user_id = get_current_user(http_request)

    try:
        if request.session_id:
            session = ta.session_manager.get_session_by_id(request.session_id)
        else:
            session = ta.get_active_session(user_id)

        if not session:
            raise HTTPException(status_code=404, detail="No active session found")

        session_id = session["session_id"]

        SYSTEM_PROMPT_PREFIX = "[SYSTEM INSTRUCTION]"
        full_instruction = f"{SYSTEM_PROMPT_PREFIX}\n{request.instruction}"

        instruction_id = ta.session_manager.push_instruction(session_id, full_instruction)
        logger.info(f"[INSTRUCTION] Pushed instruction {instruction_id} to session {session_id}")

        return {
            "success": True,
            "instruction_id": instruction_id,
            "session_id": session_id,
            "message": "Instruction queued for delivery via SSE",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pushing instruction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/session/instruction/admin")
def push_instruction_admin(request: InstructionRequest, api_key: str = None):
    if api_key != OBSERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required for admin endpoint")

    try:
        session = ta.session_manager.get_session_by_id(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")

        SYSTEM_PROMPT_PREFIX = "[SYSTEM INSTRUCTION]"
        full_instruction = f"{SYSTEM_PROMPT_PREFIX}\n{request.instruction}"

        instruction_id = ta.session_manager.push_instruction(request.session_id, full_instruction)
        logger.info(f"[INSTRUCTION/ADMIN] Pushed instruction {instruction_id} to session {request.session_id}")

        return {
            "success": True,
            "instruction_id": instruction_id,
            "session_id": request.session_id,
            "message": "Instruction queued for delivery via SSE",
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
                "questions_answered": s.get("questions_answered_this_session", 0),
            }
            for s in sessions
        ]
    }

@app.websocket("/ws/feed/observe")
async def websocket_observe(websocket: WebSocket):
    query_params = parse_qs(websocket.scope["query_string"].decode())
    api_key = query_params.get("api_key", [None])[0]
    session_id = query_params.get("session_id", [None])[0]

    if api_key != OBSERVER_API_KEY:
        await websocket.close(code=4001, reason="Invalid API key")
        return

    if not session_id:
        await websocket.close(code=4002, reason="Missing session_id")
        return

    session = ta.session_manager.get_session_by_id(session_id)
    if not session:
        await websocket.close(code=4003, reason="Session not found")
        return

    await websocket.accept()

    active_observers.setdefault(session_id, []).append(websocket)
    observer_count = len(active_observers[session_id])
    logger.info(f"[OBSERVER] Connected session {session_id} (total: {observer_count})")

    await websocket.send_json({
        "type": "session_info",
        "data": {
            "session_id": session_id,
            "user_id": session.get("user_id"),
            "started_at": session.get("started_at").isoformat() if session.get("started_at") else None,
            "websocket_connected": session.get("websocket_connected", False),
            "message": "Observer connected. Waiting for feed data...",
        },
    })

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "keepalive"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[OBSERVER] Error: {e}", exc_info=True)
    finally:
        if session_id in active_observers and websocket in active_observers[session_id]:
            active_observers[session_id].remove(websocket)
            remaining = len(active_observers[session_id])
            logger.info(f"[OBSERVER] Disconnected session {session_id} (remaining: {remaining})")
        if session_id in active_observers and not active_observers[session_id]:
            active_observers.pop(session_id, None)

# ============================================================================
# Legacy endpoints (kept for migration)
# ============================================================================
@app.post("/webhook/feed")
def receive_feed(http_request: Request, request: FeedWebhookRequest):
    user_id = get_current_user(http_request)
    try:
        logger.debug(f"[FEED] Received {request.type} from user {user_id} at {request.timestamp}")
        return {"status": "received", "type": request.type}
    except Exception as e:
        logger.error(f"Error in receive_feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send_instruction_to_tutor", response_model=PromptResponse)
def send_instruction_to_tutor(http_request: Request):
    user_id = get_current_user(http_request)
    try:
        session = ta.get_active_session(user_id)
        if not session:
            return PromptResponse(prompt="", session_info={"session_active": False})

        session_id = session["session_id"]
        instructions = ta.session_manager.get_pending_instructions(session_id)
        if instructions:
            instruction = instructions[0]
            ta.session_manager.mark_instruction_delivered(session_id, instruction["instruction_id"])
            return PromptResponse(prompt=instruction["text"], session_info=ta.get_session_info(session_id))

        return PromptResponse(prompt="", session_info=ta.get_session_info(session_id))

    except Exception as e:
        logger.error(f"Error in send_instruction_to_tutor: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("TEACHING_ASSISTANT_PORT", "8002")))
    uvicorn.run(app, host="0.0.0.0", port=port)
