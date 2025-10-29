from math import e 
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import json
import uuid
import pathlib 
import random 
from beanie import Link
from bson import ObjectId
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from beanie.operators import LTE, GT
from app.utils.khan_questions_loader import load_questions 
from app.database.models import GeneratedQuestionDocument, QuestionDocument

router = APIRouter()

base_dir=pathlib.Path(__file__).resolve().parents[2] / "CurriculumBuilder_validated"

base_dir.mkdir(parents=True, exist_ok=True)

already_seen = set()

file = {}
item = {} # question, image-path
file["data"] = []
file["data"].append(item) 

def update_json_file():
    pass

class Projection(BaseModel):
    answerArea: Optional[Dict] = None
    hints: Optional[List[Dict]] = None
    itemDataVersion: Optional[Dict] = None
    question: Dict


class ProjectionWithID(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    answerArea: Optional[Dict] = None
    hints: Optional[List[Dict]] = None
    itemDataVersion: Optional[Dict] = None
    question: Dict

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("id", mode="before")
    def convert_objectid(cls, v):
        return str(v) if isinstance(v, ObjectId) else v


# endpoint to get questions 
@router.get("/questions/{sample}")
async def get_questions(sample: int): 
    """Endpoint for retrieving questions"""
    data = await QuestionDocument.find_all().limit(sample).project(ProjectionWithID).to_list()
    return JSONResponse(content=[q.model_dump() for q in data], status_code=200)


@router.get("/get-question-for-validation")
async def get_question_for_validation():
    # Fetch all questions with generated_count > 0
    questions = await QuestionDocument.find(
        GT(QuestionDocument.generated_count, 0)
    ).to_list()

    if not questions:
        raise HTTPException(status_code=404, detail="No questions available for validation")

    # Select a random one
    question = random.choice(questions)

    # Fetch its linked generated questions
    await question.fetch_link(QuestionDocument.generated)

    # --- Prepare structured response ---
    data = question.model_dump()

    question_data = {
        "answerArea": data.get("answerArea"),
        "hints": data.get("hints"),
        "question": data.get("question"),
        "itemDataVersion": data.get("itemDataVersion"),
    }

    metadata = {
        "source": data.get("source"),
        "generated_count": data.get("generated_count"),
    }

    generated_data = data.get("generated", [])

    # ✅ Safely encode ObjectIds and nested links
    return JSONResponse(
        content=jsonable_encoder({
            "finished": False,
            "question": question_data,
            "metadata": metadata,
            "generated": generated_data,
        }),
        status_code=200,
    )
    # question = await QuestionDocument.find_one({"_id": ObjectId(id)}).project(Projection)
    # return JSONResponse(content={"finished":False, "question": question.model_dump()}, status_code=200)



@router.get("/get-question-for-generation")
async def get_question_for_generation():
    responses = await QuestionDocument.find(
        QuestionDocument.source == "khan",
        LTE(QuestionDocument.generated_count, 2)).project(ProjectionWithID).to_list()
    if responses:
        response = random.choice(responses)
        return response
    raise HTTPException(status_code=404, detail="No data")


@router.post("/save-generated-question/{source_question_id}")
async def save_generted_question(source_question_id, request: Request):
    data = await request.json()
    question = GeneratedQuestionDocument(**data)
    await question.insert()

    source_question = await QuestionDocument.get(source_question_id)
    if not source_question:
        raise HTTPException(status_code=404, detail="Original document not found")
    source_question.generated.append(question)
    source_question.generated_count = 1
    await source_question.save()

    return JSONResponse(content={"message": "Success"}, status_code=201)

# @router.get("/get-generated-question")
# async def get_generated_question():
#     """Endpoint for retrieving a generated question"""
#     data = await GeneratedQuestionDocument.find(
#         GeneratedQuestionDocument.human_approved == False
#     ).project(ProjectionWithID).to_list()
#     if not data:
#         raise HTTPException(status_code=404, detail="Generated question not found")
#     parent_question = data.fetch_link(
#         GeneratedQuestionDocument.
#     )

# endpoint to get generated questions
@router.get("/generated-questions/{sample_size}")
async def get_generated_questions(sample_size: int):
    """Endpoint for retrieving generated questions"""
    data = load_questions(
        sample_size=sample_size,
        isGenerated=True
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
