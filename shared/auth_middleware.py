"""
Shared JWT authentication middleware for FastAPI services
"""
from typing import Dict, Optional

import jwt
from fastapi import HTTPException, Request

from shared.jwt_config import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_AUTH_TOKEN_USE,
    JWT_ISSUER,
    JWT_SECRET,
)


def _decode_auth_token(token: str) -> Dict:
    """Decode backend auth tokens using the shared auth contract."""
    payload = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["sub", "aud", "iss", "iat", "exp", "token_use"]},
    )

    if payload.get("token_use") != JWT_AUTH_TOKEN_USE:
        raise jwt.InvalidTokenError("unexpected token_use")

    return payload


def get_current_user(request: Request) -> str:
    """
    Extract and validate JWT token from request, return user_id

    Args:
        request: FastAPI request object

    Returns:
        user_id string

    Raises:
        HTTPException: If token is missing or invalid
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid authorization header"
        )

    token = auth_header.split(" ")[1]

    try:
        payload = _decode_auth_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_jwt_payload(request: Request) -> Dict:
    """
    Extract full JWT payload from request. Returns dict with all claims.
    Raises HTTPException if token is missing/invalid.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def require_admin(request: Request) -> str:
    """
    Verify the request comes from an admin user.
    Checks user_type in MongoDB. Returns user_id or raises 403.
    """
    user_id = get_current_user(request)
    try:
        from managers.mongodb_manager import mongo_db
        user_data = mongo_db.users.find_one({"user_id": user_id})
        if not user_data or user_data.get("user_type") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


def get_user_from_token(token: str) -> Optional[Dict]:
    """
    Extract user information from JWT token (for WebSocket connections)
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with user info or None if invalid
    """
    try:
        payload = _decode_auth_token(token)
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
            "google_id": payload.get("google_id", "")
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
