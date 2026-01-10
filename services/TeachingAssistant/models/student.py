"""
Student Model - Pydantic models for student data and biography
Based on the Cognitive Memory Pipeline architecture
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OnboardingData(BaseModel):
    """Data collected during student onboarding"""
    core_values: List[str] = Field(default_factory=list, description="Student's core values")
    north_star_goals: List[str] = Field(default_factory=list, description="Long-term goals")
    personality_traits: List[str] = Field(default_factory=list, description="Personality characteristics")
    blind_spots: List[str] = Field(default_factory=list, description="Areas of self-unawareness")
    emotional_baseline: str = Field(default="neutral", description="Default emotional state")
    interests: List[str] = Field(default_factory=list, description="Hobbies and interests")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Milestone(BaseModel):
    """Academic milestone or breakthrough"""
    date: datetime
    description: str
    topic: Optional[str] = None


class AcademicJourney(BaseModel):
    """Tracks academic progress over time"""
    current_topic: str = Field(default="", description="Current focus area")
    mastered_topics: List[str] = Field(default_factory=list, description="Topics student has mastered")
    struggling_topics: List[str] = Field(default_factory=list, description="Topics needing work")
    milestones: List[Milestone] = Field(default_factory=list, description="Key breakthroughs")


class BiographyVersion(BaseModel):
    """A versioned snapshot of the student's biography"""
    version: int
    text: str
    created_at: datetime
    session_count: int


class Biography(BaseModel):
    """Living Biography - the core innovation of TA v5"""
    text: str = Field(default="", description="The narrative biography (300-500 words)")
    version: int = Field(default=0, description="Version number")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    session_count: int = Field(default=0, description="Sessions included in this biography")


class StudentStatistics(BaseModel):
    """Aggregate statistics for a student"""
    total_sessions: int = 0
    total_questions_answered: int = 0
    total_questions_correct: int = 0
    average_session_duration_minutes: float = 0.0
    last_session_date: Optional[datetime] = None


class Student(BaseModel):
    """
    Complete student document for MongoDB.

    The Living Biography is the core of the cognitive memory system:
    - A narrative document (300-500 words) that tells the story of who the student is
    - Updated after every session by the Biographer Agent
    - Injected into system prompt at session start
    """
    id: str = Field(alias="_id")
    name: str
    email: Optional[str] = None
    onboarding_data: OnboardingData = Field(default_factory=OnboardingData)
    biography: Biography = Field(default_factory=Biography)
    biography_history: List[BiographyVersion] = Field(default_factory=list)
    academic_journey: AcademicJourney = Field(default_factory=AcademicJourney)
    statistics: StudentStatistics = Field(default_factory=StudentStatistics)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StudentCreate(BaseModel):
    """Model for creating a new student"""
    name: str
    email: Optional[str] = None
    onboarding_data: Optional[OnboardingData] = None


class StudentUpdate(BaseModel):
    """Model for updating student data"""
    name: Optional[str] = None
    email: Optional[str] = None
    onboarding_data: Optional[OnboardingData] = None
    biography: Optional[Biography] = None
    academic_journey: Optional[AcademicJourney] = None
