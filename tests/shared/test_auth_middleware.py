from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from services.AuthService.jwt_utils import create_jwt_token, create_setup_token
from shared import auth_middleware


def test_get_current_user_returns_auth_subject():
    token = create_jwt_token(
        {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-user",
        }
    )

    request = SimpleNamespace(headers={"Authorization": f"Bearer {token}"})

    assert auth_middleware.get_current_user(request) == "user-123"


def test_get_current_user_rejects_setup_tokens():
    token = create_setup_token(
        {
            "id": "google-user",
            "email": "student@example.com",
            "name": "Student",
        }
    )

    request = SimpleNamespace(headers={"Authorization": f"Bearer {token}"})

    with pytest.raises(HTTPException) as exc_info:
        auth_middleware.get_current_user(request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail.startswith("Invalid token:")


def test_get_current_user_requires_bearer_header():
    request = SimpleNamespace(headers={})

    with pytest.raises(HTTPException) as exc_info:
        auth_middleware.get_current_user(request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid authorization header"


def test_get_user_from_token_returns_none_for_setup_tokens():
    token = create_setup_token(
        {
            "id": "google-user",
            "email": "student@example.com",
            "name": "Student",
        }
    )

    assert auth_middleware.get_user_from_token(token) is None
