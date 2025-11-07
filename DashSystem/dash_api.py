import time
import sys
import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import random

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from DashSystem.dash_system import DASHSystem, Question, GradeLevel
from auth.auth_routes import get_current_user
from db.perseus_repository import get_random_questions
from utils.perseus_screenshot import capture_perseus_question
from utils.gamification import calculate_xp_earned, award_xp_and_update_gamification
from loguru import logger
from typing import Optional

app = FastAPI()
dash_system = DASHSystem()

# Temporary in-memory storage for questions being screenshotted
_temp_questions = {}

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows the React frontend to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnswerSubmission(BaseModel):
    question_id: str
    skill_ids: List[str]
    is_correct: bool
    response_time_seconds: float = 0.0


class SkillDetail(BaseModel):
    skill_id: str
    name: str
    memory_strength: float
    is_direct: bool  # Whether this skill was directly tested

@app.get("/next-question/{user_id}")
def get_next_question(user_id: str, grade: Optional[str] = None) -> Dict[str, Any]:
    """
    Gets the next recommended Perseus-formatted question for a given user.
    Also captures a screenshot of the rendered question for visual AI processing.

    Args:
        user_id: User identifier
        grade: Optional grade level (e.g., "5", "GRADE_5", "K") for new users
    """
    # Convert grade string to GradeLevel enum if provided
    grade_level_enum: Optional[GradeLevel] = None
    if grade:
        try:
            # Normalize grade input (e.g., "grade_7" -> "GRADE_7", "7" -> "GRADE_7")
            grade_upper = grade.upper()
            if not grade_upper.startswith("GRADE_"):
                # Accommodate inputs like "7" or "K"
                if grade_upper.isdigit() and grade_upper != '0':
                    grade_upper = f"GRADE_{grade_upper}"

            grade_level_enum = GradeLevel[grade_upper]
            logger.info(f"Parsed grade level: {grade_level_enum.name}")
        except KeyError:
            valid_grades = [g.name for g in GradeLevel]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid grade level '{grade}'. Valid options are: {valid_grades}"
            )

    # Ensure the user exists and is loaded, potentially initializing skills based on grade
    dash_system.load_user_or_create(user_id, grade_level=grade_level_enum)

    # Get a Perseus question from MongoDB
    perseus_questions = get_random_questions(sample_size=1)

    if not perseus_questions:
        raise HTTPException(status_code=404, detail="No Perseus questions available.")

    perseus_question = perseus_questions[0]

    # Generate a unique question ID for tracking
    question_id = f"perseus_{random.randint(10000, 99999)}"

    # For now, assign to a default skill (you can map Perseus questions to skills later)
    skill_ids = ["counting_1_10"]  # Default skill

    # Screenshot capture disabled for faster loading (Gemini sees screen via MediaMixer anyway)
    # If you need screenshots, uncomment this block:
    screenshot_path = None
    # try:
    #     screenshots_dir = Path(__file__).parent.parent / "question_screenshots"
    #     screenshots_dir.mkdir(exist_ok=True)
    #
    #     screenshot_file = screenshots_dir / f"{question_id}.png"
    #
    #     logger.info(f"Capturing screenshot for question {question_id}...")
    #     screenshot_path = capture_perseus_question(
    #         perseus_content=perseus_question,
    #         output_path=screenshot_file
    #     )
    #
    #     if screenshot_path:
    #         logger.info(f"✓ Screenshot captured: {screenshot_path}")
    #     else:
    #         logger.warning(f"Screenshot capture failed for question {question_id}")
    #
    # except Exception as e:
    #     logger.error(f"Error capturing screenshot: {e}")
    #     # Don't fail the request if screenshot fails

    # Return in the format the frontend and Pipecat expect
    return {
        "question_id": question_id,
        "skill_ids": skill_ids,
        "content": perseus_question,  # Full Perseus object (question, answerArea, hints)
        "difficulty": 0.5,
        "screenshot_path": screenshot_path  # Path to rendered question screenshot
    }


