"""
Onboarding API Service - Duolingo/Kahoot-style onboarding for Math
Enhanced with DASH system integration for adaptive questions
"""
import os
import sys
import time
import logging
import random
import re
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from shared.auth_middleware import get_current_user
from managers.mongodb_manager import mongo_db
from managers.user_manager import UserManager
from services.DashSystem.dash_system import DASHSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Onboarding Service API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Get port from environment or default
PORT = int(os.getenv("ONBOARDING_SERVICE_PORT", "8004"))

# Initialize user manager and DASH system
user_manager = UserManager()
try:
    dash_system = DASHSystem()
    logger.info("[ONBOARDING] DASH system initialized successfully")
except Exception as e:
    logger.error(f"[ONBOARDING] Failed to initialize DASH system: {e}")
    logger.warning("[ONBOARDING] Onboarding will use fallback questions only")
    dash_system = None

# Onboarding configuration
ONBOARDING_QUESTION_COUNT = 8  # Number of questions in onboarding

# Onboarding question data models
class OnboardingQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str  # "multiple_choice", "number_input", "true_false", "perseus"
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str
    skill_level: str  # "beginner", "intermediate", "advanced"
    points: int = 10
    skill_ids: Optional[List[str]] = None
    perseus_data: Optional[Dict] = None  # Full Perseus data if available

class OnboardingAnswer(BaseModel):
    question_id: str
    answer: str
    time_taken_seconds: float

class OnboardingProgress(BaseModel):
    current_question_index: int
    total_questions: int
    correct_answers: int
    total_points: int
    completed: bool
    achievements: List[str]

def extract_text_from_perseus(perseus_data: Dict) -> str:
    """Extract question text from Perseus data"""
    try:
        # Try to get question text from various possible locations
        question_data = perseus_data.get('question', {})
        if isinstance(question_data, dict):
            # Try content field
            content = question_data.get('content', '')
            if content:
                # Remove HTML tags
                import re
                text = re.sub(r'<[^>]+>', '', content)
                return text.strip()[:200]  # Limit length
        return "Solve this math problem"
    except Exception as e:
        logger.warning(f"Error extracting text from Perseus: {e}")
        return "Solve this math problem"

def extract_answer_from_perseus(perseus_data: Dict) -> str:
    """Extract correct answer from Perseus data"""
    try:
        answer_area = perseus_data.get('answerArea', {})
        if isinstance(answer_area, dict):
            # Try to get answer from various possible locations
            options = answer_area.get('options', [])
            if options:
                # Find correct option
                for opt in options:
                    if opt.get('correct', False):
                        return str(opt.get('content', opt.get('value', '')))
            # Try calculator answer
            calculator = answer_area.get('calculator', {})
            if calculator:
                return str(calculator.get('answer', ''))
        return ""
    except Exception as e:
        logger.warning(f"Error extracting answer from Perseus: {e}")
        return ""

def convert_dash_question_to_onboarding(dash_question, perseus_data: Optional[Dict] = None) -> Dict:
    """Convert a DASH question to onboarding format"""
    question_id = dash_question.question_id
    skill_ids = dash_question.skill_ids
    
    # Get skill name for explanation
    skill_name = "math"
    if skill_ids and dash_system is not None and hasattr(dash_system, 'skills') and dash_system.skills:
        if skill_ids[0] in dash_system.skills:
            skill_name = dash_system.skills[skill_ids[0]].name
    
    # If we have Perseus data, use it
    if perseus_data:
        question_text = extract_text_from_perseus(perseus_data)
        correct_answer = extract_answer_from_perseus(perseus_data)
        
        # Generate options if multiple choice
        options = None
        answer_area = perseus_data.get('answerArea', {})
        if isinstance(answer_area, dict):
            answer_options = answer_area.get('options', [])
            if len(answer_options) >= 2:
                options = [str(opt.get('content', opt.get('value', ''))) for opt in answer_options[:4]]
                question_type = "multiple_choice"
            else:
                question_type = "number_input"
        else:
            question_type = "number_input"
        
        if not correct_answer:
            # Fallback: use question content as text
            correct_answer = "See explanation"
        
        return {
            "question_id": question_id,
            "question_text": question_text or "Solve this math problem",
            "question_type": question_type,
            "options": options,
            "correct_answer": correct_answer,
            "explanation": f"Great work! You're mastering {skill_name}!",
            "skill_level": "beginner",
            "points": 10,
            "skill_ids": skill_ids,
            "perseus_data": perseus_data
        }
    else:
        # Fallback to simple format
        return {
            "question_id": question_id,
            "question_text": f"Practice {skill_name}",
            "question_type": "number_input",
            "options": None,
            "correct_answer": "",
            "explanation": f"Excellent! You're learning {skill_name}!",
            "skill_level": "beginner",
            "points": 10,
            "skill_ids": skill_ids
        }

