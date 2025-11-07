from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from urllib.parse import urlparse

import requests

from config_manager import ConfigManager
from .khan_questions_loader import load_questions

router = APIRouter()

class Question(BaseModel):
    question: dict = Field(description="The question data")
    answerArea: dict = Field(description="The answer area")
    hints: List = Field(description="List of question hints")

@router.get("/questions/{sample_size}", response_model=List[Question])
async def get_questions(sample_size: int = 14):
    """Endpoint for retrieving questions"""
    data = load_questions(
        sample_size=sample_size
    )
    return data


@router.post("/daily/token")
async def create_daily_token():
    """Provision a Daily meeting token for the configured room."""
    config = ConfigManager()
    room_url = config.get_daily_room_url()

    if not room_url:
        raise HTTPException(status_code=500, detail="Daily room URL is not configured.")

    api_key = config.get_api_key("daily")
    parsed = urlparse(room_url)
    room_name = parsed.path.strip("/ ")

    if not room_name:
        raise HTTPException(status_code=500, detail="Invalid Daily room URL configuration.")

    # If no API key is provided, return the URL so clients can attempt a tokenless join.
    if not api_key:
        return {"token": None, "room_url": room_url, "room_name": room_name}

    try:
        response = requests.post(
            "https://api.daily.co/v1/meeting-tokens",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "properties": {
                    "room_name": room_name,
                    "is_owner": False,
                }
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Daily API error: {exc}") from exc

    payload = response.json()
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=502, detail="Daily API did not return a token.")

    return {"token": token, "room_url": room_url, "room_name": room_name}


@router.post("/voice/start")
async def start_voice_session():
    """Proxy request to the Pipecat bot start endpoint."""
    config = ConfigManager()
    start_url = config.get_pipecat_start_url()
    if not start_url:
        raise HTTPException(
            status_code=500,
            detail="Pipecat start URL is not configured. Set PIPECAT_START_URL in the environment.",
        )

    headers = {"Content-Type": "application/json"}
    api_key = config.get_pipecat_public_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "createDailyRoom": False,
        "dailyRoomProperties": {"start_video_off": True},
    }

    daily_room_url = config.get_daily_room_url()
    if daily_room_url:
        body["dailyRoomUrl"] = daily_room_url

    try:
        response = requests.post(
            start_url,
            headers=headers,
            json=body,
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502, detail=f"Pipecat start error: {exc}"
        ) from exc

    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise HTTPException(status_code=502, detail=payload["error"])

    # If pipecat returns null or empty response, construct our own response
    if not payload or payload is None:
        payload = {}

    # Daily transport expects specific field names: dailyRoom and dailyToken
    # Ensure the client gets the room URL to connect to
    if "dailyRoom" not in payload and daily_room_url:
        payload["dailyRoom"] = daily_room_url

    # Token can be null for public rooms
    if "dailyToken" not in payload:
        payload["dailyToken"] = None

    return payload


def _pipecat_health_url(start_url: str) -> str:
    trimmed = start_url.rstrip("/")
    if trimmed.endswith("/start"):
        trimmed = trimmed[: -len("/start")]
    return f"{trimmed}/health"


@router.get("/voice/status")
async def get_voice_status():
    """Check whether the Pipecat pipeline is reachable."""
    config = ConfigManager()
    start_url = config.get_pipecat_start_url()
    if not start_url:
        raise HTTPException(
            status_code=500,
            detail="Pipecat start URL is not configured. Set PIPECAT_START_URL in the environment.",
        )

    health_url = _pipecat_health_url(start_url)
    headers = {}
    api_key = config.get_pipecat_public_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.get(health_url, headers=headers, timeout=5)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Pipecat health check failed: {exc}",
        ) from exc

    if response.status_code == 200:
        return {"status": "ok"}

    # Treat 404 as "reachable but no health endpoint exposed"
    if response.status_code == 404:
        return {"status": "reachable", "detail": "Health endpoint missing"}

    raise HTTPException(
        status_code=503,
        detail=f"Pipecat health check returned {response.status_code}",
    )
