import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.TeachingAssistant.teaching_assistant import TeachingAssistant

app = FastAPI(title="Teaching Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "https://tutor-frontend-staging-utmfhquz6a-uc.a.run.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ta = TeachingAssistant()


class StartSessionRequest(BaseModel):
    user_id: str


class EndSessionRequest(BaseModel):
    interrupt_audio: bool = True


class QuestionAnsweredRequest(BaseModel):
    question_id: str
    is_correct: bool


class PromptResponse(BaseModel):
    prompt: str
    session_info: dict


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "TeachingAssistant"}


@app.post("/session/start", response_model=PromptResponse)
def start_session(request: StartSessionRequest):
    try:
        prompt = ta.start_session(request.user_id)
        session_info = ta.get_session_info()
        return PromptResponse(prompt=prompt, session_info=session_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/end", response_model=PromptResponse)
def end_session(request: Optional[EndSessionRequest] = None):
    try:
        prompt = ta.end_session()
        if not prompt:
            raise HTTPException(status_code=400, detail="No active session to end")
        
        session_info = ta.get_session_info()
        return PromptResponse(prompt=prompt, session_info=session_info)
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("TEACHING_ASSISTANT_PORT", "8002")))
    uvicorn.run(app, host="0.0.0.0", port=port)

