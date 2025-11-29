"""
JWT token utilities for authentication
"""
import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 1440 # 24 hours


def create_jwt_token(user_data: Dict) -> str:
    """
    Create a JWT token for authenticated user
    
    Args:
        user_data: Dictionary containing user_id, email, name, google_id
        
    Returns:
        JWT token string
    """
    payload = {
        "sub": user_data["user_id"],
        "email": user_data.get("email", ""),
        "name": user_data.get("name", ""),
        "google_id": user_data.get("google_id", ""),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
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
    payload = {
        "google_id": google_user["id"],
        "email": google_user.get("email", ""),
        "name": google_user.get("name", ""),
        "picture": google_user.get("picture", ""),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=30)  # 30 min expiration for setup
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[Dict]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_setup_token(token: str) -> Optional[Dict]:
    """
    Verify setup token and return Google user info
    
    Args:
        token: Setup token string
        
    Returns:
        Google user info if valid, None otherwise
    """
    return verify_token(token)

