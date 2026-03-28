"""Shared JWT configuration with security validation."""

import os
import re
import secrets
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

JWT_ALGORITHM = "HS256"
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "teachr-api")
JWT_SETUP_AUDIENCE = os.getenv("JWT_SETUP_AUDIENCE", "teachr-setup")
JWT_ISSUER = os.getenv("JWT_ISSUER", "teachr-auth-service")
JWT_AUTH_TOKEN_USE = "auth"
JWT_SETUP_TOKEN_USE = "setup"

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


def is_cloud_run_runtime() -> bool:
    """Return True when running in a deployed Cloud Run service."""
    return bool(os.getenv("K_SERVICE"))


def should_fail_closed_on_weak_jwt_secret() -> bool:
    """Return True when weak JWT secrets must abort startup.

    Fails closed by default: any ENVIRONMENT value other than an explicit
    dev/test marker is treated as production. This prevents silent ephemeral
    secrets on staging servers that use non-standard env names like 'prod',
    'live', or 'staging2'.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    explicitly_dev = environment in {"development", "dev", "test", "local", "ci"}
    return (not explicitly_dev) or is_cloud_run_runtime()


def should_abort_on_weak_jwt_secret() -> bool:
    """Return True when invalid JWT secrets should terminate module startup."""
    return should_fail_closed_on_weak_jwt_secret()


def handle_invalid_jwt_secret(error_message: str) -> None:
    """Print remediation guidance and abort when the runtime must fail closed."""
    print(f"\n{'='*80}")
    print("🔒 JWT SECURITY ERROR")
    print(f"{'='*80}")
    print(f"\n❌ {error_message}\n")
    print("To fix this issue:")
    print("1. Generate a strong JWT secret:")
    print('   python -c "import secrets; print(secrets.token_urlsafe(32))"')
    print("\n2. Set it in your environment:")
    print("   export JWT_SECRET='your-generated-secret-here'")
    print("\n3. Or add it to your .env file:")
    print("   JWT_SECRET=your-generated-secret-here")
    print(f"\n{'='*80}\n")

    if should_abort_on_weak_jwt_secret():
        print("⛔ REFUSING TO START WITH WEAK JWT SECRET IN DEPLOYED/PRODUCTION MODE")
        sys.exit(1)

    print("⚠️  WARNING: Running in development mode with weak JWT secret")
    print("⚠️  This is INSECURE and should NEVER be used in production!\n")


# Get JWT secret from environment
_jwt_secret_raw = os.getenv("JWT_SECRET", "")

# Validate the secret
is_valid, error_msg = validate_jwt_secret(_jwt_secret_raw)

if not is_valid:
    handle_invalid_jwt_secret(error_msg)

# In dev/test with a weak/missing secret, use an ephemeral strong secret rather than
# signing tokens with an empty string (which PyJWT accepts for both sign and verify,
# making every token trivially forgeable).
if is_valid:
    JWT_SECRET = _jwt_secret_raw
else:
    JWT_SECRET = secrets.token_urlsafe(32)
