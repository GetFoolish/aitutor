"""
API Routes for Athena API

Endpoints for fetching and managing questions in Athena format.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .question_loader import (
    get_question_by_id,
    get_questions,
    get_questions_by_ids,
    get_widget_types_summary,
    search_questions,
)

router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class AthenaWidget(BaseModel):
    type: str
    options: Dict[str, Any]
    alignment: str = "default"
    graded: bool = True
    static: bool = False


class AthenaQuestion(BaseModel):
    content: str
    widgets: Dict[str, AthenaWidget]
    images: Dict[str, Any] = {}


class AthenaHint(BaseModel):
    content: str
    widgets: Dict[str, AthenaWidget] = {}
    images: Dict[str, Any] = {}
    replace: bool = False


class AthenaAnswerArea(BaseModel):
    calculator: bool = False
    periodicTable: bool = False
    chi2Table: bool = False
    tTable: bool = False
    zTable: bool = False
    financialCalculator: bool = False


class AthenaItem(BaseModel):
    id: str = Field(alias="_id", default="")
    slug: str = ""
    skill_prefix: str = ""
    question: AthenaQuestion
    hints: List[AthenaHint] = []
    answerArea: AthenaAnswerArea
    widgetTypes: List[str] = []

    class Config:
        populate_by_name = True


class WidgetTypeSummary(BaseModel):
    widget_types: Dict[str, int]
    total_questions: int


class QuestionSearchRequest(BaseModel):
    query: str
    limit: int = 20


class QuestionIdsRequest(BaseModel):
    ids: List[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/question/{question_id}")
async def get_single_question(question_id: str):
    """
    Fetch a single question by its MongoDB ObjectId.

    Use this to view a specific question in the Athena renderer.
    """
    question = get_question_by_id(question_id)

    if not question:
        raise HTTPException(
            status_code=404,
            detail=f"Question not found: {question_id}"
        )

    return question


@router.get("/questions/{sample_size}")
async def get_multiple_questions(
    sample_size: int = 10,
    widget_types: Optional[str] = Query(None, description="Comma-separated widget types"),
    skill_prefix: Optional[str] = Query(None, description="Skill prefix filter")
):
    """
    Fetch multiple random questions.

    Args:
        sample_size: Number of questions to fetch (default: 10)
        widget_types: Comma-separated list of widget types to filter
        skill_prefix: Filter by skill prefix

    Returns:
        List of Athena-formatted questions
    """
    # Parse widget types
    types_list = None
    if widget_types:
        types_list = [t.strip() for t in widget_types.split(',')]

    questions = get_questions(
        sample_size=sample_size,
        widget_types=types_list,
        skill_prefix=skill_prefix
    )

    if not questions:
        raise HTTPException(
            status_code=404,
            detail="No questions found matching criteria"
        )

    return questions


@router.post("/questions/by-ids")
async def get_questions_by_object_ids(request: QuestionIdsRequest):
    """
    Fetch multiple questions by their ObjectIds.

    Useful for loading a specific set of questions.
    """
    questions = get_questions_by_ids(request.ids)

    if not questions:
        raise HTTPException(
            status_code=404,
            detail="No questions found for provided IDs"
        )

    return questions


@router.get("/widget-types")
async def get_available_widget_types():
    """
    Get a summary of all widget types in the database.

    Useful for understanding what types of questions are available.
    """
    summary = get_widget_types_summary()

    return {
        "widget_types": summary,
        "total_types": len(summary),
        "total_widgets": sum(summary.values())
    }


@router.post("/questions/search")
async def search_questions_endpoint(request: QuestionSearchRequest):
    """
    Search questions by content text.

    Searches in question content and slug.
    """
    questions = search_questions(request.query, request.limit)

    return {
        "results": questions,
        "count": len(questions),
        "query": request.query
    }


@router.get("/questions/random")
async def get_random_questions(
    count: int = Query(5, ge=1, le=50, description="Number of questions")
):
    """
    Get random questions for practice.
    """
    questions = get_questions(sample_size=count)
    return questions


@router.get("/stats")
async def get_database_stats():
    """
    Get statistics about the question database.
    """
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sys.path.insert(0, project_root)

    from managers.mongodb_manager import mongo_db

    total_questions = mongo_db.perseus_questions.count_documents({})
    widget_summary = get_widget_types_summary()

    return {
        "total_questions": total_questions,
        "widget_types": widget_summary,
        "service": "athenaAPI",
        "renderer": "Athena"
    }
