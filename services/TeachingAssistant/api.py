import sys
import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.TeachingAssistant.teaching_assistant import TeachingAssistant
from services.TeachingAssistant.Memory.consolidator import ConversationWatcher

app = FastAPI(title="Teaching Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "https://tutor-frontend-staging-utmfhquz6a-uc.a.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ta = TeachingAssistant()

# Global conversation watcher for real-time memory processing
conversation_watcher = ConversationWatcher(verbose=True)
# Note: We don't call start() - no file polling needed, only real-time events


class StartSessionRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None


class EndSessionRequest(BaseModel):
    interrupt_audio: bool = True
    session_id: Optional[str] = None


class QuestionAnsweredRequest(BaseModel):
    question_id: str
    is_correct: bool


class PromptResponse(BaseModel):
    prompt: str
    session_info: dict


class ConversationTurnRequest(BaseModel):
    session_id: str
    user_id: str
    user_text: str
    adam_text: str
    timestamp: str


class SessionStartRequest(BaseModel):
    session_id: str
    user_id: str


class MemorySessionEndRequest(BaseModel):
    session_id: str
    user_id: str
    end_time: str


class UserTurnRequest(BaseModel):
    session_id: str
    user_id: str
    user_text: str = ""  # Optional - if empty, just get stored injection
    timestamp: str
    adam_text: str = ""


class MemoryInjectionResponse(BaseModel):
    status: str
    session_id: str
    injection_text: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "TeachingAssistant"}


@app.post("/session/start", response_model=PromptResponse)
def start_session(request: StartSessionRequest):
    try:
        prompt = ta.start_session(request.user_id, request.session_id)
        session_info = ta.get_session_info()
        return PromptResponse(prompt=prompt, session_info=session_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/end", response_model=PromptResponse)
def end_session(request: Optional[EndSessionRequest] = Body(None)):
    try:
        # Try to get session_id from request, or from conversation_watcher, or from ta
        session_id = None
        if request and request.session_id:
            session_id = request.session_id
        elif ta.current_session_id:
            session_id = ta.current_session_id
        else:
            # Try to get the most recent session_id from conversation_watcher
            try:
                if hasattr(conversation_watcher, '_session_caches') and conversation_watcher._session_caches:
                    # Get the most recent session_id
                    session_id = list(conversation_watcher._session_caches.keys())[-1] if conversation_watcher._session_caches else None
            except:
                pass
        
        prompt = ta.end_session(session_id)
        if not prompt:
            raise HTTPException(status_code=400, detail="No active session to end")
        
        session_info = ta.get_session_info()
        return PromptResponse(prompt=prompt, session_info=session_info)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question/answered")
def record_question(request: QuestionAnsweredRequest):
    try:
        ta.record_question_answered(request.question_id, request.is_correct)
        return {"status": "recorded", "session_info": ta.get_session_info()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/info")
def get_session_info():
    return ta.get_session_info()


@app.post("/conversation/turn")
def record_conversation_turn():
    try:
        ta.record_conversation_turn()
        return {"status": "recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/inactivity/check", response_model=PromptResponse)
def check_inactivity():
    try:
        prompt = ta.get_inactivity_prompt()
        if prompt:
            session_info = ta.get_session_info()
            return PromptResponse(prompt=prompt, session_info=session_info)
        return PromptResponse(prompt="", session_info=ta.get_session_info())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/session/start")
def memory_session_start(request: SessionStartRequest):
    """Handle real-time session start event for memory processing."""
    try:
        # Initialize memory retriever if not already initialized for this user
        if not ta.memory_retriever or ta.current_user_id != request.user_id:
            from services.TeachingAssistant.Memory.retriever import MemoryRetriever, MemoryRetrievalWatcher
            ta.memory_retriever = MemoryRetriever(student_id=request.user_id)
            ta.memory_retriever.watcher = MemoryRetrievalWatcher(
                retriever=ta.memory_retriever,
                verbose=True
            )
            ta.current_user_id = request.user_id
        
        # Activate session for memory processing (required for on_user_turn to work)
        # This allows TA-light and TA-deep retrieval to function properly
        if not ta.session_active:
            ta.session_active = True
        
        # Sync session_id
        if ta.current_user_id == request.user_id:
            ta.current_session_id = request.session_id
        
        conversation_watcher.on_session_start(request.session_id, request.user_id)
        return {"status": "ok", "session_id": request.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/turn")
def memory_turn(request: ConversationTurnRequest):
    """Handle real-time conversation turn event for memory processing."""
    try:
        conversation_watcher.on_turn(
            request.session_id,
            request.user_id,
            request.user_text,
            request.adam_text,
            request.timestamp
        )
        return {"status": "ok", "session_id": request.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/session/end")
def memory_session_end(request: MemorySessionEndRequest):
    """Handle real-time session end event for memory processing."""
    try:
        conversation_watcher.on_session_end(request.session_id, request.user_id, request.end_time)
        # Clear conversation history for this session
        if ta.memory_retriever:
            ta.memory_retriever.clear_session_history(request.session_id)
        return {"status": "ok", "session_id": request.session_id}
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in memory_session_end: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/retrieval/user-turn", response_model=MemoryInjectionResponse)
def memory_retrieval_user_turn(request: UserTurnRequest):
    """Handle real-time user turn event for memory retrieval and return injection text."""
    try:
        # Initialize memory retriever if not already initialized for this user
        if not ta.memory_retriever or ta.current_user_id != request.user_id:
            from services.TeachingAssistant.Memory.retriever import MemoryRetriever, MemoryRetrievalWatcher
            ta.memory_retriever = MemoryRetriever(student_id=request.user_id)
            ta.memory_retriever.watcher = MemoryRetrievalWatcher(
                retriever=ta.memory_retriever,
                verbose=True
            )
            ta.current_user_id = request.user_id
        
        # Sync session_id if session is active
        if ta.session_active and ta.current_user_id == request.user_id:
            ta.current_session_id = request.session_id
        
        # Only trigger retrieval if user_text is provided and not empty
        if request.user_text and request.user_text.strip():
            # Call TeachingAssistant's on_user_turn method (triggers retrieval and stores in memory)
            try:
                ta.on_user_turn(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    user_text=request.user_text,
                    timestamp=request.timestamp,
                    adam_text=request.adam_text
                )
            except Exception as e:
                print(f"[INJECTION] API: Error during retrieval: {e}")
                import traceback
                traceback.print_exc()
            
            # During retrieval phase, DON'T get injection text yet
            # Just trigger retrieval and return None - injection will happen later
            injection_text = None
        else:
            # Only get injection when user_text is empty (injection request phase)
            # This happens when injectMemoriesForNextTurn() calls with empty user_text
            injection_text = None
            try:
                injection_text = ta.get_memory_injection(request.session_id)
            except Exception as e:
                print(f"[INJECTION] API: Error getting injection: {e}")
                import traceback
                traceback.print_exc()
        
        # Log injection status
        if injection_text:
            print(f"[INJECTION] API: Returning injection text ({len(injection_text)} chars) for session {request.session_id}")
        else:
            print(f"[INJECTION] API: No injection text available for session {request.session_id}")
        
        return MemoryInjectionResponse(
            status="ok",
            session_id=request.session_id,
            injection_text=injection_text
        )
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"[INJECTION] API Error: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("TEACHING_ASSISTANT_PORT", "8002")))
    uvicorn.run(app, host="0.0.0.0", port=port)

