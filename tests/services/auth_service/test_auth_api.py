import sys
import types
from types import SimpleNamespace

from fastapi.testclient import TestClient

import services.AuthService.auth_api as auth_api
import managers.mongodb_manager as mongodb_manager


def test_gemini_key_endpoint_is_not_exposed():
    with TestClient(auth_api.app) as client:
        response = client.get("/auth/gemini-key")

    assert response.status_code == 404


def test_gemini_token_returns_ephemeral_token(monkeypatch):
    monkeypatch.setattr(auth_api, "get_current_user", lambda request: "user-123")
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "models/test-live")

    created_configs = []

    class FakeAuthTokens:
        def create(self, config):
            created_configs.append(config)
            return types.SimpleNamespace(name="token-abc123")

    class FakeClient:
        def __init__(self, api_key, http_options):
            self.api_key = api_key
            self.http_options = http_options
            self.auth_tokens = FakeAuthTokens()

    fake_google = types.ModuleType("google")
    fake_genai = types.ModuleType("google.genai")
    fake_genai.Client = FakeClient
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    with TestClient(auth_api.app) as client:
        response = client.get("/auth/gemini-token", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 200
    assert response.json() == {"token": "token-abc123", "model": "models/test-live"}
    assert created_configs == [{"uses": 1}]


def test_google_login_sets_oauth_state_cookie(monkeypatch):
    monkeypatch.setattr(
        auth_api.oauth_handler,
        "get_authorization_url",
        lambda: ("https://accounts.google.com/o/oauth2/v2/auth?state=state-123", "state-123"),
    )

    with TestClient(auth_api.app) as client:
        response = client.get("/auth/google")

    assert response.status_code == 200
    assert response.json()["state"] == "state-123"
    assert response.cookies.get(auth_api.OAUTH_STATE_COOKIE) == "state-123"


def test_google_callback_requires_state(monkeypatch):
    called = False

    async def fake_get_user_info(*args, **kwargs):
        nonlocal called
        called = True
        return {"id": "google-user"}

    monkeypatch.setattr(auth_api.oauth_handler, "get_user_info", fake_get_user_info)

    with TestClient(auth_api.app) as client:
        response = client.get("/auth/callback?code=test-code")

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing state parameter"
    assert called is False


def test_google_callback_redirects_with_fragment_not_query(monkeypatch):
    async def fake_get_user_info(code, state, authorization_response):
        assert code == "test-code"
        assert state == "state-123"
        assert "state=state-123" in authorization_response
        return {
            "id": "google-user",
            "email": "student@example.com",
            "name": "Student",
        }

    monkeypatch.setattr(auth_api.oauth_handler, "get_user_info", fake_get_user_info)
    monkeypatch.setattr(
        auth_api.user_manager,
        "get_user_by_google_id",
        lambda google_id: SimpleNamespace(user_id="user-123"),
    )
    monkeypatch.setattr(auth_api.user_manager, "update_last_login", lambda user_id: None)
    monkeypatch.setattr(auth_api, "create_jwt_token", lambda payload: "jwt-123")
    monkeypatch.setattr(
        mongodb_manager,
        "mongo_db",
        SimpleNamespace(
            users=SimpleNamespace(
                find_one=lambda query: {
                    "google_email": "student@example.com",
                    "google_name": "Student",
                }
            )
        ),
    )

    with TestClient(auth_api.app) as client:
        client.cookies.set(auth_api.OAUTH_STATE_COOKIE, "state-123", domain="testserver.local", path="/auth")
        response = client.get(
            "/auth/callback",
            params={"code": "test-code", "state": "state-123"},
            follow_redirects=False,
        )

    assert response.status_code == 307
    location = response.headers["location"]
    assert "#token=jwt-123" in location
    assert "is_new_user=false" in location
    assert "?token=" not in location
