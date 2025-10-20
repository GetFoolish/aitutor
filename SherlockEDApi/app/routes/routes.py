from math import e 
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import asyncio
import json
import uuid
import pathlib 
from typing import List
from app.utils.khan_questions_loader import load_questions

router = APIRouter()

base_dir=pathlib.Path(__file__).resolve().parents[2] / "CurriculumBuilder_Validated"

# endpoint to get questions 
@router.get("/questions/{sample_size}")
async def get_questions(sample_size: int):
    """Endpoint for retrieving questions"""
    data = load_questions(
        sample_size=sample_size
    )
    return data

# endpoint to get generated questions
@router.get("/generated-questions/{sample_size}")
async def get_generated_questions(sample_size: int):
    """Endpoint for retrieving generated questions"""
    data = load_questions(
        sample_size=sample_size,
        is_generated=True
    )
    return data 

@router.post("/save-validated-question")
async def save_validated_json(request: Request):
    data = await request.json()
    file_path = base_dir / f"{str(uuid.uuid4())}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return JSONResponse(
        content={"message":"JSON saved successfully"},
        status_code=201
    )
    