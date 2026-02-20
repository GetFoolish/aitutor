"""
Pydantic models for MongoDB question documents.

Provides schema validation to prevent silent None cascades from malformed data.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class WidgetType(str, Enum):
    """Supported Perseus widget types."""
    RADIO = "radio"
    NUMERIC_INPUT = "numeric-input"
    DROPDOWN = "dropdown"
    EXPRESSION = "expression"
    MATCHER = "matcher"
    SORTER = "sorter"
    ORDERER = "orderer"
    DEFINITION = "definition"
    IMAGE = "image"


class PerseusWidget(BaseModel):
    """Base Perseus widget structure."""
    type: str
    graded: Optional[bool] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    alignment: Optional[str] = "default"
    static: Optional[bool] = False
    version: Optional[Dict[str, int]] = None

    class Config:
        extra = "allow"  # Perseus has many optional fields


class PerseusQuestion(BaseModel):
    """Perseus question structure."""
    content: str = Field(min_length=1)
    images: Dict[str, Any] = Field(default_factory=dict)
    widgets: Dict[str, PerseusWidget] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Question content cannot be empty")
        return v

    @field_validator("widgets")
    @classmethod
    def at_least_one_widget(cls, v: Dict[str, PerseusWidget]) -> Dict[str, PerseusWidget]:
        if not v:
            raise ValueError("Question must have at least one widget")
        return v

    class Config:
        extra = "allow"


class PerseusHint(BaseModel):
    """Perseus hint structure."""
    content: str = Field(min_length=10)
    images: Dict[str, Any] = Field(default_factory=dict)
    widgets: Dict[str, Any] = Field(default_factory=dict)
    replace: bool = False

    class Config:
        extra = "allow"


class PerseusAnswerArea(BaseModel):
    """Perseus answer area configuration."""
    calculator: bool = False
    type: str = "multiple"

    class Config:
        extra = "allow"


class DashMetadata(BaseModel):
    """DASH system metadata for questions."""
    skill_ids: List[str] = Field(default_factory=list)
    skill_names: List[str] = Field(default_factory=list)
    difficulty: float = Field(ge=0.0, le=1.0)
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    dash_question_id: Optional[str] = None

    class Config:
        extra = "allow"


class PerseusItem(BaseModel):
    """Complete Perseus question item."""
    question: PerseusQuestion
    answerArea: PerseusAnswerArea = Field(default_factory=lambda: PerseusAnswerArea())
    hints: List[PerseusHint] = Field(default_factory=list)
    dash_metadata: Optional[DashMetadata] = None

    @field_validator("hints")
    @classmethod
    def validate_hints(cls, v: List[PerseusHint]) -> List[PerseusHint]:
        """Ensure hints are meaningful if present."""
        for hint in v:
            if len(hint.content.strip()) < 10:
                raise ValueError(f"Hint content too short: '{hint.content}'")
        return v

    class Config:
        extra = "allow"


class QuestionDocument(BaseModel):
    """MongoDB document for stored questions."""
    question_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    skill_name: str = Field(min_length=1)
    item: PerseusItem
    difficulty: float = Field(ge=0.0, le=1.0)
    format: str
    created_at: datetime
    content_hash: Optional[str] = None

    # Optional quality tracking fields
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    attempt_count: Optional[int] = Field(None, ge=0)
    correct_count: Optional[int] = Field(None, ge=0)

    class Config:
        extra = "allow"  # Allow additional fields for flexibility


class ContentPoolDocument(BaseModel):
    """MongoDB document for content pool questions."""
    question_id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    difficulty_bucket: str  # "easy", "medium", "hard", "synthesis"
    item: PerseusItem
    seed: str  # Deterministic seed for reproducibility
    format: str
    created_at: datetime
    content_hash: str = Field(min_length=1)

    # Generation audit trail
    model: Optional[str] = None
    temperature: Optional[float] = None
    prompt_version: Optional[str] = None

    # Verification status
    verified: bool = False
    assessment_verified: bool = False

    # Quality tracking
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    generation_attempts: Optional[int] = Field(None, ge=0)

    class Config:
        extra = "allow"


class AssessmentSession(BaseModel):
    """MongoDB document for assessment sessions."""
    assessment_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    start_time: datetime
    end_time: Optional[datetime] = None
    completed: bool = False

    # Questions and responses
    questions: List[str] = Field(default_factory=list)  # question_ids
    responses: List[Dict[str, Any]] = Field(default_factory=list)

    # Adaptive tracking
    difficulties: List[float] = Field(default_factory=list)
    score: int = 0
    total: int = 0

    class Config:
        extra = "allow"


# Validation helper functions
def validate_perseus_item(data: Dict[str, Any]) -> PerseusItem:
    """
    Validate a Perseus item dictionary against the schema.

    Raises:
        ValidationError: If the data doesn't match the schema

    Returns:
        Validated PerseusItem instance
    """
    return PerseusItem.model_validate(data)


def validate_question_document(data: Dict[str, Any]) -> QuestionDocument:
    """
    Validate a question document from MongoDB.

    Raises:
        ValidationError: If the data doesn't match the schema

    Returns:
        Validated QuestionDocument instance
    """
    return QuestionDocument.model_validate(data)


def safe_get_perseus_item(data: Dict[str, Any]) -> Optional[PerseusItem]:
    """
    Safely extract and validate a Perseus item.

    Returns None instead of raising if validation fails.
    Logs validation errors for debugging.
    """
    try:
        return validate_perseus_item(data)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[SCHEMA] Perseus item validation failed: {e}")
        return None
