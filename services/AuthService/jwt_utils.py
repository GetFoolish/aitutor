"""JWT token utilities for authentication."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt

from shared.jwt_config import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_AUTH_TOKEN_USE,
    JWT_ISSUER,
    JWT_SECRET,
    JWT_SETUP_AUDIENCE,
    JWT_SETUP_TOKEN_USE,
)

JWT_EXPIRATION_MINUTES = 1440  # 24 hours
AUTH_TOKEN_USE = JWT_AUTH_TOKEN_USE
SETUP_TOKEN_USE = JWT_SETUP_TOKEN_USE


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_jwt_token(user_data: Dict) -> str:
    """
    Create a JWT token for authenticated user
    
    Args:
        user_data: Dictionary containing user_id, email, name, google_id
        
    Returns:
        JWT token string
    """
    issued_at = _utc_now()
    payload = {
        "sub": user_data["user_id"],
        "email": user_data.get("email", ""),
        "name": user_data.get("name", ""),
        "google_id": user_data.get("google_id", ""),
        "aud": JWT_AUDIENCE,
        "iss": JWT_ISSUER,
        "token_use": JWT_AUTH_TOKEN_USE,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=JWT_EXPIRATION_MINUTES),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def create_setup_token(google_user: Dict) -> str:
    """
    Create a temporary token for completing user setup
    
    Args:
        google_user: Google user information from OAuth
        
    Returns:
        Setup token string
    """
    issued_at = _utc_now()
    payload = {
        "sub": google_user["id"],
        "google_id": google_user["id"],
        "email": google_user.get("email", ""),
        "name": google_user.get("name", ""),
        "picture": google_user.get("picture", ""),
        "aud": JWT_SETUP_AUDIENCE,
        "iss": JWT_ISSUER,
        "token_use": JWT_SETUP_TOKEN_USE,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=30),  # 30 min expiration for setup
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def _verify_token_for_use(token: str, audience: str, expected_use: str) -> Optional[Dict]:
    """Verify a JWT for a specific audience and token use."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=audience,
            issuer=JWT_ISSUER,
            options={"require": ["aud", "iss", "iat", "exp", "token_use"]},
        )
        if payload.get("token_use") != expected_use:
            return None
        if expected_use == JWT_AUTH_TOKEN_USE and not payload.get("sub"):
            return None
        if expected_use == JWT_SETUP_TOKEN_USE and not all(
            payload.get(key) for key in ("sub", "google_id", "email", "name")
        ):
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    return _verify_token_for_use(token, JWT_AUDIENCE, JWT_AUTH_TOKEN_USE)


def verify_setup_token(token: str) -> Optional[Dict]:
    """
    Verify setup token and return Google user info
    
    Args:
        token: Setup token string
        
    Returns:
        Google user info if valid, None otherwise
    """
    return _verify_token_for_use(token, JWT_SETUP_AUDIENCE, JWT_SETUP_TOKEN_USE)
