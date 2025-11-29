"""
Shared JWT authentication middleware for FastAPI services
"""
import jwt
from fastapi import Request, HTTPException
from typing import Optional, Dict
from shared.jwt_config import JWT_SECRET, JWT_ALGORITHM


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
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_user_from_token(token: str) -> Optional[Dict]:
    """
    Extract user information from JWT token (for WebSocket connections)
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with user info or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
            "google_id": payload.get("google_id", "")
        }
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

