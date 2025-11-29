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
from typing import Optional

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.AuthService.oauth_handler import GoogleOAuthHandler
from services.AuthService.jwt_utils import create_jwt_token, create_setup_token, verify_setup_token, verify_token
from managers.user_manager import UserManager
from managers.user_manager import calculate_grade_from_age

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Auth Service")

# Configure CORS with environment-specific origins
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,https://tutor-frontend-staging-utmfhquz6a-uc.a.run.app")
origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Get base URL from environment
BASE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8003")
REDIRECT_URI = f"{BASE_URL}/auth/callback"

# Initialize OAuth handler
oauth_handler = GoogleOAuthHandler(REDIRECT_URI)

# Initialize UserManager
user_manager = UserManager()


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
                url=f"{frontend_url}/auth/callback?token={jwt_token}&is_new_user=false"
            )
        else:
            # New user - need to complete setup
            setup_token = create_setup_token(google_user)
            
            # Redirect to frontend setup page
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            return RedirectResponse(
                url=f"{frontend_url}/auth/setup?setup_token={setup_token}"
            )
            
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
async def get_current_user(request: Request):
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


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)

