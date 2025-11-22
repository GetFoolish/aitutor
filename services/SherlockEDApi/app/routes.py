from fastapi import APIRouter
import json
import pathlib
from pydantic import BaseModel, Field
from typing import List
from .khan_questions_loader import load_questions

router = APIRouter()

class Question(BaseModel):
    question: dict = Field(description="The question data")
    answerArea: dict = Field(description="The answer area")
    hints: List = Field(description="List of question hints")

@router.get("/questions/{sample_size}", response_model=List[Question])
async def get_questions(sample_size: int = 14):
    """Endpoint for retrieving questions"""
    data = load_questions(
        sample_size=sample_size
    )
    return data