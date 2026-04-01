from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

import managers.mongodb_manager as mongodb_manager
import services.AuthService.auth_api as auth_api
from services.AuthService.jwt_utils import (
    create_jwt_token,
    create_setup_token,
    verify_setup_token,
    verify_token,
)
from shared import auth_middleware
from shared import jwt_config


def test_verify_token_accepts_only_auth_tokens():
    auth_token = create_jwt_token(
        {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-123",
        }
    )
    setup_token = create_setup_token(
        {
            "id": "google-123",
            "email": "student@example.com",
            "name": "Student",
            "picture": "https://example.com/pic.png",
        }
    )

    auth_payload = verify_token(auth_token)
    assert auth_payload is not None
    assert auth_payload["sub"] == "user-123"
    assert auth_payload["token_use"] == "auth"

    assert verify_setup_token(auth_token) is None
    assert verify_token(setup_token) is None


def test_complete_setup_accepts_setup_token_and_returns_auth_token(monkeypatch):
    setup_token = create_setup_token(
        {
            "id": "google-123",
            "email": "student@example.com",
            "name": "Student",
            "picture": "https://example.com/pic.png",
        }
    )

    monkeypatch.setattr(
        auth_api.user_manager,
        "create_google_user",
        lambda **kwargs: SimpleNamespace(user_id="user-123", age=12, current_grade="GRADE_7"),
    )
    monkeypatch.setattr(
        mongodb_manager,
        "mongo_db",
        SimpleNamespace(
            users=SimpleNamespace(
                find_one=lambda query: {
                    "user_id": "user-123",
                    "google_email": "student@example.com",
                    "google_name": "Student",
                }
            )
        ),
    )

    with TestClient(auth_api.app) as client:
        response = client.post(
            "/auth/complete-setup",
            json={"setup_token": setup_token, "user_type": "student", "age": 12},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["is_new_user"] is True
    assert body["user"]["user_id"] == "user-123"
    issued_payload = verify_token(body["token"])
    assert issued_payload is not None
    assert issued_payload["sub"] == "user-123"


def test_complete_setup_rejects_auth_token(monkeypatch):
    auth_token = create_jwt_token(
        {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-123",
        }
    )

    create_calls = []
    monkeypatch.setattr(
        auth_api.user_manager,
        "create_google_user",
        lambda **kwargs: create_calls.append(kwargs),
    )

    with TestClient(auth_api.app) as client:
        response = client.post(
            "/auth/complete-setup",
            json={"setup_token": auth_token, "user_type": "student", "age": 12},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired setup token"
    assert create_calls == []


def test_auth_me_rejects_setup_tokens():
    setup_token = create_setup_token(
        {
            "id": "google-123",
            "email": "student@example.com",
            "name": "Student",
        }
    )

    with TestClient(auth_api.app) as client:
        response = client.get("/auth/me", headers={"Authorization": f"Bearer {setup_token}"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_auth_middleware_only_accepts_auth_tokens():
    auth_token = create_jwt_token(
        {
            "user_id": "user-456",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-456",
        }
    )
    setup_token = create_setup_token(
        {
            "id": "google-456",
            "email": "student@example.com",
            "name": "Student",
        }
    )

    request = SimpleNamespace(headers={"Authorization": f"Bearer {auth_token}"})
    assert auth_middleware.get_current_user(request) == "user-456"
    assert auth_middleware.get_user_from_token(auth_token)["google_id"] == "google-456"
    assert auth_middleware.get_user_from_token(setup_token) is None

    with pytest.raises(Exception):
        auth_middleware.get_current_user(SimpleNamespace(headers={"Authorization": f"Bearer {setup_token}"}))


def test_jwt_config_enforces_strict_mode_in_cloud_run(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("K_SERVICE", "auth-service")

    assert jwt_config.should_fail_closed_on_weak_jwt_secret() is True
    with pytest.raises(SystemExit):
        jwt_config.handle_invalid_jwt_secret("weak secret")


def test_jwt_config_warns_in_local_development(monkeypatch, capsys):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("K_SERVICE", raising=False)

    jwt_config.handle_invalid_jwt_secret("weak secret")
    output = capsys.readouterr().out

    assert "WARNING: Running in development mode" in output
    assert "REFUSING TO START" not in output
