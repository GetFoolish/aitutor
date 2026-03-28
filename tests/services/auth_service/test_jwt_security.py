from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

import managers.mongodb_manager as mongodb_manager
import services.AuthService.auth_api as auth_api
from services.AuthService.jwt_utils import create_jwt_token, create_setup_token, verify_setup_token, verify_token
from shared.auth_middleware import get_current_user, get_user_from_token


def make_request(token: str | None = None) -> Request:
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
        }
    )


def test_setup_token_and_auth_token_are_separated():
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
            "picture": "https://example.com/picture.png",
        }
    )

    auth_payload = verify_token(auth_token)
    setup_payload = verify_setup_token(setup_token)

    assert auth_payload is not None
    assert auth_payload["sub"] == "user-123"
    assert auth_payload["token_use"] == "auth"

    assert setup_payload is not None
    assert setup_payload["sub"] == "google-123"
    assert setup_payload["google_id"] == "google-123"
    assert setup_payload["token_use"] == "setup"

    assert verify_setup_token(auth_token) is None
    assert verify_token(setup_token) is None


def test_auth_middleware_accepts_only_auth_tokens():
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
        }
    )

    assert get_current_user(make_request(auth_token)) == "user-123"
    assert get_user_from_token(auth_token) == {
        "user_id": "user-123",
        "email": "student@example.com",
        "name": "Student",
        "google_id": "google-123",
    }
    assert get_user_from_token(setup_token) is None

    with pytest.raises(HTTPException) as exc:
        get_current_user(make_request(setup_token))

    assert exc.value.status_code == 401
    assert "Invalid token" in exc.value.detail


def test_complete_setup_accepts_setup_token(monkeypatch):
    setup_token = create_setup_token(
        {
            "id": "google-123",
            "email": "student@example.com",
            "name": "Student",
            "picture": "https://example.com/picture.png",
        }
    )

    monkeypatch.setattr(
        auth_api.user_manager,
        "create_google_user",
        lambda **kwargs: SimpleNamespace(
            user_id="user-123",
            age=10,
            current_grade="GRADE_5",
        ),
    )
    monkeypatch.setattr(auth_api, "create_jwt_token", lambda payload: "jwt-123")
    monkeypatch.setattr(
        mongodb_manager,
        "mongo_db",
        SimpleNamespace(users=SimpleNamespace(find_one=lambda query: {"user_id": "user-123"})),
    )

    with TestClient(auth_api.app) as client:
        response = client.post(
            "/auth/complete-setup",
            json={
                "setup_token": setup_token,
                "user_type": "student",
                "age": 10,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "token": "jwt-123",
        "user": {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "age": 10,
            "current_grade": "GRADE_5",
            "user_type": "student",
        },
        "is_new_user": True,
    }


def test_complete_setup_rejects_normal_auth_token():
    auth_token = create_jwt_token(
        {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-123",
        }
    )

    with TestClient(auth_api.app) as client:
        response = client.post(
            "/auth/complete-setup",
            json={
                "setup_token": auth_token,
                "user_type": "student",
                "age": 10,
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired setup token"
