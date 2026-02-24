"""
Auth Service - Google OAuth authentication API
"""
import os
import sys
import logging
import secrets
import threading
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import date, datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.AuthService.oauth_handler import GoogleOAuthHandler
from services.AuthService.jwt_utils import create_jwt_token, create_setup_token, verify_setup_token, verify_token
from services.AuthService.password_utils import hash_password, verify_password, validate_password_strength
from managers.user_manager import UserManager
from managers.user_manager import calculate_grade_from_age
from shared.auth_middleware import get_current_user
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.cache_middleware import CacheControlMiddleware

from shared.logging_config import get_logger

logger = get_logger(__name__)


# ── In-memory rate limiter (Bug #68) ──────────────────────────────
import time as _time
from collections import defaultdict as _defaultdict

class _RateLimiter:
    """Simple sliding-window rate limiter keyed by IP."""
    _MAX_KEYS = 10_000  # prevent unbounded growth from unique IPs

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = _defaultdict(list)

    def check(self, key: str) -> bool:
        now = _time.time()
        cutoff = now - self.window_seconds
        bucket = self._hits[key]
        self._hits[key] = bucket = [t for t in bucket if t > cutoff]
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        # Periodic eviction: if dict is too large, prune all expired entries
        if len(self._hits) > self._MAX_KEYS:
            stale = [k for k, v in self._hits.items() if not v or v[-1] < cutoff]
            for k in stale:
                del self._hits[k]
        return True

_login_limiter = _RateLimiter(max_requests=10, window_seconds=60)
_signup_limiter = _RateLimiter(max_requests=5, window_seconds=300)
_dev_login_limiter = _RateLimiter(max_requests=20, window_seconds=60)


AUTH_EXCHANGE_CODE_TTL_SECONDS = int(os.getenv("AUTH_EXCHANGE_CODE_TTL_SECONDS", "300"))
_auth_exchange_codes: Dict[str, Dict[str, Any]] = {}
_auth_exchange_lock = threading.Lock()
OAUTH_STATE_TTL_SECONDS = int(os.getenv("OAUTH_STATE_TTL_SECONDS", "600"))
_oauth_state_frontend_urls: Dict[str, Dict[str, Any]] = {}
_oauth_state_lock = threading.Lock()


def _prune_auth_exchange_codes(now: Optional[float] = None) -> None:
    ts = now if now is not None else _time.time()
    expired_codes = [code for code, entry in _auth_exchange_codes.items() if entry["expires_at"] <= ts]
    for code in expired_codes:
        _auth_exchange_codes.pop(code, None)


def _issue_auth_exchange_code(payload: Dict[str, Any]) -> str:
    code = secrets.token_urlsafe(32)
    now = _time.time()
    with _auth_exchange_lock:
        _prune_auth_exchange_codes(now)
        _auth_exchange_codes[code] = {
            "payload": payload,
            "expires_at": now + AUTH_EXCHANGE_CODE_TTL_SECONDS,
        }
    return code


def _consume_auth_exchange_code(code: str) -> Optional[Dict[str, Any]]:
    now = _time.time()
    with _auth_exchange_lock:
        _prune_auth_exchange_codes(now)
        entry = _auth_exchange_codes.pop(code, None)
    if not entry:
        return None
    if entry.get("expires_at", 0) <= now:
        return None
    return entry.get("payload")


