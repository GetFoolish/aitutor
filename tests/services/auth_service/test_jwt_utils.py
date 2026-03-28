from datetime import datetime, timedelta, timezone

import jwt

from services.AuthService import jwt_utils


def test_verify_setup_token_round_trip():
    token = jwt_utils.create_setup_token(
        {
            "id": "google-user",
            "email": "student@example.com",
            "name": "Student",
            "picture": "https://example.com/avatar.png",
        }
    )

    payload = jwt_utils.verify_setup_token(token)

    assert payload is not None
    assert payload["google_id"] == "google-user"
    assert payload["email"] == "student@example.com"
    assert payload["token_use"] == jwt_utils.SETUP_TOKEN_USE


def test_verify_setup_token_rejects_auth_tokens():
    token = jwt_utils.create_jwt_token(
        {
            "user_id": "user-123",
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-user",
        }
    )

    assert jwt_utils.verify_setup_token(token) is None


def test_verify_token_rejects_setup_tokens():
    token = jwt_utils.create_setup_token(
        {
            "id": "google-user",
            "email": "student@example.com",
            "name": "Student",
        }
    )

    assert jwt_utils.verify_token(token) is None


def test_verify_setup_token_rejects_wrong_audience():
    issued_at = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "google-user",
            "google_id": "google-user",
            "email": "student@example.com",
            "name": "Student",
            "aud": jwt_utils.JWT_AUDIENCE,
            "iss": jwt_utils.JWT_ISSUER,
            "token_use": jwt_utils.SETUP_TOKEN_USE,
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=30),
        },
        jwt_utils.JWT_SECRET,
        algorithm=jwt_utils.JWT_ALGORITHM,
    )

    assert jwt_utils.verify_setup_token(token) is None


def test_verify_setup_token_rejects_missing_required_claims():
    issued_at = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "google-user",
            "google_id": "google-user",
            "email": "student@example.com",
            "aud": jwt_utils.JWT_SETUP_AUDIENCE,
            "iss": jwt_utils.JWT_ISSUER,
            "token_use": jwt_utils.SETUP_TOKEN_USE,
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=30),
        },
        jwt_utils.JWT_SECRET,
        algorithm=jwt_utils.JWT_ALGORITHM,
    )

    assert jwt_utils.verify_setup_token(token) is None


def test_verify_token_rejects_missing_subject():
    issued_at = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "email": "student@example.com",
            "name": "Student",
            "google_id": "google-user",
            "aud": jwt_utils.JWT_AUDIENCE,
            "iss": jwt_utils.JWT_ISSUER,
            "token_use": jwt_utils.AUTH_TOKEN_USE,
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=30),
        },
        jwt_utils.JWT_SECRET,
        algorithm=jwt_utils.JWT_ALGORITHM,
    )

    assert jwt_utils.verify_token(token) is None