def generate_onboarding_questions_from_dash(user_id: str, user_profile) -> List[Dict]:
    """Generate adaptive onboarding questions using DASH system"""
    try:
        # Get user's grade to determine appropriate questions
        current_grade = user_profile.current_grade
        current_time = time.time()
        
        # Check if DASH system is properly initialized
        if not dash_system or not hasattr(dash_system, 'skills') or not dash_system.skills:
            logger.warning(f"[ONBOARDING] DASH system not properly initialized, using fallback questions")
            return ONBOARDING_QUESTIONS_FALLBACK[:ONBOARDING_QUESTION_COUNT]
        
        # Get questions from DASH system (adaptive based on grade)
        onboarding_questions = []
        selected_question_ids = []
        
        # Get questions progressively - start easier, adapt based on performance
        for i in range(ONBOARDING_QUESTION_COUNT):
            try:
                # Use DASH to get next question
                next_question = dash_system.get_next_question_flexible(
                    user_id,
                    current_time,
                    exclude_question_ids=selected_question_ids,
                    force_grade_range=True  # Allow grade-appropriate questions
                )
                
                if not next_question:
                    # If no more questions, break and use fallback
                    logger.info(f"[ONBOARDING] No more DASH questions available after {i} questions")
                    break
                
                # Try to load Perseus data for this question
                perseus_data = None
                try:
                    from services.DashSystem.dash_api import load_perseus_items_for_dash_questions_from_mongodb
                    perseus_items = load_perseus_items_for_dash_questions_from_mongodb([next_question])
                    if perseus_items:
                        perseus_data = perseus_items[0]
                except Exception as e:
                    logger.warning(f"Could not load Perseus data for question {next_question.question_id}: {e}")
                
                # Convert to onboarding format
                onboarding_q = convert_dash_question_to_onboarding(next_question, perseus_data)
                onboarding_questions.append(onboarding_q)
                selected_question_ids.append(next_question.question_id)
            except Exception as question_error:
                logger.warning(f"[ONBOARDING] Error getting question {i+1}: {question_error}")
                # Continue to next question or break if too many errors
                if i == 0:
                    # If first question fails, use fallback
                    break
                continue
        
        # If we don't have enough questions, fill with fallback questions
        while len(onboarding_questions) < ONBOARDING_QUESTION_COUNT:
            # Use simple fallback questions
            fallback_q = {
                "question_id": f"onboard_fallback_{len(onboarding_questions) + 1}",
                "question_text": "What is 5 + 3?",
                "question_type": "multiple_choice",
                "options": ["6", "7", "8", "9"],
                "correct_answer": "8",
                "explanation": "Great! 5 + 3 = 8. You're getting the hang of addition!",
                "skill_level": "beginner",
                "points": 10,
                "skill_ids": []
            }
            onboarding_questions.append(fallback_q)
        
        return onboarding_questions[:ONBOARDING_QUESTION_COUNT]
        
    except Exception as e:
        logger.error(f"Error generating onboarding questions from DASH: {e}", exc_info=True)
        # Fallback to predefined questions
        return ONBOARDING_QUESTIONS_FALLBACK[:ONBOARDING_QUESTION_COUNT]

