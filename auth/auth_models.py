"""
Authentication and User Profile Models
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class AccountType(str, Enum):
    SELF_LEARNER = "self-learner"
    PARENT = "parent"


class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"
    FACEBOOK = "facebook"


class UserBase(BaseModel):
    email: EmailStr
    name: str
    account_type: AccountType = AccountType.SELF_LEARNER
    age: Optional[int] = None
    language: str = "en"
    region: str = "US"


class UserCreate(UserBase):
    password: str
    auth_provider: AuthProvider = AuthProvider.EMAIL


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OAuthUserCreate(UserBase):
    auth_provider: AuthProvider
    oauth_id: str  # ID from OAuth provider
    profile_picture: Optional[str] = None


class UserInDB(UserBase):
    user_id: str
    hashed_password: Optional[str] = None  # None for OAuth users
    auth_provider: AuthProvider
    oauth_id: Optional[str] = None
    credits: int = 100  # Starting credits
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    profile_picture: Optional[str] = None
    created_at: datetime
    last_login: datetime
    is_active: bool = True

    # Gamification fields
    xp: int = 0  # Experience points
    level: int = 1  # User level
    streak_count: int = 0  # Days of consecutive practice
    last_practice_date: Optional[str] = None  # ISO date string (YYYY-MM-DD)
    daily_goal_xp: int = 50  # Daily XP goal


class UserResponse(UserBase):
    user_id: str
    credits: int
    parent_id: Optional[str] = None
    children: List[str]
    profile_picture: Optional[str] = None
    created_at: datetime
    last_login: datetime

    # Gamification fields
    xp: int = 0
    level: int = 1
    streak_count: int = 0
    last_practice_date: Optional[str] = None
    daily_goal_xp: int = 50


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None


class ChildAccountCreate(BaseModel):
    name: str
    age: int
    language: str = "en"
    region: str = "US"
