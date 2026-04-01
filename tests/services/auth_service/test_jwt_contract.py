from types import SimpleNamespace

from fastapi.testclient import TestClient

import managers.mongodb_manager as mongodb_manager
import services.AuthService.auth_api as auth_api
import services.AuthService.jwt_utils as jwt_utils


def test_verify_setup_token_rejects_normal_auth_jwt():
    auth_token = jwt_utils.create_jwt_token(
        {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-123",
        }
    )

    assert jwt_utils.verify_setup_token(auth_token) is None


def test_verify_token_rejects_setup_token():
    setup_token = jwt_utils.create_setup_token(
        {
            "id": "google-123",
            "email": "student@example.com",
            "name": "Student",
        }
    )

    assert jwt_utils.verify_token(setup_token) is None


def test_complete_setup_accepts_setup_token(monkeypatch):
    created_users = []

    def fake_create_google_user(**kwargs):
        created_users.append(kwargs)
        return SimpleNamespace(user_id="user-123", age=12, current_grade="GRADE_7")

    monkeypatch.setattr(auth_api.user_manager, "create_google_user", fake_create_google_user)
    monkeypatch.setattr(auth_api, "create_jwt_token", lambda payload: "jwt-123")
    monkeypatch.setattr(
        mongodb_manager,
        "mongo_db",
        SimpleNamespace(users=SimpleNamespace(find_one=lambda query: {"user_type": "student"})),
    )

    setup_token = jwt_utils.create_setup_token(
        {
            "id": "google-123",
            "email": "student@example.com",
            "name": "Student",
            "picture": "https://example.com/p.png",
        }
    )

    with TestClient(auth_api.app) as client:
        response = client.post(
            "/auth/complete-setup",
            json={"setup_token": setup_token, "user_type": "student", "age": 12},
        )

    assert response.status_code == 200
    assert response.json()["token"] == "jwt-123"
    assert response.json()["is_new_user"] is True
    assert created_users == [
        {
            "google_id": "google-123",
            "email": "student@example.com",
            "name": "Student",
            "age": 12,
            "picture": "https://example.com/p.png",
            "user_type": "student",
        }
    ]


def test_complete_setup_rejects_auth_token(monkeypatch):
    def fail_create_google_user(**kwargs):
        raise AssertionError("normal auth JWTs must never reach user creation")

    monkeypatch.setattr(auth_api.user_manager, "create_google_user", fail_create_google_user)

    auth_token = jwt_utils.create_jwt_token(
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
            json={"setup_token": auth_token, "user_type": "student", "age": 12},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired setup token"
