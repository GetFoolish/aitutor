"""
Pydantic models for InsightExtractor service
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class EmailCategory(str, Enum):
    """Categories of emails we extract insights from"""
    COURSE_ENROLLMENT = "course_enrollment"
    COURSE_PROGRESS = "course_progress"
    NEWSLETTER = "newsletter"
    CERTIFICATE = "certificate"
    RECEIPT = "receipt"
    JOB_RELATED = "job_related"
    CALENDAR_EVENT = "calendar_event"
    OTHER = "other"


class SkillLevel(str, Enum):
    """Inferred skill level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    UNKNOWN = "unknown"


class LearningStyle(str, Enum):
    """Inferred learning style preferences"""
    VIDEO_COURSES = "video_courses"
    TEXT_ARTICLES = "text_articles"
    INTERACTIVE = "interactive"
    MIXED = "mixed"


class EmailSignal(BaseModel):
    """Raw email signal extracted from Gmail"""
    message_id: str
    sender: str
    sender_domain: str
    subject: str
    snippet: str
    date: datetime
    labels: List[str] = []

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExtractedCourse(BaseModel):
    """Course enrollment/progress extracted from email"""
    platform: str = Field(description="Learning platform (Coursera, Udemy, etc.)")
    course_name: str
    topic: str = Field(description="Main topic/subject area")
    subtopics: List[str] = []
    enrollment_date: Optional[datetime] = None
    status: str = Field(default="enrolled", description="enrolled, in_progress, completed")
    inferred_level: SkillLevel = SkillLevel.UNKNOWN
    confidence: float = Field(default=0.5, ge=0, le=1)


class ExtractedNewsletter(BaseModel):
    """Newsletter subscription extracted from email"""
    name: str
    domain: str
    topics: List[str]
    frequency: str = Field(default="unknown", description="daily, weekly, monthly")
    content_type: str = Field(default="mixed", description="technical, business, general")
    first_seen: Optional[datetime] = None
    count: int = 1


class ExtractedCertificate(BaseModel):
    """Certificate/completion email extracted"""
    platform: str
    course_name: str
    topic: str
    completion_date: Optional[datetime] = None
    credential_id: Optional[str] = None
    skills_demonstrated: List[str] = []


class LearningInsight(BaseModel):
    """Single learning insight derived from email analysis"""
    category: EmailCategory
    source_platform: Optional[str] = None
    topic: str
    subtopics: List[str] = []
    skill_level: SkillLevel = SkillLevel.UNKNOWN
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence_count: int = 1
    last_seen: Optional[datetime] = None


class ColdStartProfile(BaseModel):
    """Aggregated cold start profile for a user"""
    user_id: str
    extraction_timestamp: datetime

    # Extracted data
    interests: List[str] = Field(default=[], description="Primary interest areas")
    active_courses: List[ExtractedCourse] = []
    newsletters: List[ExtractedNewsletter] = []
    certificates: List[ExtractedCertificate] = []

    # Inferred attributes
    inferred_level: SkillLevel = SkillLevel.UNKNOWN
    learning_style: LearningStyle = LearningStyle.MIXED
    preferred_topics: Dict[str, float] = Field(
        default={},
        description="Topic -> confidence score mapping"
    )

    # Career/goal signals
    career_interests: List[str] = []

    # Metadata
    total_emails_scanned: int = 0
    relevant_emails_found: int = 0
    confidence_scores: Dict[str, float] = Field(
        default={},
        description="Confidence in each inferred attribute"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class InsightExtractionRequest(BaseModel):
    """Request to extract insights from Gmail"""
    user_id: str
    access_token: str = Field(description="Gmail OAuth access token")
    max_emails: int = Field(default=500, le=1000, description="Max emails to scan")
    lookback_months: int = Field(default=6, le=12, description="How far back to scan")


class InsightExtractionResponse(BaseModel):
    """Response from insight extraction"""
    success: bool
    user_id: str
    profile: Optional[ColdStartProfile] = None
    error: Optional[str] = None
    processing_time_seconds: float = 0


class GmailConsentRequest(BaseModel):
    """Request to initiate Gmail consent flow"""
    user_id: str
    redirect_uri: str


class GmailConsentResponse(BaseModel):
    """Response with Gmail authorization URL"""
    authorization_url: str
    state: str


class GmailCallbackRequest(BaseModel):
    """OAuth callback data"""
    code: str
    state: str


class UserInsightDocument(BaseModel):
    """MongoDB document for storing user insights"""
    user_id: str
    gmail_connected: bool = False
    gmail_access_token: Optional[str] = None
    gmail_refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None

    last_scan: Optional[datetime] = None
    scan_count: int = 0

    raw_signals: Dict = Field(default_factory=lambda: {
        "courses_detected": [],
        "newsletters": [],
        "certificates": [],
        "calendar_events": []
    })

    processed_profile: Optional[ColdStartProfile] = None

    consent_timestamp: Optional[datetime] = None
    consent_version: str = "1.0"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
