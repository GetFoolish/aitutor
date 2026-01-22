"""
Shared CORS configuration for FastAPI services
"""
import os
from typing import List

# Get allowed origins from environment or use safe defaults
def get_allowed_origins() -> List[str]:
    """
    Get allowed CORS origins from environment variable or use safe defaults.
    
    Returns:
        List of allowed origin URLs
    """
    # Check if ALLOWED_ORIGINS is set in environment
    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    
    if env_origins:
        # Split by comma and strip whitespace
        origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
        print(f"INFO: Using CORS origins from environment: {origins}")
        return origins
    
    # Default safe origins for development
    default_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://localhost:4173",
        "http://localhost:5173",
        "http://localhost:8080",  # For serving test HTML files
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://127.0.0.1:3005",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",  # For serving test HTML files
        "null",  # For file:// protocol (dev only)
    ]
    
    # Add production domain if set
    production_domain = os.getenv("PRODUCTION_DOMAIN")
    if production_domain:
        default_origins.append(f"https://{production_domain}")
        default_origins.append(f"https://www.{production_domain}")
    
    print(f"WARNING: Using default CORS origins (development): {default_origins}")
    print("WARNING: Set ALLOWED_ORIGINS environment variable for production")
    
    return default_origins


# CORS configuration
ALLOWED_ORIGINS = get_allowed_origins()
ALLOW_CREDENTIALS = True  # Allow cookies/auth headers
ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
ALLOWED_HEADERS = ["*"]  # Allow all headers for flexibility
