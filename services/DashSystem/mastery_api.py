"""
Mastery Tracking API
Tracks user progress on focus topics and learning paths
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from managers.mongodb_manager import mongo_db

router = APIRouter()

class TopicProgress(BaseModel):
    topic: str
    questions_answered: int
    questions_correct: int
    total_needed: int
    mastered: bool
    last_updated: Optional[datetime] = None

class UpdateProgressRequest(BaseModel):
    user_id: str
    topic: str
    correct: bool
    question_id: str

class GetProgressRequest(BaseModel):
    user_id: str
    subject: str
    grade: str

@router.post("/api/mastery/update")
async def update_mastery_progress(request: UpdateProgressRequest):
    """
    Update mastery progress after answering a question
    """
    try:
        # Get or create user's mastery record
        mastery_record = mongo_db.mastery_progress.find_one({
            "user_id": request.user_id,
            "topic": request.topic
        })

        if not mastery_record:
            # Create new record
            mastery_record = {
                "user_id": request.user_id,
                "topic": request.topic,
                "questions_answered": 0,
                "questions_correct": 0,
                "total_needed": 10,
                "mastered": False,
                "question_history": [],
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow()
            }

        # Update progress
        mastery_record["questions_answered"] += 1
        if request.correct:
            mastery_record["questions_correct"] += 1

        # Add to history
        if "question_history" not in mastery_record:
            mastery_record["question_history"] = []

        mastery_record["question_history"].append({
            "question_id": request.question_id,
            "correct": request.correct,
            "answered_at": datetime.utcnow()
        })

        # Check mastery (8 out of 10 correct)
        if mastery_record["questions_answered"] >= 10:
            if mastery_record["questions_correct"] >= 8:
                mastery_record["mastered"] = True
                mastery_record["mastered_at"] = datetime.utcnow()

        mastery_record["last_updated"] = datetime.utcnow()

        # Save to MongoDB
        mongo_db.mastery_progress.update_one(
            {
                "user_id": request.user_id,
                "topic": request.topic
            },
            {"$set": mastery_record},
            upsert=True
        )

        return {
            "success": True,
            "topic": request.topic,
            "questions_answered": mastery_record["questions_answered"],
            "questions_correct": mastery_record["questions_correct"],
            "mastered": mastery_record["mastered"],
            "progress_percent": round((mastery_record["questions_correct"] / mastery_record["total_needed"]) * 100)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update progress: {str(e)}")


@router.post("/api/mastery/progress")
async def get_mastery_progress(request: GetProgressRequest):
    """
    Get user's mastery progress for all topics
    """
    try:
        # Get all mastery records for user
        records = list(mongo_db.mastery_progress.find({
            "user_id": request.user_id
        }))

        # Convert to response format
        progress = []
        for record in records:
            progress.append({
                "topic": record["topic"],
                "questions_answered": record["questions_answered"],
                "questions_correct": record["questions_correct"],
                "total_needed": record.get("total_needed", 10),
                "mastered": record.get("mastered", False),
                "last_updated": record.get("last_updated", record.get("created_at"))
            })

        return {
            "user_id": request.user_id,
            "subject": request.subject,
            "grade": request.grade,
            "topics": progress,
            "total_topics": len(progress),
            "mastered_topics": len([p for p in progress if p["mastered"]])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/api/mastery/stats/{user_id}")
async def get_mastery_stats(user_id: str):
    """
    Get overall mastery statistics for user
    """
    try:
        records = list(mongo_db.mastery_progress.find({"user_id": user_id}))

        total_topics = len(records)
        mastered_topics = len([r for r in records if r.get("mastered", False)])
        total_questions = sum(r["questions_answered"] for r in records)
        total_correct = sum(r["questions_correct"] for r in records)

        return {
            "user_id": user_id,
            "total_topics": total_topics,
            "mastered_topics": mastered_topics,
            "in_progress_topics": total_topics - mastered_topics,
            "total_questions_answered": total_questions,
            "total_correct_answers": total_correct,
            "overall_accuracy": round((total_correct / total_questions * 100) if total_questions > 0 else 0, 1),
            "mastery_percentage": round((mastered_topics / total_topics * 100) if total_topics > 0 else 0)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.delete("/api/mastery/reset/{user_id}")
async def reset_mastery_progress(user_id: str):
    """
    Reset all mastery progress for a user (for testing)
    """
    try:
        result = mongo_db.mastery_progress.delete_many({"user_id": user_id})
        return {
            "success": True,
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset progress: {str(e)}")