# Fallback questions if DASH fails
ONBOARDING_QUESTIONS_FALLBACK = [
    {
        "question_id": "onboard_1",
        "question_text": "What is 5 + 3?",
        "question_type": "multiple_choice",
        "options": ["6", "7", "8", "9"],
        "correct_answer": "8",
        "explanation": "Great! 5 + 3 = 8. You're getting the hang of addition!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_2",
        "question_text": "What is 10 - 4?",
        "question_type": "multiple_choice",
        "options": ["4", "5", "6", "7"],
        "correct_answer": "6",
        "explanation": "Excellent! 10 - 4 = 6. Subtraction is the opposite of addition!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_3",
        "question_text": "What is 2 × 4?",
        "question_type": "multiple_choice",
        "options": ["6", "7", "8", "9"],
        "correct_answer": "8",
        "explanation": "Perfect! 2 × 4 = 8. Multiplication is repeated addition!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_4",
        "question_text": "What is 12 ÷ 3?",
        "question_type": "multiple_choice",
        "options": ["3", "4", "5", "6"],
        "correct_answer": "4",
        "explanation": "Awesome! 12 ÷ 3 = 4. Division is the opposite of multiplication!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_5",
        "question_text": "Which number is greater: 15 or 12?",
        "question_type": "multiple_choice",
        "options": ["12", "15", "They are equal", "Cannot determine"],
        "correct_answer": "15",
        "explanation": "Correct! 15 is greater than 12. You're comparing numbers like a pro!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_6",
        "question_text": "What is 7 + 8?",
        "question_type": "multiple_choice",
        "options": ["13", "14", "15", "16"],
        "correct_answer": "15",
        "explanation": "Great job! 7 + 8 = 15. Keep up the excellent work!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_7",
        "question_text": "What is 20 - 7?",
        "question_type": "multiple_choice",
        "options": ["11", "12", "13", "14"],
        "correct_answer": "13",
        "explanation": "Perfect! 20 - 7 = 13. You're mastering subtraction!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_8",
        "question_text": "What is 3 × 5?",
        "question_type": "multiple_choice",
        "options": ["12", "13", "14", "15"],
        "correct_answer": "15",
        "explanation": "Excellent! 3 × 5 = 15. Multiplication is getting easier!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_9",
        "question_text": "What is 18 ÷ 2?",
        "question_type": "multiple_choice",
        "options": ["7", "8", "9", "10"],
        "correct_answer": "9",
        "explanation": "Awesome! 18 ÷ 2 = 9. Division skills are improving!",
        "skill_level": "beginner",
        "points": 10
    },
    {
        "question_id": "onboard_10",
        "question_text": "What is 6 + 9?",
        "question_type": "multiple_choice",
        "options": ["14", "15", "16", "17"],
        "correct_answer": "15",
        "explanation": "Fantastic! 6 + 9 = 15. You've completed the onboarding! 🎉",
        "skill_level": "beginner",
        "points": 10
    }
]

# Store generated questions per user (in-memory cache)
user_onboarding_questions: Dict[str, List[Dict]] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "onboarding"}

