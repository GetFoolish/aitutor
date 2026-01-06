"""
Auth Service - Google OAuth authentication API
"""
import os
import sys
import logging
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
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
    subjects: Optional[List[str]] = []
    learning_goals: Optional[List[str]] = []
    interests: Optional[List[str]] = []
    learning_style: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AuthService"}


@app.get("/auth/google")
async def google_login():
    """Initiate Google OAuth flow"""
    try:
        authorization_url, state = oauth_handler.get_authorization_url()
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
            
            # Redirect to frontend with token
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            return RedirectResponse(
                url=f"{frontend_url}/app/login?token={jwt_token}&is_new_user=false"
            )
        else:
            # New user - need to complete setup
            setup_token = create_setup_token(google_user)
            
            # Redirect to frontend setup page
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            return RedirectResponse(
                url=f"{frontend_url}/app/login?setup_token={setup_token}"
            )
            
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


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
async def email_signup(request: EmailSignupRequest):
    """Register a new user with email and password"""
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
async def email_login(request: EmailLoginRequest):
    """Login with email and password"""
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
        "name": user_data.get("google_name", "") if user_data else "",
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
    
    return {
        "user_id": user_profile.user_id,
        "email": email,
        "name": name,
        "date_of_birth": date_of_birth,
        "location": location,
        "credits": credits
    }


@app.post("/auth/logout")
async def logout():
    """Logout endpoint (frontend clears token)"""
    return {"message": "Logged out successfully"}


@app.get("/auth/gemini-key")
async def get_gemini_key(request: Request):
    """Get Gemini API key for authenticated user (DEPRECATED - use /auth/gemini-token instead)"""
    try:
        # Verify JWT token
        user_id = get_current_user(request)

        # Get API key and model from environment variables
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-native-audio-preview-09-2025")

        if not api_key:
            logger.error("GEMINI_API_KEY not configured in environment")
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        return {
            "api_key": api_key,
            "model": model
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Gemini API key: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get API key: {str(e)}")


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
        logger.info(f"Token name: {token.name}")
        logger.info(f"Token object: {token}")

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

