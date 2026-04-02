from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import services.TeachingAssistant.api as teaching_api


class DummySessionManager:
    def __init__(self):
        self.instructions = []

    def list_active_sessions(self):
        return [
            {
                "session_id": "sess-123",
                "user_id": "user-123",
                "started_at": datetime(2026, 1, 1, 0, 0, 0),
                "websocket_connected": True,
                "sse_connected": False,
                "questions_answered_this_session": 2,
            }
        ]

    def get_session_by_id(self, session_id):
        return {"session_id": session_id, "user_id": "user-123", "started_at": datetime(2026, 1, 1, 0, 0, 0)}

    def push_instruction(self, session_id, instruction):
        self.instructions.append((session_id, instruction))
        return "instr-123"


def create_client(monkeypatch):
    dummy_ta = SimpleNamespace(session_manager=DummySessionManager())
    monkeypatch.setattr(teaching_api, "ta", dummy_ta)
    return TestClient(teaching_api.app)


def test_sessions_active_is_disabled_without_observer_secret(monkeypatch):
    monkeypatch.delenv("OBSERVER_API_KEY", raising=False)

    with create_client(monkeypatch) as client:
        response = client.get("/sessions/active")

    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].lower()


def test_sessions_active_rejects_default_observer_secret(monkeypatch):
    monkeypatch.setenv("OBSERVER_API_KEY", teaching_api.DEFAULT_OBSERVER_API_KEY)

    with create_client(monkeypatch) as client:
        response = client.get(
            "/sessions/active",
            headers={teaching_api.OBSERVER_API_KEY_HEADER: teaching_api.DEFAULT_OBSERVER_API_KEY},
        )

    assert response.status_code == 503


def test_admin_and_listing_endpoints_require_configured_header_secret(monkeypatch):
    monkeypatch.setenv("OBSERVER_API_KEY", "super-secure-observer-key")

    with create_client(monkeypatch) as client:
        list_response = client.get(
            "/sessions/active",
            headers={teaching_api.OBSERVER_API_KEY_HEADER: "super-secure-observer-key"},
        )
        admin_response = client.post(
            "/session/instruction/admin",
            json={"instruction": "Stay on task", "session_id": "sess-123"},
            headers={teaching_api.OBSERVER_API_KEY_HEADER: "super-secure-observer-key"},
        )

    assert list_response.status_code == 200
    assert list_response.json()["sessions"][0]["session_id"] == "sess-123"
    assert admin_response.status_code == 200
    assert admin_response.json()["instruction_id"] == "instr-123"


def test_observer_websocket_is_disabled_without_configured_secret(monkeypatch):
    monkeypatch.delenv("OBSERVER_API_KEY", raising=False)

    with create_client(monkeypatch) as client:
        # The server now closes the WebSocket *before* accepting when the
        # observer key is not configured, so the disconnect may surface
        # during the connect handshake rather than during receive_json.
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/ws/feed/observe?session_id=sess-123") as websocket:
                websocket.receive_json()

    assert excinfo.value.code == 4001


def test_observer_websocket_rejects_invalid_auth_message(monkeypatch):
    monkeypatch.setenv("OBSERVER_API_KEY", "super-secure-observer-key")

    with create_client(monkeypatch) as client:
        with client.websocket_connect("/ws/feed/observe?session_id=sess-123") as websocket:
            websocket.send_json({"type": "auth", "api_key": "wrong-key"})

            with pytest.raises(WebSocketDisconnect) as excinfo:
                websocket.receive_json()

    assert excinfo.value.code == 4001


def test_observer_websocket_accepts_valid_auth_message(monkeypatch):
    monkeypatch.setenv("OBSERVER_API_KEY", "super-secure-observer-key")

    with create_client(monkeypatch) as client:
        with client.websocket_connect("/ws/feed/observe?session_id=sess-123") as websocket:
            websocket.send_json({"type": "auth", "api_key": "super-secure-observer-key"})
            session_info = websocket.receive_json()

    assert session_info["type"] == "session_info"
    assert session_info["data"]["session_id"] == "sess-123"
    assert session_info["data"]["user_id"] == "user-123"


def test_user_instruction_endpoint_rejects_foreign_session(monkeypatch):
    monkeypatch.setattr(teaching_api, "get_current_user", lambda request: "user-123")

    dummy_ta = SimpleNamespace(
        session_manager=SimpleNamespace(
            get_session_by_id=lambda session_id: {
                "session_id": session_id,
                "user_id": "user-999",
            },
            push_instruction=lambda session_id, instruction: "instr-123",
        ),
        get_active_session=lambda user_id: {
            "session_id": "sess-active",
            "user_id": user_id,
        },
    )
    monkeypatch.setattr(teaching_api, "ta", dummy_ta)

    with TestClient(teaching_api.app) as client:
        response = client.post(
            "/session/instruction",
            json={"instruction": "Stay focused", "session_id": "sess-foreign"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 403
    assert "own session" in response.json()["detail"]
