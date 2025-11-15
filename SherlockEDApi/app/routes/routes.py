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
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from beanie.operators import LTE, GT
from app.utils.khan_questions_loader import load_questions 
from app.database.models import GeneratedQuestionDocument, QuestionDocument

router = APIRouter()

base_dir=pathlib.Path(__file__).resolve().parents[2] / "CurriculumBuilder_validated"

base_dir.mkdir(parents=True, exist_ok=True)

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
    """Endpoint for retrieving random questions"""
    # Use aggregation pipeline to get random questions
    data = await QuestionDocument.aggregate(
        [
            {"$sample": {"size": sample}},
            {"$project": {
                "_id": {"$toString": "$_id"}, # Convert ObjectId to string
                "answerArea": "$answerArea",
                "hints": "$hints",
                "itemDataVersion": "$itemDataVersion",
                "question": "$question",
            }}
        ],
        projection_model=ProjectionWithID
    ).to_list()
    return JSONResponse(content=[q.model_dump() for q in data], status_code=200)


@router.get("/question/{id}")
async def get_question_by_id(id: str):
    """Endpoint to get a single QuestionDocument by its ID"""
    question = await QuestionDocument.find_one({"_id": ObjectId(id)}).project(ProjectionWithID)
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    return JSONResponse(content=question.model_dump(), status_code=200)


@router.get("/get-questions-pending-approval")
async def get_questions_pending_approval(sort_by: str = "created_at", order: str = "desc"):
    """
    Get all questions with generated_count > 0, sorted by generation time.
    sort_by: field to sort by (default: "created_at")
    order: "asc" or "desc" (default: "desc")
    """
    from beanie.operators import In
    from pymongo import ASCENDING, DESCENDING
    
    # Fetch all questions with generated_count > 0
    questions = await QuestionDocument.find(
        GT(QuestionDocument.generated_count, 0)
    ).to_list()
    
    # Fetch generated questions for each
    result = []
    for question in questions:
        await question.fetch_all_links()
        data = question.model_dump()
        
        # Get generated questions that are not yet approved
        generated_questions = []
        for gen_q in question.generated:
            # After fetch_all_links(), gen_q should already be a document
            # If it's still a Link, fetch it; otherwise use it directly
            from beanie import Link
            if isinstance(gen_q, Link):
                gen_q = await gen_q.fetch()
            gen_data = gen_q.model_dump()
            if not gen_data.get("human_approved", False):
                # Ensure _id is a string
                gen_id = str(gen_q.id) if hasattr(gen_q, "id") else str(gen_data.get("id", gen_data.get("_id", "")))
                generated_questions.append({
                    "_id": gen_id,
                    "created_at": gen_data.get("created_at"),
                    "generation_cost": gen_data.get("generation_cost"),
                })
        
        # Only include questions that have pending (non-approved) generated items
        if generated_questions:
            result.append({
                "_id": str(question.id),
                "source": data.get("source", "khan"),
                "generated_count": len(generated_questions),
                "created_at": data.get("created_at"),
                "generated": generated_questions,
            })
    
    # Sort results
    reverse_order = (order.lower() == "desc")
    if sort_by == "created_at":
        result.sort(key=lambda x: x.get("created_at", datetime.min), reverse=reverse_order)
    elif sort_by == "generated_count":
        result.sort(key=lambda x: x.get("generated_count", 0), reverse=reverse_order)
    
    return JSONResponse(content=jsonable_encoder(result), status_code=200)