def _normalize_origin(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _prune_oauth_state_frontend_urls(now: Optional[float] = None) -> None:
    ts = now if now is not None else _time.time()
    expired_states = [
        state for state, entry in _oauth_state_frontend_urls.items()
        if entry["expires_at"] <= ts
    ]
    for state in expired_states:
        _oauth_state_frontend_urls.pop(state, None)


def _remember_oauth_state_frontend_url(state: str, frontend_url: str) -> None:
    now = _time.time()
    with _oauth_state_lock:
        _prune_oauth_state_frontend_urls(now)
        _oauth_state_frontend_urls[state] = {
            "frontend_url": frontend_url,
            "expires_at": now + OAUTH_STATE_TTL_SECONDS,
        }


def _consume_oauth_state_frontend_url(state: str) -> Optional[str]:
    now = _time.time()
    with _oauth_state_lock:
        _prune_oauth_state_frontend_urls(now)
        entry = _oauth_state_frontend_urls.pop(state, None)
    if not entry or entry.get("expires_at", 0) <= now:
        return None
    return entry.get("frontend_url")


def _extract_frontend_origin(request: Request) -> Optional[str]:
    for header_name in ("origin", "referer"):
        normalized = _normalize_origin(request.headers.get(header_name))
        if normalized and normalized in ALLOWED_ORIGINS:
            return normalized
    return None


def _resolve_frontend_redirect_url(state: Optional[str]) -> str:
    configured_frontend_url = _normalize_origin(os.getenv("FRONTEND_URL"))
    if configured_frontend_url:
        return configured_frontend_url

    if state:
        remembered_frontend_url = _consume_oauth_state_frontend_url(state)
        if remembered_frontend_url:
            return remembered_frontend_url

    # Vite dev server default in this repository.
    return "http://localhost:5173"


def _client_ip(request: Request) -> str:
    """Best-effort client IP extraction (handles proxies)."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real = request.headers.get("X-Real-IP", "")
    if real:
        return real
    return request.client.host if request.client else "unknown"
# ──────────────────────────────────────────────────────────────────


# Configure logging (logger already initialized via get_logger above)
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = FastAPI(title="Auth Service")

# Add timing middleware for performance monitoring (Phase 1)
app.add_middleware(UnpluggedTimingMiddleware)

# Cache Control (Phase 7)
app.add_middleware(CacheControlMiddleware)

# Configure CORS with secure origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

# Get base URL from environment
BASE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8003")
REDIRECT_URI = f"{BASE_URL}/auth/callback"

# Initialize OAuth handler
oauth_handler = GoogleOAuthHandler(REDIRECT_URI)

# Initialize UserManager
user_manager = UserManager()


class EmailSignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    date_of_birth: date
    gender: str
    preferred_language: str
    location: Optional[str] = None
    user_type: str = "student"

class EmailLoginRequest(BaseModel):
    email: EmailStr
    password: str

class CompleteSetupRequest(BaseModel):
    setup_token: str
    user_type: str  # "student" or "parent" (but always stored as "student")
    date_of_birth: date  # Changed from age
    gender: str
    preferred_language: str
    location: Optional[str] = None
    subjects: Optional[List[str]] = []
    learning_goals: Optional[List[str]] = []
    interests: Optional[List[str]] = []
    learning_style: Optional[str] = None

class AuthCodeExchangeRequest(BaseModel):
    code: str

class UpdateAccountRequest(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    location: Optional[str] = None
    gender: Optional[str] = None
    preferred_language: Optional[str] = None

class UpdateMissingInfoRequest(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    preferred_language: Optional[str] = None
    location: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AuthService"}


@app.get("/auth/google")
async def google_login(request: Request):
    """Initiate Google OAuth flow"""
    try:
        authorization_url, state = oauth_handler.get_authorization_url()
        frontend_origin = _extract_frontend_origin(request)
        if frontend_origin:
            _remember_oauth_state_frontend_url(state, frontend_origin)
        return {
            "authorization_url": authorization_url,
            "state": state
        }
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth: {str(e)}")


@app.get("/auth/callback")
async def google_callback(code: Optional[str] = Query(None), state: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """Handle Google OAuth callback"""
    if error:
        logger.error(f"OAuth error: {error}")
        return JSONResponse(
            status_code=400,
            content={"error": "OAuth authentication failed", "details": error}
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    try:
        # Get user info from Google
        google_user = await oauth_handler.get_user_info(code, state or "")
        
        if not google_user:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
        # Check if user already exists
        existing_user = user_manager.get_user_by_google_id(google_user["id"])
        
        if existing_user:
            # Existing user - update last login and issue JWT
            user_manager.update_last_login(existing_user.user_id)
            
            # Get full user data from MongoDB
            from managers.mongodb_manager import mongo_db
            user_data = mongo_db.users.find_one({"user_id": existing_user.user_id})
            
            jwt_token = create_jwt_token({
                "user_id": existing_user.user_id,
                "email": user_data.get("google_email", "") if user_data else google_user.get("email", ""),
                "name": user_data.get("google_name", "") if user_data else google_user.get("name", ""),
                "google_id": google_user["id"]
            })
            
            # Redirect with one-time auth code (never send JWT in URL)
            auth_code = _issue_auth_exchange_code({
                "token": jwt_token,
                "is_new_user": False
            })
            frontend_url = _resolve_frontend_redirect_url(state)
            return RedirectResponse(
                url=f"{frontend_url}/app/login?auth_code={auth_code}"
            )
        else:
            # New user - need to complete setup
            setup_token = create_setup_token(google_user)
            
            # Redirect with one-time auth code (never send setup token in URL)
            auth_code = _issue_auth_exchange_code({
                "setup_token": setup_token,
                "requires_setup": True,
                "is_new_user": True
            })
            frontend_url = _resolve_frontend_redirect_url(state)
            return RedirectResponse(
                url=f"{frontend_url}/app/login?auth_code={auth_code}"
            )
            
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@app.post("/auth/exchange-code")
async def exchange_auth_code(request: AuthCodeExchangeRequest):
    """Exchange one-time OAuth redirect code for auth payload."""
    payload = _consume_auth_exchange_code(request.code)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired auth code")
    return payload


@app.post("/auth/complete-setup")
async def complete_setup(request: CompleteSetupRequest):
    """Complete user setup with date_of_birth, gender, language and user_type"""
    try:
        # Verify setup token
        google_user_data = verify_setup_token(request.setup_token)

        if not google_user_data:
            raise HTTPException(status_code=400, detail="Invalid or expired setup token")

        # Calculate age from date_of_birth
        today = datetime.now().date()
        age = today.year - request.date_of_birth.year - ((today.month, today.day) < (request.date_of_birth.month, request.date_of_birth.day))

        # Validate age
        if age < 5 or age > 18:
            raise HTTPException(status_code=400, detail="Age must be between 5 and 18")

        # Validate user_type (but always store as "student" for now)
        if request.user_type not in ["student", "parent"]:
            raise HTTPException(status_code=400, detail="user_type must be 'student' or 'parent'")

        # Validate gender
        if request.gender not in ["Male", "Female", "Other", "Prefer not to say"]:
            raise HTTPException(status_code=400, detail="Invalid gender value")

        # Validate language
        if request.preferred_language not in ["English", "Hindi", "Spanish", "French"]:
            raise HTTPException(status_code=400, detail="Invalid language value")

        # Create user (always store as "student" regardless of frontend selection)
        user_profile = user_manager.create_google_user(
            google_id=google_user_data["google_id"],
            email=google_user_data["email"],
            name=google_user_data["name"],
            age=age,
            picture=google_user_data.get("picture", ""),
            user_type="student",  # Always "student" for now
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            preferred_language=request.preferred_language,
            location=request.location,
            subjects=request.subjects,
            learning_goals=request.learning_goals,
            interests=request.interests,
            learning_style=request.learning_style
        )
        
        # Create JWT token
        jwt_token = create_jwt_token({
            "user_id": user_profile.user_id,
            "email": google_user_data["email"],
            "name": google_user_data["name"],
            "google_id": google_user_data["google_id"]
        })
        
        # Get full user data for response
        from managers.mongodb_manager import mongo_db
        user_data = mongo_db.users.find_one({"user_id": user_profile.user_id})
        
        return {
            "token": jwt_token,
            "user": {
                "user_id": user_profile.user_id,
                "email": google_user_data["email"],
                "name": google_user_data["name"],
                "age": user_profile.age,
                "current_grade": user_profile.current_grade,
                "user_type": "student",
                "preferred_language": request.preferred_language
            },
            "is_new_user": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing setup: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@app.post("/auth/signup")
async def email_signup(http_req: Request, request: EmailSignupRequest):
    """Register a new user with email and password"""
    # Rate limit by IP (Bug #68)
    if not _signup_limiter.check(_client_ip(http_req)):
        raise HTTPException(status_code=429, detail="Too many signup attempts. Please try again later.")
    try:
        # Validate password strength
        is_valid, error_message = validate_password_strength(request.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        # Calculate age from date_of_birth
        today = datetime.now().date()
        age = today.year - request.date_of_birth.year - ((today.month, today.day) < (request.date_of_birth.month, request.date_of_birth.day))

        # Validate age
        if age < 5 or age > 18:
            raise HTTPException(status_code=400, detail="Age must be between 5 and 18")

        # Validate gender
        if request.gender not in ["Male", "Female", "Other", "Prefer not to say"]:
            raise HTTPException(status_code=400, detail="Invalid gender value")

        # Validate language
        if request.preferred_language not in ["English", "Hindi", "Spanish", "French"]:
            raise HTTPException(status_code=400, detail="Invalid language value")

        # Check if email already exists
        from managers.mongodb_manager import mongo_db
        existing_user = mongo_db.users.find_one({"email": request.email.lower()})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password
        password_hash = hash_password(request.password)

        # Create user
        user_profile = user_manager.create_email_user(
            email=request.email.lower(),
            password_hash=password_hash,
            name=request.name,
            age=age,
            date_of_birth=request.date_of_birth,
            gender=request.gender,
            preferred_language=request.preferred_language,
            location=request.location,
            user_type=request.user_type
        )

        # Create JWT token
        jwt_token = create_jwt_token({
            "user_id": user_profile.user_id,
            "email": request.email.lower(),
            "name": request.name
        })

        logger.info(f"New email signup: {request.email} -> {user_profile.user_id}")

        return {
            "token": jwt_token,
            "user": {
                "user_id": user_profile.user_id,
                "email": request.email.lower(),
                "name": request.name,
                "age": age,
                "current_grade": user_profile.current_grade,
                "user_type": request.user_type,
                "preferred_language": request.preferred_language
            },
            "is_new_user": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in email signup: {e}")
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@app.post("/auth/login")
async def email_login(http_req: Request, request: EmailLoginRequest):
    """Login with email and password"""
    # Rate limit by IP (Bug #68)
    if not _login_limiter.check(_client_ip(http_req)):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again in a minute.")
    try:
        # Get user by email
        from managers.mongodb_manager import mongo_db
        user_data = mongo_db.users.find_one({"email": request.email.lower()})

        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Check if user has password (email auth user)
        if "password_hash" not in user_data:
            raise HTTPException(status_code=400, detail="This account uses Google sign-in. Please use 'Continue with Google'")

        # Verify password
        if not verify_password(request.password, user_data["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Update last login
        user_manager.update_last_login(user_data["user_id"])

        # Create JWT token
        jwt_token = create_jwt_token({
            "user_id": user_data["user_id"],
            "email": user_data.get("email", ""),
            "name": user_data.get("name", "")
        })

        logger.info(f"Email login: {request.email} -> {user_data['user_id']}")

        return {
            "token": jwt_token,
            "user": {
                "user_id": user_data["user_id"],
                "email": user_data.get("email", ""),
                "name": user_data.get("name", ""),
                "age": user_data.get("age", 5),
                "current_grade": user_data.get("current_grade", "K"),
                "user_type": user_data.get("user_type", "student"),
                "preferred_language": user_data.get("preferred_language", "English")
            },
            "is_new_user": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in email login: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.get("/auth/me")
async def get_current_user_info(request: Request):
    """Get current user info from JWT token"""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get user from database
    user_profile = user_manager.load_user(payload["sub"])
    
    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get full user data from MongoDB
    from managers.mongodb_manager import mongo_db
    user_data = mongo_db.users.find_one({"user_id": user_profile.user_id})
    
    return {
        "user_id": user_profile.user_id,
        "email": user_data.get("google_email", "") if user_data else "",
        "name": (user_data.get("google_name") or user_data.get("name", "")) if user_data else "",
        "age": user_profile.age,
        "current_grade": user_profile.current_grade,
        "user_type": user_data.get("user_type", "student") if user_data else "student",
        "preferred_language": user_data.get("preferred_language", "English") if user_data else "English"
    }


@app.get("/account/info")
async def get_account_info(request: Request):
    """Get user account information including credits"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header.split(" ")[1]
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Get user from database
    user_profile = user_manager.load_user(payload["sub"])

    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")

    # ENTERPRISE SOLUTION: Allocate daily free minutes if needed (before fetching balance)
    # This ensures the UI always shows accurate, up-to-date balance
    from services.PaymentService.free_minutes_handler import allocate_daily_free_minutes
    try:
        allocate_daily_free_minutes(user_profile.user_id)
    except Exception as e:
        logger.warning(f"[ACCOUNT_INFO] Failed to allocate daily minutes: {e}")

    # Get full user data from MongoDB
    from managers.mongodb_manager import mongo_db
    user_data = mongo_db.users.find_one({"user_id": user_profile.user_id})
    
    # Get email and name (handle both Google OAuth and email/password)
    email = user_data.get("google_email", "") if user_data else ""
    if not email:
        email = user_data.get("email", "") if user_data else ""
    
    name = user_data.get("google_name", "") if user_data else ""
    if not name:
        name = user_data.get("name", "") if user_data else ""
    
    # Get date of birth
    date_of_birth = user_data.get("date_of_birth", "") if user_data else ""
    
    # Get location (default to empty string if not set)
    location = user_data.get("location", "") if user_data else ""
    
    # Get gender
    gender = user_data.get("gender", "") if user_data else ""
    
    # Get preferred language
    preferred_language = user_data.get("preferred_language", "") if user_data else ""
    
    # Get user type
    user_type = user_data.get("user_type", "student") if user_data else "student"
    
    # Get credits (default to 0.0 balance with USD currency if not set)
    credits = user_data.get("credits", {}) if user_data else {}
    if not credits:
        credits = {"balance": 0.0, "currency": "USD"}
    else:
        # Ensure balance and currency exist
        if "balance" not in credits:
            credits["balance"] = 0.0
        if "currency" not in credits:
            credits["currency"] = "USD"

    # Get subscription plan (default to None if not set)
    subscription_plan = user_data.get("subscription_plan") if user_data else None
    
    # Get free_minutes (for daily allocation)
    free_minutes = user_data.get("free_minutes", {}) if user_data else {}
    if not free_minutes:
        free_minutes = {"balance": 0.0, "last_reset_date": None}
    else:
        # Ensure balance exists
        if "balance" not in free_minutes:
            free_minutes["balance"] = 0.0
        if "last_reset_date" not in free_minutes:
            free_minutes["last_reset_date"] = None

    # Calculate hours and minutes until next reset (for better UX)
    next_reset_in_hours = None
    next_reset_in_minutes = None
    last_reset_date = free_minutes.get("last_reset_date")
    if last_reset_date:
        try:
            if isinstance(last_reset_date, str):
                last_reset_dt = datetime.fromisoformat(last_reset_date)
            elif isinstance(last_reset_date, datetime):
                last_reset_dt = last_reset_date
            else:
                last_reset_dt = None

            if last_reset_dt:
                # Calculate hours and minutes until next midnight (UTC)
                from datetime import timedelta
                today = datetime.now().date()
                last_reset_day = last_reset_dt.date()

                # If last reset was today, calculate hours and minutes until tomorrow midnight
                if last_reset_day == today:
                    tomorrow_midnight = datetime.combine(today + timedelta(days=1), datetime.min.time())
                    time_until_reset = tomorrow_midnight - datetime.now()
                    total_seconds = time_until_reset.total_seconds()
                    next_reset_in_hours = int(total_seconds // 3600)
                    next_reset_in_minutes = int((total_seconds % 3600) // 60)
                else:
                    # If last reset was before today, reset is available now (0 hours, 0 minutes)
                    next_reset_in_hours = 0
                    next_reset_in_minutes = 0
        except Exception as e:
            logger.warning(f"[ACCOUNT_INFO] Failed to calculate next reset time: {e}")
            next_reset_in_hours = None
            next_reset_in_minutes = None

    return {
        "user_id": user_profile.user_id,
        "email": email,
        "name": name,
        "date_of_birth": date_of_birth,
        "location": location,
        "gender": gender,
        "preferred_language": preferred_language,
        "user_type": user_type,
        "credits": credits,
        "free_minutes": {
            **free_minutes,
            "next_reset_in_hours": next_reset_in_hours,
            "next_reset_in_minutes": next_reset_in_minutes
        },
        "subscription_plan": subscription_plan
    }


@app.put("/account/update")
async def update_account_info(request: Request, update_data: UpdateAccountRequest):
    """Update user account information"""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload["sub"]
    
    # Get user from database
    user_profile = user_manager.load_user(user_id)
    
    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get full user data from MongoDB
    from managers.mongodb_manager import mongo_db
    user_data = mongo_db.users.find_one({"user_id": user_id})
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build update dictionary with only provided fields
    update_dict = {}
    
    if update_data.name is not None:
        # Always update google_name (what /auth/me reads) + name for consistency
        update_dict["google_name"] = update_data.name
        update_dict["name"] = update_data.name
    
    if update_data.date_of_birth is not None:
        update_dict["date_of_birth"] = update_data.date_of_birth.isoformat()
        # Recalculate age and current_grade
        today = datetime.now().date()
        age = today.year - update_data.date_of_birth.year - ((today.month, today.day) < (update_data.date_of_birth.month, update_data.date_of_birth.day))
        current_grade = calculate_grade_from_age(age)
        update_dict["age"] = age
        update_dict["current_grade"] = current_grade
        # Also update in UserProfile
        user_profile.age = age
        user_profile.current_grade = current_grade
    
    if update_data.location is not None:
        update_dict["location"] = update_data.location
    
    if update_data.gender is not None:
        # Validate gender
        if update_data.gender not in ["Male", "Female", "Other", "Prefer not to say"]:
            raise HTTPException(status_code=400, detail="Invalid gender value")
        update_dict["gender"] = update_data.gender
    
    if update_data.preferred_language is not None:
        # Validate language
        if update_data.preferred_language not in ["English", "Hindi", "Spanish", "French"]:
            raise HTTPException(status_code=400, detail="Invalid language value")
        update_dict["preferred_language"] = update_data.preferred_language
    
    # Update MongoDB
    if update_dict:
        mongo_db.users.update_one(
            {"user_id": user_id},
            {"$set": update_dict}
        )
        
        # Save updated UserProfile if age/grade changed
        if "age" in update_dict or "current_grade" in update_dict:
            user_manager.save_user(user_profile)
        
        logger.info(f"[ACCOUNT] Updated account info for user {user_id}: {list(update_dict.keys())}")
    
    # Return updated account info
    return await get_account_info(request)


@app.get("/auth/detect-location")
async def detect_location(request: Request):
    """Detect user's country from IP address"""
    try:
        # Get client IP from headers (handles proxies/load balancers)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.headers.get("X-Real-IP", "")
        if not client_ip:
            client_ip = request.client.host if request.client else None
        
        if not client_ip:
            return {"country": None, "error": "Could not determine IP address"}
        
        # Use ipapi.co for geolocation (free tier: 30k/month)
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                # Free tier doesn't require API key, but you can add one for higher limits
                api_key = os.getenv("IPAPI_API_KEY", "")  # Optional
                url = f"https://ipapi.co/{client_ip}/json/"
                if api_key:
                    url += f"?key={api_key}"
                
                resp = await client.get(url, timeout=5.0)
                
                if resp.status_code == 200:
                    data = resp.json()
                    country = data.get("country_name", "")
                    country_code = data.get("country_code", "")
                    
                    return {
                        "country": country,
                        "country_code": country_code,
                        "ip": client_ip
                    }
                else:
                    logger.warning(f"ipapi.co returned status {resp.status_code}")
                    return {"country": None, "error": "Geolocation service unavailable"}
                    
            except Exception as e:
                logger.error(f"Error calling ipapi.co: {e}")
                return {"country": None, "error": str(e)}
                
    except Exception as e:
        logger.error(f"Error detecting location: {e}")
        return {"country": None, "error": str(e)}


class DevLoginRequest(BaseModel):
    age: int
    name: str = "Test Student"


@app.post("/auth/dev-login")
async def dev_login(http_req: Request, request: DevLoginRequest):
    """DEV ONLY: Create a test user with a specific age and return a JWT instantly.
    Skips password, email, and onboarding. For testing different age/grade combos."""
    # Block in production — this endpoint must NEVER be available outside dev (Bug #63)
    if os.getenv("ENVIRONMENT", "development") == "production":
        raise HTTPException(status_code=404, detail="Not found")
    # Rate limit by IP (Bug #68)
    if not _dev_login_limiter.check(_client_ip(http_req)):
        raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    import uuid
    from managers.mongodb_manager import mongo_db

    age = max(5, min(18, request.age))
    current_grade = calculate_grade_from_age(age)
    user_id = f"dev_{uuid.uuid4().hex[:12]}"

    # Create minimal user doc directly
    user_doc = {
        "user_id": user_id,
        "name": request.name,
        "email": f"{user_id}@dev.local",
        "age": age,
        "current_grade": current_grade,
        "created_at": __import__("time").time(),
        "last_updated": __import__("time").time(),
        "skill_states": {},
        "question_history": [],
        "student_notes": {},
        "auth_provider": "dev",
        "gender": "Prefer not to say",
        "preferred_language": "English",
        "location": "United States",
        "date_of_birth": f"{2026 - age}-06-01",
        "user_type": "student",
    }
    mongo_db.users.insert_one(user_doc)

    jwt_token = create_jwt_token({
        "user_id": user_id,
        "email": user_doc["email"],
        "name": request.name,
        "age": age,
    })

    logger.info(f"[DEV] Created test user {user_id}, age={age}, grade={current_grade}")

    return {
        "token": jwt_token,
        "user": {
            "user_id": user_id,
            "name": request.name,
            "email": user_doc["email"],
            "age": age,
            "current_grade": current_grade,
        },
        "is_new_user": True,
    }


@app.post("/auth/logout")
async def logout():
    """Logout endpoint (frontend clears token)"""
    return {"message": "Logged out successfully"}


@app.get("/auth/check-completeness")
async def check_user_completeness(request: Request):
    """
    Check if user has all required information and assessment status.
    Returns missing fields, assessment status, and user readiness.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload["sub"]
    
    # Get user from database
    from managers.mongodb_manager import mongo_db
    user_data = mongo_db.users.find_one({"user_id": user_id})
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check assessment status for primary subject (math)
    assessment = mongo_db.subject_assessments.find_one({
        "user_id": user_id,
        "subject": "math"
    })
    
    assessment_completed = assessment and assessment.get("assessment_completed", False)
    
    # Determine required fields
    required_fields = {
        "date_of_birth": True,  # Required for age calculation
        "gender": True,
        "preferred_language": True,
    }
    
    # Optional but recommended fields
    optional_fields = {
        "location": False,
    }
    
    # Check missing required fields
    missing_fields = []
    for field, required in {**required_fields, **optional_fields}.items():
        value = user_data.get(field)
        if required and (not value or value == "" or value is None):
            missing_fields.append(field)
    
    # Determine readiness status
    if missing_fields:
        readiness_status = "needs_info"
    elif not assessment_completed:
        readiness_status = "needs_assessment"
    else:
        readiness_status = "complete"
    
    return {
        "is_complete": len(missing_fields) == 0,
        "missing_fields": missing_fields,
        "assessment_completed": assessment_completed,
        "assessment_subject": "math",
        "user_data": {
            "date_of_birth": user_data.get("date_of_birth"),
            "gender": user_data.get("gender"),
            "preferred_language": user_data.get("preferred_language"),
            "location": user_data.get("location"),
            "age": user_data.get("age"),
            "current_grade": user_data.get("current_grade"),
        },
        "readiness_status": readiness_status
    }


@app.post("/auth/update-missing-info")
async def update_missing_info(request: Request, update_data: UpdateMissingInfoRequest):
    """
    Update missing user information with validation and grade recalculation.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload["sub"]
    
    # Get user profile
    user_profile = user_manager.load_user(user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build update dictionary
    update_dict = {}
    
    if update_data.date_of_birth:
        # Validate and recalculate age/grade
        today = datetime.now().date()
        age = today.year - update_data.date_of_birth.year - (
            (today.month, today.day) < (update_data.date_of_birth.month, update_data.date_of_birth.day)
        )
        
        if age < 5 or age > 18:
            raise HTTPException(status_code=400, detail="Age must be between 5 and 18")
        
        current_grade = calculate_grade_from_age(age)
        update_dict["date_of_birth"] = update_data.date_of_birth.isoformat()
        update_dict["age"] = age
        update_dict["current_grade"] = current_grade
        
        # Update UserProfile (only age and grade are in the dataclass)
        user_profile.age = age
        user_profile.current_grade = current_grade
    
    if update_data.gender:
        if update_data.gender not in ["Male", "Female", "Other", "Prefer not to say"]:
            raise HTTPException(status_code=400, detail="Invalid gender value")
        update_dict["gender"] = update_data.gender
    
    if update_data.preferred_language:
        if update_data.preferred_language not in ["English", "Hindi", "Spanish", "French"]:
            raise HTTPException(status_code=400, detail="Invalid language value")
        update_dict["preferred_language"] = update_data.preferred_language
    
    if update_data.location:
        update_dict["location"] = update_data.location
    
    # Update MongoDB
    from managers.mongodb_manager import mongo_db
    if update_dict:
        mongo_db.users.update_one(
            {"user_id": user_id},
            {"$set": update_dict}
        )
        
        # Save updated UserProfile
        user_manager.save_user(user_profile)
        
        logger.info(f"[USER_UPDATE] Updated fields for {user_id}: {list(update_dict.keys())}")
    
    return {
        "success": True,
        "updated_fields": list(update_dict.keys()),
        "user_data": {
            "age": user_profile.age,
            "current_grade": user_profile.current_grade
        }
    }


@app.get("/auth/gemini-key")
async def get_gemini_key(request: Request):
    """REMOVED — raw API key exposure. Use /auth/gemini-token for ephemeral tokens."""
    raise HTTPException(status_code=410, detail="This endpoint has been removed. Use /auth/gemini-token instead.")


@app.get("/auth/gemini-token")
async def get_gemini_token(request: Request):
    """Get ephemeral token for Gemini Live API (secure - single use)"""
    try:
        # Verify JWT token
        user_id = get_current_user(request)

        # Get API key and model from environment variables
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-native-audio-preview-09-2025")

        if not api_key:
            logger.error("GEMINI_API_KEY not configured in environment")
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        if not model:
            logger.error("GEMINI_MODEL not configured in environment")
            raise HTTPException(status_code=500, detail="Gemini model not configured")

        # Create ephemeral token using Google GenAI SDK
        # IMPORTANT: Ephemeral tokens require v1alpha API version
        import google.genai as genai

        client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1alpha'}
        )

        # Create single-use ephemeral token
        token = client.auth_tokens.create(
            config={
                'uses': 1,  # Single use only - expires after one connection
            }
        )

        logger.info(f"Created ephemeral token for user {user_id}")

        return {
            "token": token.name,
            "model": model
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ephemeral token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create token: {str(e)}")


# Register Payment API router (Phase 4 - Week 2)
from services.PaymentService.api import router as payment_router
app.include_router(payment_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
