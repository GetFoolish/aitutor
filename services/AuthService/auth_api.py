"""
Auth Service - Google OAuth authentication API
"""
import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from urllib.parse import urlencode

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.AuthService.oauth_handler import GoogleOAuthHandler
from services.AuthService.jwt_utils import create_jwt_token, create_setup_token, verify_setup_token, verify_token
from managers.user_manager import UserManager
from managers.user_manager import calculate_grade_from_age
from shared.auth_middleware import get_current_user
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS
from shared.timing_middleware import UnpluggedTimingMiddleware
from shared.cache_middleware import CacheControlMiddleware

from shared.logging_config import get_logger

logger = get_logger(__name__)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

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
OAUTH_STATE_COOKIE = "oauth_state"

# Initialize OAuth handler
oauth_handler = GoogleOAuthHandler(REDIRECT_URI)

# Initialize UserManager
user_manager = UserManager()


def oauth_cookie_secure() -> bool:
    return BASE_URL.startswith("https://")


def oauth_cookie_samesite() -> str:
    return "none" if oauth_cookie_secure() else "lax"


def set_oauth_state_cookie(response: JSONResponse, state: str) -> None:
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=oauth_cookie_secure(),
        samesite=oauth_cookie_samesite(),
        max_age=600,
        path="/auth",
    )


def clear_oauth_state_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(
        key=OAUTH_STATE_COOKIE,
        path="/auth",
        httponly=True,
        secure=oauth_cookie_secure(),
        samesite=oauth_cookie_samesite(),
    )


def build_frontend_redirect(fragment_params: dict[str, str]) -> RedirectResponse:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    response = RedirectResponse(
        url=f"{frontend_url}/app/login#{urlencode(fragment_params)}"
    )
    clear_oauth_state_cookie(response)
    return response


class CompleteSetupRequest(BaseModel):
    setup_token: str
    user_type: str  # "student" or "parent" (but always stored as "student")
    age: int


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AuthService"}


@app.get("/auth/google")
async def google_login():
    """Initiate Google OAuth flow"""
    try:
        authorization_url, state = oauth_handler.get_authorization_url()
        response = JSONResponse({
            "authorization_url": authorization_url,
            "state": state
        })
        set_oauth_state_cookie(response, state)
        return response
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth: {str(e)}")


@app.get("/auth/callback")
async def google_callback(request: Request, code: Optional[str] = Query(None), state: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """Handle Google OAuth callback"""
    if error:
        logger.error(f"OAuth error: {error}")
        return JSONResponse(
            status_code=400,
            content={"error": "OAuth authentication failed", "details": error}
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")
    if not expected_state or state != expected_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    
    try:
        # Get user info from Google
        google_user = await oauth_handler.get_user_info(code, state, str(request.url))
        
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
            
            return build_frontend_redirect(
                {
                    "token": jwt_token,
                    "is_new_user": "false",
                }
            )
        else:
            # New user - need to complete setup
            setup_token = create_setup_token(google_user)
            
            return build_frontend_redirect({"setup_token": setup_token})
            
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@app.post("/auth/complete-setup")
async def complete_setup(request: CompleteSetupRequest):
    """Complete user setup with age and user_type"""
    try:
        # Verify setup token
        google_user_data = verify_setup_token(request.setup_token)
        
        if not google_user_data:
            raise HTTPException(status_code=400, detail="Invalid or expired setup token")
        
        # Validate age
        if request.age < 5 or request.age > 18:
            raise HTTPException(status_code=400, detail="Age must be between 5 and 18")
        
        # Validate user_type (but always store as "student" for now)
        if request.user_type not in ["student", "parent"]:
            raise HTTPException(status_code=400, detail="user_type must be 'student' or 'parent'")
        
        # Create user (always store as "student" regardless of frontend selection)
        user_profile = user_manager.create_google_user(
            google_id=google_user_data["google_id"],
            email=google_user_data["email"],
            name=google_user_data["name"],
            age=request.age,
            picture=google_user_data.get("picture", ""),
            user_type="student"  # Always "student" for now
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
                "user_type": "student"
            },
            "is_new_user": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing setup: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


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
        "name": user_data.get("google_name", "") if user_data else "",
        "age": user_profile.age,
        "current_grade": user_profile.current_grade,
        "user_type": user_data.get("user_type", "student") if user_data else "student"
    }


@app.post("/auth/logout")
async def logout():
    """Logout endpoint (frontend clears token)"""
    return {"message": "Logged out successfully"}


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

        logger.info(f"Created ephemeral Gemini token for user {user_id}")

        return {
            "token": token.name,
            "model": model
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ephemeral token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create token: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)