@app.post("/submit-answer/{user_id}")
def submit_answer(user_id: str, submission: AnswerSubmission):
    """
    Submit an answer and update skill states in MongoDB.
    Also awards XP and updates gamification stats.
    Returns updated skill details and gamification info.
    """
    # Ensure the user exists
    user_profile = dash_system.user_manager.get_or_create_user(
        user_id,
        list(dash_system.skills.keys())
    )

    # Record the question attempt and update skills
    affected_skills = dash_system.record_question_attempt(
        user_profile=user_profile,
        question_id=submission.question_id,
        skill_ids=submission.skill_ids,
        is_correct=submission.is_correct,
        response_time_seconds=submission.response_time_seconds
    )

    # Prepare skill details for response
    skill_details = []
    for skill_id in affected_skills:
        if skill_id in user_profile.skill_states:
            skill_state = user_profile.skill_states[skill_id]
            skill = dash_system.skills.get(skill_id)

            skill_details.append(SkillDetail(
                skill_id=skill_id,
                name=skill.name if skill else skill_id,
                memory_strength=skill_state.memory_strength,
                is_direct=skill_id in submission.skill_ids
            ))

    # Award XP and update gamification stats (for auth user)
    gamification_update = None
    if submission.is_correct:
        try:
            from db.auth_repository import get_user_by_id

            # Get user's current streak for XP calculation
            auth_user = get_user_by_id(user_id)
            if auth_user:
                current_streak = auth_user.get('streak_count', 0)

                # Calculate XP (assume first try for now - could track this later)
                xp_earned = calculate_xp_earned(
                    is_correct=True,
                    is_first_try=True,
                    streak_count=current_streak
                )

                # Award XP and update stats
                gamification_update = award_xp_and_update_gamification(user_id, xp_earned)
                logger.info(f"Awarded {xp_earned} XP to user {user_id}")
        except Exception as e:
            logger.error(f"Error updating gamification for user {user_id}: {e}")
            # Don't fail the request if gamification fails

    return {
        "success": True,
        "is_correct": submission.is_correct,
        "skill_details": skill_details,
        "affected_skills_count": len(affected_skills),
        "gamification": gamification_update  # Include gamification stats in response
    }


@app.get("/skill-states/{user_id}")
def get_skill_states(user_id: str):
    """
    Get all skill states for a user.
    Used for the Learning Path sidebar.
    """
    user_profile = dash_system.user_manager.get_or_create_user(
        user_id,
        list(dash_system.skills.keys())
    )

    skill_states = []
    for skill_id, skill in dash_system.skills.items():
        state = user_profile.skill_states.get(skill_id)
        if state:
            skill_states.append({
                "skill_id": skill_id,
                "name": skill.name,
                "grade_level": skill.grade_level.name,
                "memory_strength": state.memory_strength,
                "practice_count": state.practice_count,
                "correct_count": state.correct_count,
                "prerequisites": skill.prerequisites,
                "is_locked": not dash_system.are_prerequisites_met(user_id, skill_id, time.time())
            })

    return {"skills": skill_states}


@app.get("/get-question/{question_id}")
def get_question(question_id: str) -> Dict[str, Any]:
    """
    Get a question by temporary ID (used for screenshot rendering).
    """
    if question_id not in _temp_questions:
        raise HTTPException(status_code=404, detail="Question not found or expired")

    return _temp_questions[question_id]


@app.post("/store-temp-question")
def store_temp_question(question_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Temporarily store a question for screenshot rendering.
    Returns a temporary ID that expires after use.
    """
    temp_id = f"temp_{random.randint(100000, 999999)}"
    _temp_questions[temp_id] = question_data
    return {"temp_id": temp_id}


@app.delete("/delete-temp-question/{question_id}")
def delete_temp_question(question_id: str):
    """
    Clean up a temporary question after screenshot is captured.
    """
    if question_id in _temp_questions:
        del _temp_questions[question_id]
        return {"success": True}
    return {"success": False}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