@app.get("/api/onboarding/questions", response_model=List[OnboardingQuestion])
async def get_onboarding_questions(request: Request):
    """Get adaptive onboarding questions using DASH system"""
    try:
        # Verify authentication
        user_id = get_current_user(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Check if we already generated questions for this user
        if user_id in user_onboarding_questions:
            questions = user_onboarding_questions[user_id]
        else:
            # Load user profile
            user_profile = user_manager.load_user(user_id)
            if not user_profile:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Generate adaptive questions from DASH
            try:
                if dash_system is None:
                    logger.warning("[ONBOARDING] DASH system not available, using fallback questions")
                    questions = ONBOARDING_QUESTIONS_FALLBACK[:ONBOARDING_QUESTION_COUNT]
                else:
                    questions = generate_onboarding_questions_from_dash(user_id, user_profile)
                # Cache the questions
                user_onboarding_questions[user_id] = questions
                logger.info(f"[ONBOARDING] Generated {len(questions)} questions for user {user_id} (grade: {user_profile.current_grade})")
            except Exception as e:
                logger.warning(f"[ONBOARDING] DASH question generation failed, using fallback: {e}", exc_info=True)
                questions = ONBOARDING_QUESTIONS_FALLBACK[:ONBOARDING_QUESTION_COUNT]
        
        # Convert to response model
        try:
            return [OnboardingQuestion(**q) for q in questions]
        except Exception as conversion_error:
            logger.error(f"[ERROR] Error converting questions to response model: {conversion_error}")
            logger.error(f"[ERROR] Question data: {questions[:1] if questions else 'No questions'}")
            # Try to return fallback questions if conversion fails
            return [OnboardingQuestion(**q) for q in ONBOARDING_QUESTIONS_FALLBACK[:ONBOARDING_QUESTION_COUNT]]
    except HTTPException:
        # Re-raise HTTP exceptions (401, 404, etc.)
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error getting onboarding questions: {e}", exc_info=True)
        # Return fallback questions instead of raising error
        try:
            return [OnboardingQuestion(**q) for q in ONBOARDING_QUESTIONS_FALLBACK[:ONBOARDING_QUESTION_COUNT]]
        except Exception as fallback_error:
            logger.error(f"[ERROR] Even fallback questions failed: {fallback_error}")
            raise HTTPException(status_code=500, detail=f"Failed to load questions: {str(e)}")

@app.get("/api/onboarding/progress")
async def get_onboarding_progress(request: Request):
    """Get user's onboarding progress"""
    try:
        user_id = get_current_user(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_profile = user_manager.load_user(user_id)
        
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get onboarding data from user profile (handle None student_notes)
        if not hasattr(user_profile, 'student_notes') or user_profile.student_notes is None:
            user_profile.student_notes = {}
        
        onboarding_data = user_profile.student_notes.get('onboarding', {})
        current_index = onboarding_data.get('current_question_index', 0)
        correct_answers = onboarding_data.get('correct_answers', 0)
        total_points = onboarding_data.get('total_points', 0)
        completed = onboarding_data.get('completed', False)
        achievements = onboarding_data.get('achievements', [])
        
        # Get total questions count (from cache or fallback)
        total_questions = ONBOARDING_QUESTION_COUNT
        if user_id in user_onboarding_questions:
            total_questions = len(user_onboarding_questions[user_id])
        
        progress = OnboardingProgress(
            current_question_index=current_index,
            total_questions=total_questions,
            correct_answers=correct_answers,
            total_points=total_points,
            completed=completed,
            achievements=achievements if isinstance(achievements, list) else []
        )
        
        return progress
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error getting onboarding progress: {e}", exc_info=True)
        # Return default progress instead of failing
        return OnboardingProgress(
            current_question_index=0,
            total_questions=ONBOARDING_QUESTION_COUNT,
            correct_answers=0,
            total_points=0,
            completed=False,
            achievements=[]
        )

@app.post("/api/onboarding/answer")
async def submit_answer(answer: OnboardingAnswer, request: Request):
    """Submit an answer to an onboarding question"""
    try:
        user_id = get_current_user(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_profile = user_manager.load_user(user_id)
        
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find the question (from cache or fallback)
        question = None
        try:
            if user_id in user_onboarding_questions:
                question = next((q for q in user_onboarding_questions[user_id] if q.get('question_id') == answer.question_id), None)
        except Exception as e:
            logger.warning(f"Error searching cached questions: {e}")
        
        if not question:
            # Try fallback questions
            try:
                question = next((q for q in ONBOARDING_QUESTIONS_FALLBACK if q.get('question_id') == answer.question_id), None)
            except Exception as e:
                logger.warning(f"Error searching fallback questions: {e}")
        
        if not question:
            logger.error(f"[ERROR] Question not found: question_id={answer.question_id}, user_id={user_id}")
            logger.error(f"[ERROR] Available question IDs in cache: {[q.get('question_id') for q in user_onboarding_questions.get(user_id, [])]}")
            raise HTTPException(status_code=404, detail=f"Question not found: {answer.question_id}")
        
        # If this is a DASH question, update skill states
        if question.get('skill_ids') and answer.answer and dash_system is not None:
            try:
                # Record answer in DASH system (calculate is_correct first)
                correct_answer = str(question.get('correct_answer', '')).strip()
                user_answer = str(answer.answer).strip() if answer.answer else ''
                dash_is_correct = user_answer == correct_answer
                dash_system.record_question_attempt(
                    user_profile,
                    answer.question_id,
                    question.get('skill_ids', []),
                    dash_is_correct,
                    answer.time_taken_seconds
                )
            except Exception as e:
                logger.warning(f"Could not update DASH skill states: {e}", exc_info=True)
        
        # Check if answer is correct (handle None/empty values)
        correct_answer = str(question.get('correct_answer', '')).strip()
        user_answer = str(answer.answer).strip() if answer.answer else ''
        is_correct = user_answer == correct_answer
        
        # Get or initialize onboarding data (handle None student_notes)
        if not hasattr(user_profile, 'student_notes') or user_profile.student_notes is None:
            user_profile.student_notes = {}
        
        if 'onboarding' not in user_profile.student_notes:
            user_profile.student_notes['onboarding'] = {
                'current_question_index': 0,
                'correct_answers': 0,
                'total_points': 0,
                'completed': False,
                'answers': [],
                'achievements': []
            }
        
        onboarding_data = user_profile.student_notes['onboarding']
        
        # Update progress
        if is_correct:
            onboarding_data['correct_answers'] += 1
            onboarding_data['total_points'] += question.get('points', 10)
        
        # Record the answer
        onboarding_data['answers'].append({
            'question_id': answer.question_id,
            'answer': str(answer.answer) if answer.answer is not None else '',
            'is_correct': is_correct,
            'time_taken_seconds': answer.time_taken_seconds
        })
        
        # Get total questions count
        total_questions = ONBOARDING_QUESTION_COUNT
        if user_id in user_onboarding_questions:
            total_questions = len(user_onboarding_questions[user_id])
        
        # Move to next question
        current_index = onboarding_data['current_question_index']
        if current_index < total_questions - 1:
            onboarding_data['current_question_index'] = current_index + 1
        else:
            # Completed onboarding
            onboarding_data['completed'] = True
            onboarding_data['current_question_index'] = total_questions
            
            # Award achievements
            achievements = []
            if onboarding_data['correct_answers'] == total_questions:
                achievements.append("perfect_score")
            if onboarding_data['correct_answers'] >= total_questions * 0.8:
                achievements.append("math_master")
            if answer.time_taken_seconds < 5:
                achievements.append("speed_demon")
            
            onboarding_data['achievements'] = list(set(onboarding_data.get('achievements', []) + achievements))
        
        # Save user profile
        try:
            user_manager.save_user(user_profile)
        except Exception as save_error:
            logger.error(f"[ERROR] Failed to save user profile: {save_error}")
            # Continue anyway - we'll return the response even if save fails
        
        logger.info(f"[ONBOARDING] User {user_id} answered question {answer.question_id}: {'correct' if is_correct else 'incorrect'}")
        
        return {
            "is_correct": is_correct,
            "explanation": question.get('explanation', 'Good job!'),
            "points_earned": question.get('points', 10) if is_correct else 0,
            "progress": {
                "current_question_index": onboarding_data.get('current_question_index', 0),
                "total_questions": total_questions,
                "correct_answers": onboarding_data.get('correct_answers', 0),
                "total_points": onboarding_data.get('total_points', 0),
                "completed": onboarding_data.get('completed', False)
            },
            "achievements": onboarding_data.get('achievements', [])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] Error submitting answer: {e}", exc_info=True)
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[ERROR] Full traceback: {error_details}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to submit answer: {str(e)}. Check server logs for details."
        )

@app.post("/api/onboarding/complete")
async def complete_onboarding(request: Request):
    """Mark onboarding as complete"""
    try:
        user_id = get_current_user(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_profile = user_manager.load_user(user_id)
        
        if not user_profile:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Mark onboarding as complete (handle None student_notes)
        if not hasattr(user_profile, 'student_notes') or user_profile.student_notes is None:
            user_profile.student_notes = {}
        
        if 'onboarding' not in user_profile.student_notes:
            user_profile.student_notes['onboarding'] = {}
        
        user_profile.student_notes['onboarding']['completed'] = True
        user_profile.student_notes['onboarding']['completed_at'] = time.time()
        
        user_manager.save_user(user_profile)
        
        logger.info(f"[ONBOARDING] User {user_id} completed onboarding")
        
        return {"status": "completed", "message": "Onboarding completed successfully!"}
    except Exception as e:
        logger.error(f"[ERROR] Error completing onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/onboarding/status")
async def get_onboarding_status(request: Request):
    """Check if user has completed onboarding"""
    try:
        user_id = get_current_user(request)
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_profile = user_manager.load_user(user_id)
        
        if not user_profile:
            return {"completed": False, "required": True}
        
        # Handle None student_notes
        if not hasattr(user_profile, 'student_notes') or user_profile.student_notes is None:
            user_profile.student_notes = {}
        
        onboarding_data = user_profile.student_notes.get('onboarding', {})
        completed = onboarding_data.get('completed', False)
        
        # Get total questions count
        total_questions = ONBOARDING_QUESTION_COUNT
        if user_id in user_onboarding_questions:
            total_questions = len(user_onboarding_questions[user_id])
        
        return {
            "completed": completed,
            "required": True,
            "progress": {
                "current_question_index": onboarding_data.get('current_question_index', 0),
                "total_questions": total_questions,
                "correct_answers": onboarding_data.get('correct_answers', 0)
            }
        }
    except Exception as e:
        logger.error(f"[ERROR] Error checking onboarding status: {e}")
        return {"completed": False, "required": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)