@router.get("/get-question-for-validation")
async def get_question_for_validation(question_id: Optional[str] = None):
    # If question_id is provided, get that specific question
    if question_id:
        question = await QuestionDocument.get(ObjectId(question_id))
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
    else:
        # Fetch all questions with generated_count > 0
        questions = await QuestionDocument.find(
            GT(QuestionDocument.generated_count, 0)
        ).to_list()

        if not questions:
            raise HTTPException(status_code=404, detail="No questions available for validation")
        question = random.choice(questions)
    
    await question.fetch_all_links()
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
        "source_question_id": str(question.id),
    }

    generated_data = []
    for gen_q in question.generated:
        # After fetch_all_links(), gen_q should already be a document
        # If it's still a Link, fetch it; otherwise use it directly
        from beanie import Link
        if isinstance(gen_q, Link):
            gen_q = await gen_q.fetch()
        gen_data = gen_q.model_dump()
        # Normalize id to _id for frontend compatibility
        if "id" in gen_data:
            gen_data["_id"] = str(gen_data["id"])
        elif hasattr(gen_q, "id"):
            gen_data["_id"] = str(gen_q.id)
        generated_data.append(gen_data)

    return JSONResponse(
        content=jsonable_encoder({
            "finished": False,
            "question": question_data,
            "metadata": metadata,
            "generated": generated_data,
        }),
        status_code=200,
    )


@router.get("/get-question-for-generation")
async def get_question_for_generation():
    # Prioritize by generated_count: 0s first, then 1s, then 2s
    # Try to get questions with generated_count = 0 first
    responses = await QuestionDocument.find(
        QuestionDocument.source == "khan",
        QuestionDocument.generated_count == 0
    ).project(ProjectionWithID).to_list()
    
    if not responses:
        # If no 0s, try 1s
        responses = await QuestionDocument.find(
            QuestionDocument.source == "khan",
            QuestionDocument.generated_count == 1
        ).project(ProjectionWithID).to_list()
    
    if not responses:
        # If no 1s, try 2s
        responses = await QuestionDocument.find(
            QuestionDocument.source == "khan",
            QuestionDocument.generated_count == 2
        ).project(ProjectionWithID).to_list()
    
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
    # Increment generated_count instead of setting it to 1
    source_question.generated_count = len(source_question.generated)
    await source_question.save()

    return JSONResponse(content={"message": "Success"}, status_code=201)


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

async def _remove_generated_from_source(question_doc_id: ObjectId) -> bool:
    """
    Helper to detach a generated question reference from its source question
    and keep generated_count in sync with pending items.
    """
    from beanie import Link

    source_questions = await QuestionDocument.find(
        GT(QuestionDocument.generated_count, 0)
    ).to_list()

    for source_question in source_questions:
        await source_question.fetch_all_links()
        new_generated_list = []
        removed = False

        for generated_entry in source_question.generated:
            if isinstance(generated_entry, Link):
                entry_id = generated_entry.ref.id
            else:
                entry_id = generated_entry.id

            if entry_id == question_doc_id:
                removed = True
            else:
                new_generated_list.append(generated_entry)

        if removed:
            source_question.generated = new_generated_list
            source_question.generated_count = len(new_generated_list)
            await source_question.save()
            print(
                f"Detached generated question {question_doc_id} from source {source_question.id}. "
                f"Pending count is now {source_question.generated_count}"
            )
            return True

    return False


@router.post("/approve-question/{question_id}")
async def approve_question(question_id: str):
    try:
        # Find the GeneratedQuestionDocument by its _id
        question_doc = await GeneratedQuestionDocument.get(ObjectId(question_id))

        if not question_doc:
            raise HTTPException(status_code=404, detail="Generated question not found")

        # Set human_approved to True
        question_doc.human_approved = True
        await question_doc.save()

        await _remove_generated_from_source(question_doc.id)

        return JSONResponse(content={"message": "Question approved successfully"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve question: {e}")


@router.post("/reject-question/{question_id}")
async def reject_question(question_id: str):
    try:
        # Find the GeneratedQuestionDocument by its _id
        question_doc = await GeneratedQuestionDocument.get(ObjectId(question_id))

        if not question_doc:
            raise HTTPException(status_code=404, detail="Generated question not found")

        question_doc_id = question_doc.id if hasattr(question_doc, "id") else ObjectId(question_id)
        await _remove_generated_from_source(question_doc_id)

        # Delete the generated question document
        await question_doc.delete()

        return JSONResponse(content={"message": "Question rejected and deleted successfully"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject question: {e}")
