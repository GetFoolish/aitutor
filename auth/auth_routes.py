"""
Authentication Routes - Signup, Login, OAuth
"""
from fastapi import APIRouter, HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
import uuid

from .auth_models import (
    UserCreate, UserLogin, UserResponse, Token, OAuthUserCreate,
    ChildAccountCreate, AuthProvider, AccountType, TokenData
)
from .auth_utils import (
    get_password_hash, verify_password, create_access_token, decode_access_token
)
from db.auth_repository import (
    get_user_by_email, get_user_by_id, get_user_by_oauth_id,
    create_user, update_last_login, add_child_to_parent, get_user_credits
)
from user_manager import UserManager

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize UserManager for skill cold-start
user_manager = UserManager(use_mongo=True)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    """Sign up a new user with email and password"""

    # Check if user already exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Generate user ID
    user_id = str(uuid.uuid4())

    # Hash password
    hashed_password = get_password_hash(user_data.password)

    # Create user document
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "hashed_password": hashed_password,
        "account_type": user_data.account_type.value,
        "age": user_data.age,
        "language": user_data.language,
        "region": user_data.region,
        "auth_provider": AuthProvider.EMAIL.value,
        "oauth_id": None,
        "credits": 100,  # Initial credits
        "parent_id": None,
        "children": [],
        "profile_picture": None,
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow(),
        "is_active": True,

        # Gamification fields
        "xp": 0,
        "level": 1,
        "streak_count": 0,
        "last_practice_date": None,
        "daily_goal_xp": 50,
    }

    # Save to database
    create_user(user_doc)

    # Initialize cold-start skills for the user
    # Load all skill IDs from skills collection
    from DashSystem.dash_system import DASHSystem
    dash = DASHSystem()
    all_skill_ids = list(dash.skills.keys())
    user_manager.get_or_create_user(user_id, all_skill_ids)

    # Create JWT token
    access_token = create_access_token(data={"user_id": user_id, "email": user_data.email})

    # Prepare response
    user_response = UserResponse(
        user_id=user_id,
        email=user_data.email,
        name=user_data.name,
        account_type=user_data.account_type,
        age=user_data.age,
        language=user_data.language,
        region=user_data.region,
        credits=100,
        parent_id=None,
        children=[],
        profile_picture=None,
        created_at=user_doc["created_at"],
        last_login=user_doc["last_login"],
    )

    return Token(access_token=access_token, user=user_response)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login with email and password"""

    # Get user
    user = get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not user.get("hashed_password") or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Update last login
    update_last_login(user["user_id"])

    # Create JWT token
    access_token = create_access_token(data={"user_id": user["user_id"], "email": user["email"]})

    # Prepare response
    user_response = UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user["name"],
        account_type=AccountType(user["account_type"]),
        age=user.get("age"),
        language=user.get("language", "en"),
        region=user.get("region", "US"),
        credits=user.get("credits", 0),
        parent_id=user.get("parent_id"),
        children=user.get("children", []),
        profile_picture=user.get("profile_picture"),
        created_at=user["created_at"],
        last_login=datetime.utcnow(),
    )

    return Token(access_token=access_token, user=user_response)


from pydantic import BaseModel as PydanticBaseModel

class GoogleOAuthRequest(PydanticBaseModel):
    id_token: str

class AppleOAuthRequest(PydanticBaseModel):
    id_token: str

class FacebookOAuthRequest(PydanticBaseModel):
    access_token: str


@router.post("/oauth/google", response_model=Token)
async def google_oauth(request: GoogleOAuthRequest):
    """Google OAuth login/signup"""
    from .oauth_providers import OAuthProvider

    # Verify Google ID token
    user_info = OAuthProvider.verify_google_token(request.id_token)

    # Check if user exists
    user = get_user_by_oauth_id(AuthProvider.GOOGLE.value, user_info['oauth_id'])

    if user:
        # Existing user - login
        update_last_login(user["user_id"])
        user_id = user["user_id"]
    else:
        # New user - signup
        user_id = str(uuid.uuid4())

        user_doc = {
            "user_id": user_id,
            "email": user_info['email'],
            "name": user_info['name'],
            "hashed_password": None,  # OAuth users don't have passwords
            "account_type": AccountType.SELF_LEARNER.value,
            "age": None,
            "language": "en",
            "region": "US",
            "auth_provider": AuthProvider.GOOGLE.value,
            "oauth_id": user_info['oauth_id'],
            "credits": 100,
            "parent_id": None,
            "children": [],
            "profile_picture": user_info.get('picture'),
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow(),
            "is_active": True,
        }

        create_user(user_doc)

        # Initialize cold-start skills
        from DashSystem.dash_system import DASHSystem
        dash = DASHSystem()
        all_skill_ids = list(dash.skills.keys())
        user_manager.get_or_create_user(user_id, all_skill_ids)

        user = user_doc

    # Create JWT token
    access_token = create_access_token(data={"user_id": user_id, "email": oauth_user.email})

    user_response = UserResponse(
        user_id=user_id,
        email=user["email"],
        name=user["name"],
        account_type=AccountType(user["account_type"]),
        age=user.get("age"),
        language=user.get("language", "en"),
        region=user.get("region", "US"),
        credits=user.get("credits", 0),
        parent_id=user.get("parent_id"),
        children=user.get("children", []),
        profile_picture=user.get("profile_picture"),
        created_at=user["created_at"],
        last_login=datetime.utcnow(),
    )

    return Token(access_token=access_token, user=user_response)


@router.post("/oauth/apple", response_model=Token)
async def apple_oauth(oauth_user: OAuthUserCreate):
    """Apple OAuth login/signup"""
    # Same logic as Google OAuth but with Apple provider
    oauth_user.auth_provider = AuthProvider.APPLE
    return await google_oauth(oauth_user)  # Reuse the logic


@router.post("/oauth/facebook", response_model=Token)
async def facebook_oauth(oauth_user: OAuthUserCreate):
    """Facebook OAuth login/signup"""
    # Same logic as Google OAuth but with Facebook provider
    oauth_user.auth_provider = AuthProvider.FACEBOOK
    return await google_oauth(oauth_user)  # Reuse the logic


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return UserResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        name=current_user["name"],
        account_type=AccountType(current_user["account_type"]),
        age=current_user.get("age"),
        language=current_user.get("language", "en"),
        region=current_user.get("region", "US"),
        credits=current_user.get("credits", 0),
        parent_id=current_user.get("parent_id"),
        children=current_user.get("children", []),
        profile_picture=current_user.get("profile_picture"),
        created_at=current_user["created_at"],
        last_login=current_user["last_login"],
    )


@router.post("/parent/create-child", response_model=UserResponse)
async def create_child_account(
    child_data: ChildAccountCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a child account under parent"""

    # Verify current user is a parent
    if current_user["account_type"] != AccountType.PARENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parent accounts can create child accounts"
        )

    # Generate child user ID
    child_id = str(uuid.uuid4())

    # Create child document
    child_doc = {
        "user_id": child_id,
        "email": f"{child_id}@child.account",  # Placeholder email
        "name": child_data.name,
        "hashed_password": None,
        "account_type": AccountType.SELF_LEARNER.value,
        "age": child_data.age,
        "language": child_data.language,
        "region": child_data.region,
        "auth_provider": AuthProvider.EMAIL.value,
        "oauth_id": None,
        "credits": 100,
        "parent_id": current_user["user_id"],
        "children": [],
        "profile_picture": None,
        "created_at": datetime.utcnow(),
        "last_login": datetime.utcnow(),
        "is_active": True,
    }

    # Save child
    create_user(child_doc)

    # Add child to parent's children list
    add_child_to_parent(current_user["user_id"], child_id)

    # Initialize cold-start skills
    from DashSystem.dash_system import DASHSystem
    dash = DASHSystem()
    all_skill_ids = list(dash.skills.keys())
    user_manager.get_or_create_user(child_id, all_skill_ids)

    return UserResponse(
        user_id=child_id,
        email=child_doc["email"],
        name=child_doc["name"],
        account_type=AccountType.SELF_LEARNER,
        age=child_doc["age"],
        language=child_doc["language"],
        region=child_doc["region"],
        credits=child_doc["credits"],
        parent_id=child_doc["parent_id"],
        children=[],
        profile_picture=None,
        created_at=child_doc["created_at"],
        last_login=child_doc["last_login"],
    )


@router.get("/credits/balance")
async def get_credit_balance(current_user: dict = Depends(get_current_user)):
    """Get user's credit balance"""
    return {"credits": current_user.get("credits", 0)}
