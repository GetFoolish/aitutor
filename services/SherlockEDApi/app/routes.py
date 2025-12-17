from fastapi import APIRouter, Query, HTTPException
import json
import pathlib
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from .khan_questions_loader import load_questions, load_question_by_id, _load_cache, _questions_by_widget_type, _questions_cache

router = APIRouter()

class Question(BaseModel):
    id: str = Field(default="", alias="_id", description="Question ID")
    question: dict = Field(description="The question data")
    answerArea: dict = Field(description="The answer area")
    hints: List = Field(description="List of question hints")
    widgetTypes: List[str] = Field(default=[], description="Widget types in this question")
    courseName: str = Field(default="", description="Course name")
    lessonName: str = Field(default="", description="Lesson name")

    class Config:
        extra = "allow"
        populate_by_name = True


@router.get("/questions/{sample_size}", response_model=List[Question])
async def get_questions(
    sample_size: int = 14,
    widget_types: Optional[str] = Query(None, description="Comma-separated widget types to filter by")
):
    """Endpoint for retrieving questions. Optionally filter by widget types."""
    types_list = None
    if widget_types:
        types_list = [t.strip() for t in widget_types.split(",") if t.strip()]

    data = load_questions(sample_size=sample_size, widget_types=types_list)
    return data


@router.get("/question/{question_id}")
async def get_question_by_id(question_id: str):
    """Endpoint for retrieving a specific question by its ObjectID"""
    data = load_question_by_id(question_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Question not found: {question_id}")
    return data


@router.get("/widget-types")
async def get_widget_types():
    """Get available widget types and their counts"""
    _load_cache()  # Ensure cache is loaded
    return {
        "total_questions": len(_questions_cache),
        "widget_types": {wt: len(questions) for wt, questions in _questions_by_widget_type.items()}
    }


@router.get("/stats")
async def get_stats():
    """Get database statistics"""
    _load_cache()
    return {
        "total_questions": len(_questions_cache),
        "widget_types": {wt: len(questions) for wt, questions in _questions_by_widget_type.items()}
    }