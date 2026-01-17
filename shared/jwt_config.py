"""
Shared JWT configuration with security validation
"""
import os
import sys
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

JWT_ALGORITHM = "HS256"
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "teachr-api")
JWT_ISSUER = os.getenv("JWT_ISSUER", "teachr-auth-service")

# Minimum security requirements for JWT secret
MIN_SECRET_LENGTH = 32
WEAK_SECRETS = {
    "change-me-in-production",
    "secret",
    "jwt-secret",
    "your-secret-key",
    "default-secret",
    "test-secret",
}


def validate_jwt_secret(secret: str) -> tuple[bool, str]:
    """
    Validate JWT secret meets security requirements.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not secret:
        return False, "JWT_SECRET environment variable is not set"
    
    if secret in WEAK_SECRETS:
        return False, f"JWT_SECRET is using a known weak/default value: '{secret}'"
    
    if len(secret) < MIN_SECRET_LENGTH:
        return False, f"JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters long (current: {len(secret)})"
    
    # Check for complexity: should have letters, numbers, and special characters
    has_letter = bool(re.search(r'[a-zA-Z]', secret))
    has_digit = bool(re.search(r'\d', secret))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:,.<>?]', secret))
    
    if not (has_letter and has_digit):
        return False, "JWT_SECRET should contain both letters and numbers for better security"
    
    return True, ""


# Get JWT secret from environment and strip whitespace/newlines
_jwt_secret_raw = os.getenv("JWT_SECRET", "").strip()

# Validate the secret
is_valid, error_msg = validate_jwt_secret(_jwt_secret_raw)

if not is_valid:
    print(f"\n{'='*80}")
    print("🔒 JWT SECURITY ERROR")
    print(f"{'='*80}")
    print(f"\n❌ {error_msg}\n")
    print("To fix this issue:")
    print("1. Generate a strong JWT secret:")
    print("   python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    print("\n2. Set it in your environment:")
    print("   export JWT_SECRET='your-generated-secret-here'")
    print("\n3. Or add it to your .env file:")
    print("   JWT_SECRET=your-generated-secret-here")
    print(f"\n{'='*80}\n")
    
    # In production, refuse to start
    if os.getenv("ENVIRONMENT", "development") == "production":
        print("⛔ REFUSING TO START IN PRODUCTION WITH WEAK JWT SECRET")
        sys.exit(1)
    else:
        print("⚠️  WARNING: Running in development mode with weak JWT secret")
        print("⚠️  This is INSECURE and should NEVER be used in production!\n")

# Strip any whitespace/newlines to prevent signature verification failures
JWT_SECRET = _jwt_secret_raw.strip()

