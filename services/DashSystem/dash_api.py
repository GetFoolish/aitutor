import time
import sys
import os
import json
import logging
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.DashSystem.dash_system import DASHSystem, Question, GradeLevel
from shared.auth_middleware import get_current_user
from shared.cache_middleware import CacheControlMiddleware
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS

from shared.logging_config import get_logger

logger = get_logger(__name__)


app = FastAPI()
dash_system = None  # Initialize as None, will be set in startup event

# Configure CORS with secure origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

# Helper function to ensure DASH system is initialized
def ensure_dash_system():
    """Ensure DASH system is initialized before use"""
    if dash_system is None:
        raise HTTPException(status_code=503, detail="DASHSystem not initialized")

# Startup event to initialize DASH system
@app.on_event("startup")
async def startup_event():
    """Initialize DASHSystem on startup"""
    global dash_system
    logger.info("Initializing DASHSystem...")
    try:
        dash_system = DASHSystem()
        logger.info(f"DASHSystem initialized: {len(dash_system.skills)} skills, {len(dash_system.question_index)} questions in index")
    except Exception as e:
        logger.error(f"Failed to initialize DASHSystem: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
# Performance Monitoring
from shared.timing_middleware import UnpluggedTimingMiddleware
app.add_middleware(UnpluggedTimingMiddleware)

# Cache Control
app.add_middleware(CacheControlMiddleware)

# Perseus item model matching frontend expectations
class PerseusQuestion(BaseModel):
    question: dict = Field(description="The question data")
    answerArea: dict = Field(description="The answer area")
    hints: List = Field(description="List of question hints")
    itemDataVersion: Optional[dict] = Field(default=None, description="Perseus item data version")
    dash_metadata: Optional[dict] = Field(default=None, description="DASH metadata for tracking")
    
    class Config:
        extra = "allow"  # Allow additional fields that aren't in the model

# Health check endpoint for startup verification
@app.get("/health")
def health_check():
    """Health check endpoint for startup verification"""
    from fastapi import Response
    if dash_system is None:
        return Response(
            content='{"status": "initializing", "ready": false}',
            media_type="application/json",
            status_code=503
        )
    return {
        "status": "ready",
        "ready": True,
        "skills_count": len(dash_system.skills),
        "questions_count": len(dash_system.question_index)
    }


def load_perseus_items_for_dash_questions_from_mongodb(
    dash_questions: List[Question]
) -> List[Dict]:
    """Load Perseus items from questions_db.questions collection matching DASH-selected questions.

    OPTIMIZED: Uses batch query with $in instead of one query per question.
    """
    from managers.mongodb_manager import mongo_db
    import json

    if not dash_questions:
        return []

    # Build lookup map for DASH metadata
    dash_lookup = {q.question_id: q for q in dash_questions}
    question_ids = list(dash_lookup.keys())

    # BATCH QUERY: Fetch all questions in one MongoDB call from questions_db
    question_docs = list(mongo_db.questions.find(
        {"question_id": {"$in": question_ids}}
    ))

    # Build lookup for question docs
    question_lookup = {doc.get('question_id'): doc for doc in question_docs}

    # Collect all unique unit_ids, lesson_ids, exercise_ids for batch fetching
    unit_ids = set()
    lesson_ids = set()
    exercise_ids = set()
    for doc in question_docs:
        if doc.get('unit_id'):
            unit_ids.add(doc.get('unit_id'))
        if doc.get('lesson_id'):
            lesson_ids.add(doc.get('lesson_id'))
        if doc.get('exercise_id'):
            exercise_ids.add(doc.get('exercise_id'))

    # BATCH QUERY: Fetch units, lessons, exercises
    unit_docs = list(mongo_db.units.find({"unit_id": {"$in": list(unit_ids)}})) if unit_ids else []
    lesson_docs = list(mongo_db.lessons.find({"lesson_id": {"$in": list(lesson_ids)}})) if lesson_ids else []
    exercise_docs = list(mongo_db.exercises.find({"exercise_id": {"$in": list(exercise_ids)}})) if exercise_ids else []

    # Build lookups
    unit_lookup = {doc.get('unit_id'): doc for doc in unit_docs}
    lesson_lookup = {doc.get('lesson_id'): doc for doc in lesson_docs}
    exercise_lookup = {doc.get('exercise_id'): doc for doc in exercise_docs}

    perseus_items = []
    
    # Ensure dash_system is available
    if dash_system is None:
        logger.error("DASH system not initialized when loading Perseus items")
        return perseus_items

    for question_id, dash_q in dash_lookup.items():
        question_doc = question_lookup.get(question_id)

        if not question_doc:
            logger.warning(f"No question found in questions_db for question_id {question_id}")
            continue

        # Extract perseus_json (already parsed in questions_db)
        perseus_json = question_doc.get('perseus_json', {})
        if not perseus_json:
            logger.warning(f"No perseus_json found for question_id {question_id}")
            continue

        # Get unit, lesson, exercise names (before try block)
        unit_doc = unit_lookup.get(question_doc.get('unit_id'))
        lesson_doc = lesson_lookup.get(question_doc.get('lesson_id'))
        exercise_doc = exercise_lookup.get(question_doc.get('exercise_id'))
        
        logger.info(f"[METADATA_LOOKUP] Q:{question_id} | unit_id={question_doc.get('unit_id')} | unit_doc={'Found' if unit_doc else 'None'} | lesson_id={question_doc.get('lesson_id')} | lesson_doc={'Found' if lesson_doc else 'None'} | exercise_id={question_doc.get('exercise_id')} | exercise_doc={'Found' if exercise_doc else 'None'}")

        # Extract required fields from perseus_json
        try:
            question = perseus_json.get('question', {})
            answer_area = perseus_json.get('answerArea', {})
            hints = perseus_json.get('hints', [])
            item_data_version = perseus_json.get('itemDataVersion', {})

            # Validate required fields
            if not question:
                logger.warning(f"Missing 'question' field in itemData for question_id {question_id}")
                continue

            # Extract slug from questionId (numeric prefix before underscore)
            # Example: "41.1.1.1.1_xde8147b8edb82294" -> "41.1.1.1.1"
            slug = question_id.split('_')[0] if '_' in question_id else question_id

            # Build Perseus data structure
            # Note: Perseus scoring uses the 'correct' property in widget choices
            # We don't need a separate answer key
            logger.info(f"[PERSEUS_LOAD] Building item for {question_id} - NO ANSWER KEY")
            
            perseus_data = {
                "question": question,
                "answerArea": answer_area,
                "hints": hints,
                "itemDataVersion": item_data_version,
                "dash_metadata": {
                    'dash_question_id': question_id,
                    'skill_ids': dash_q.skill_ids,
                    'difficulty': dash_q.difficulty,
                    'expected_time_seconds': dash_q.expected_time_seconds,
                    'slug': slug,
                    'skill_names': [dash_system.skills[sid].name for sid in dash_q.skill_ids
                                   if sid in dash_system.skills],
                    'unit_id': question_doc.get('unit_id'),  # Current module (unit) ID
                    'lesson_id': question_doc.get('lesson_id'),  # Sub-skill ID
                    'exercise_id': question_doc.get('exercise_id'),
                    'mongodb_id': str(question_doc.get('_id')),  # MongoDB ObjectId
                    'unit_name': unit_doc.get('title', 'Unknown Unit') if unit_doc else 'Unknown Unit',
                    'lesson_name': lesson_doc.get('title', 'Unknown Lesson') if lesson_doc else 'Unknown Lesson',
                    'exercise_name': exercise_doc.get('title', 'Unknown Exercise') if exercise_doc else 'Unknown Exercise'
                }
            }

            perseus_items.append(perseus_data)

        except Exception as e:
            logger.warning(f"Failed to load Perseus from questions_db for question_id {question_id}: {e}")
            continue

    return perseus_items


@app.get("/api/questions/preloaded", response_model=List[PerseusQuestion])
def get_preloaded_questions(request: Request):
    """
    Get pre-loaded questions for next session.
    Returns empty if no pre-loaded questions exist.
    """
    ensure_dash_system()
    
    # Get user_id with proper error handling
    try:
        user_id = get_current_user(request)
    except HTTPException as e:
        logger.error(f"[PRELOADED] Authentication error: {e.status_code} - {e.detail}")
        raise  # Re-raise to return proper 401/403 status code
    except Exception as e:
        logger.error(f"[PRELOADED] Unexpected error getting user: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"[PRELOADED] Checking for pre-loaded questions for user: {user_id}")
    logger.info(f"{'='*80}\n")
    
    # Check if user has pre-loaded questions stored
    from managers.mongodb_manager import mongo_db
    
    try:
        user_data = mongo_db.users.find_one({"user_id": user_id})
        if not user_data:
            logger.info("[PRELOADED] User not found")
            return []
        
        preloaded_question_ids = user_data.get("preloaded_question_ids", [])
        if not preloaded_question_ids:
            logger.info("[PRELOADED] No pre-loaded questions found")
            return []
        
        logger.info(f"[PRELOADED] Found {len(preloaded_question_ids)} pre-loaded question IDs: {preloaded_question_ids[:3]}...")
        
        # Convert question IDs to Question objects (on-demand creation)
        selected_questions = []
        for qid in preloaded_question_ids:
            question = dash_system._get_or_create_question(qid)
            if question:
                selected_questions.append(question)
            else:
                logger.warning(f"[PRELOADED] Question ID {qid} not found in DASH system")
        
        if not selected_questions:
            logger.info("[PRELOADED] No valid questions found from pre-loaded IDs")
            # Clear invalid pre-loaded questions
            mongo_db.users.update_one(
                {"user_id": user_id},
                {"$unset": {"preloaded_question_ids": ""}}
            )
            return []
        
        logger.info(f"[PRELOADED] Converted {len(selected_questions)} question IDs to Question objects")
        
        # Load Perseus items for pre-loaded questions
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(selected_questions)
        logger.info(f"[PRELOADED] Loaded {len(perseus_items)} Perseus questions from MongoDB")
        
        # Validate perseus_items structure before returning
        if perseus_items:
            # Validate first item structure
            first_item = perseus_items[0]
            required_fields = ['question', 'answerArea', 'hints']
            missing_fields = [field for field in required_fields if field not in first_item]
            if missing_fields:
                logger.error(f"[PRELOADED] Invalid Perseus item structure - missing fields: {missing_fields}")
                logger.error(f"[PRELOADED] Item keys: {list(first_item.keys())}")
            else:
                logger.info(f"[PRELOADED] Validated Perseus item structure - all required fields present")
        
        # Clear pre-loaded questions after retrieval
        mongo_db.users.update_one(
            {"user_id": user_id},
            {"$unset": {"preloaded_question_ids": ""}}
        )
        logger.info("[PRELOADED] Cleared pre-loaded questions from user profile")
        
        # Ensure we return empty list if no questions (valid response for FastAPI)
        if not perseus_items:
            logger.info("[PRELOADED] Returning empty list (no Perseus items loaded)")
            return []
        
        logger.info(f"[PRELOADED] Returning {len(perseus_items)} Perseus questions")
        return perseus_items
    except Exception as e:
        logger.error(f"[ERROR] Failed to load pre-loaded questions: {e}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        # Clear on error too
        try:
            mongo_db.users.update_one(
                {"user_id": user_id},
                {"$unset": {"preloaded_question_ids": ""}}
            )
        except Exception as clear_error:
            logger.error(f"[ERROR] Failed to clear pre-loaded questions: {clear_error}")
        # Return empty list on error (valid response)
        logger.info("[PRELOADED] Returning empty list due to error")
        return []


# ===== QUESTION ENDPOINTS =====
@app.get("/api/questions/{sample_size}", response_model=List[PerseusQuestion])
def get_questions_with_dash_intelligence(request: Request, sample_size: int):
    """
    Gets questions using DASH intelligence but returns full Perseus items.
    Uses DASH to intelligently select questions based on learning journey and adaptive difficulty.
    
    Args:
        request: FastAPI request object (for JWT extraction)
        sample_size: Number of questions to return
    """
    ensure_dash_system()
    # Get user_id from JWT token
    user_id = get_current_user(request)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"[NEW_SESSION] Requesting {sample_size} questions for user: {user_id}")
    logger.info(f"{'='*80}\n")
    
    # Ensure the user exists and is loaded (age comes from MongoDB)
    user_profile = dash_system.load_user_or_create(user_id)
    
    # Use DASH intelligence with flexible selection to get ALL questions
    current_time = time.time()
    selected_questions = []
    selected_question_ids = []  # Track selected question IDs to avoid duplicates
    
    # Get multiple questions using DASH flexible intelligence
    # Pass user_profile to avoid redundant MongoDB calls (was loading 4x for 2 questions!)
    for i in range(sample_size):
        # Use flexible selection that expands to grade-appropriate skills when needed
        next_question = dash_system.get_next_question_flexible(
            user_id,
            current_time,
            exclude_question_ids=selected_question_ids,
            user_profile=user_profile
        )
        if next_question:
            selected_questions.append(next_question)
            selected_question_ids.append(next_question.question_id)  # Track to avoid duplicates
        else:
            logger.info(f"[SESSION_END] Selected {len(selected_questions)}/{sample_size} questions (no more available)")
            break
    
    # Development bypass: if no questions selected, just get random ones from DB
    if not selected_questions and os.getenv("DEV_MODE", "true").lower() == "true":
        logger.warning(f"[DEV_BYPASS] No DASH questions selected, fetching {sample_size} random questions from Perseus DB")
        random_perseus = list(dash_system.mongo.perseus_questions.aggregate([
            {"$sample": {"size": sample_size}}
        ]))
        if random_perseus:
            logger.info(f"[DEV_BYPASS] Found {len(random_perseus)} random Perseus questions")
            return random_perseus
    
    # Load Perseus items from MongoDB for all DASH-selected questions
    try:
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(selected_questions)
        logger.info(f"[MONGODB] Loaded {len(perseus_items)} Perseus questions from MongoDB with full metadata")
    except Exception as e:
        logger.error(f"[ERROR] MongoDB Perseus load failed: {e}. Local fallback disabled.")
        raise HTTPException(status_code=500, detail=f"Failed to load Perseus questions from MongoDB: {e}")
    
    if not perseus_items:
        logger.error(f"[ERROR] No Perseus questions found in MongoDB")
        raise HTTPException(status_code=404, detail="No Perseus questions found in MongoDB")
    
    logger.info(f"[SESSION_READY] Loaded {len(perseus_items)} Perseus questions (all with DASH intelligence)\\n")
    
    # Return all questions (all selected by DASH with full intelligence)
    return perseus_items

@app.post("/api/question-displayed")
def log_question_displayed(request: Request, display_info: dict):
    """Log when student views a question (Next button clicked)"""
    ensure_dash_system()
    # Get user_id from JWT token
    user_id = get_current_user(request)
    
    # Get user_id from JWT token
    user_id = get_current_user(request)
    
    idx = display_info.get('question_index', 0)
    metadata = display_info.get('metadata', {})
    
    logger.info(f"\n{'='*80}")
    logger.info(f"[QUESTION_DISPLAYED] Question #{idx + 1}")
    logger.info(f"  Slug: {metadata.get('slug', 'unknown')}")
    logger.info(f"  DASH ID: {metadata.get('dash_question_id', 'unknown')}")
    logger.info(f"  Skills: {', '.join(metadata.get('skill_names', []))}")
    logger.info(f"  Difficulty: {metadata.get('difficulty', 0):.2f} | Expected: {metadata.get('expected_time_seconds', 0)}s")
    
    # Show current student state from question_attempts
    try:
        attempts_count = dash_system.mongo.question_attempts.count_documents({"user_id": user_id})
        if attempts_count > 0:
            logger.info(f"\n[STUDENT_STATE] {attempts_count} total question attempts recorded")
    except Exception as e:
        logger.debug(f"Could not fetch student state: {e}")
    
    logger.info(f"{'='*80}\n")
    return {"success": True}


class AnswerSubmission(BaseModel):
    question_id: str
    skill_ids: List[str]
    is_correct: bool
    response_time_seconds: float

class RecommendNextRequest(BaseModel):
    current_question_ids: List[str]
    count: int = 5

class AssessmentAnswer(BaseModel):
    question_id: str
    skill_id: str
    is_correct: bool

class CompleteAssessmentRequest(BaseModel):
    subject: str
    answers: List[AssessmentAnswer]

@app.post("/api/submit-answer")
def submit_answer(request: Request, answer: AnswerSubmission):
    """
    Record a question attempt and update DASH system.
    This enables tracking and adaptive difficulty.
    Stores raw question attempt for future-proof performance tracking.

    OPTIMIZED: Removed redundant user loads and expensive get_skill_scores call.
    Previous latency: 4-8 seconds. Target: < 500ms.
    """
    ensure_dash_system()
    
    # Import mongo_db at function level
    from managers.mongodb_manager import mongo_db
    
    # Get user_id from JWT token
    user_id = get_current_user(request)

    logger.info(f"\n{'-'*80}")
    logger.info(f"[SUBMIT_ANSWER] User: {user_id}")
    logger.info(f"[SUBMIT_ANSWER] Question ID: {answer.question_id}")
    logger.info(f"[SUBMIT_ANSWER] Is Correct: {answer.is_correct}")
    logger.info(f"[SUBMIT_ANSWER] Skill IDs: {answer.skill_ids}")
    logger.info(f"[SUBMIT_ANSWER] Response Time: {answer.response_time_seconds}s")
    logger.info(f"[SUBMIT_ANSWER] Answer object type: {type(answer.is_correct)}")
    logger.info(f"[SUBMIT_ANSWER] Answer object repr: {repr(answer.is_correct)}")
    
    # Store raw question attempt in question_attempts collection (future-proof)
    from datetime import datetime
    attempt_doc = {
        "user_id": user_id,
        "question_id": answer.question_id,
        "is_correct": answer.is_correct,
        "skill_ids": answer.skill_ids,
        "response_time_seconds": answer.response_time_seconds,
        "timestamp": datetime.now(),
        "session_id": None  # Can be added if you track sessions
    }
    
    try:
        result = mongo_db.question_attempts.insert_one(attempt_doc)
        logger.info(f"[ATTEMPT_STORED] Inserted ID: {result.inserted_id} | Question:{answer.question_id} | Correct:{answer.is_correct}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to store attempt in question_attempts: {e}")
        import traceback
        traceback.print_exc()

    user_profile = dash_system.user_manager.load_user(user_id)
    if not user_profile:
        logger.error(f"[ERROR] User {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")

    # Record the attempt using DASH system
    affected_skills = dash_system.record_question_attempt(
        user_profile, answer.question_id, answer.skill_ids,
        answer.is_correct, answer.response_time_seconds
    )

    # OPTIMIZED: Only get scores for affected skills, not all 126 skills
    # This reduces 126 calculations to just 1-5 calculations
    current_time = time.time()
    if affected_skills:
        logger.info(f"\n  [SKILL_UPDATES]")
        for skill_id in affected_skills[:3]:  # Show top 3 to keep readable
            skill = dash_system.skills.get(skill_id)
            if skill:
                # Calculate only for this specific skill
                memory_strength = dash_system.calculate_memory_strength(user_id, skill_id, current_time)
                probability = dash_system.predict_correctness(user_id, skill_id, current_time)
                skill_type = "DIRECT" if skill_id in answer.skill_ids else "PREREQ"
                logger.info(
                    f"    {skill.name[:20]:<20} ({skill_type:<6}): "
                    f"Mem {memory_strength:.3f} | "
                    f"Prob {probability:.3f}"
                )

    # OPTIMIZED: Use existing user_profile instead of reloading from MongoDB
    total_attempts = len(user_profile.question_history) + 1  # +1 for this attempt
    correct_count = sum(1 for attempt in user_profile.question_history if attempt.is_correct)
    if answer.is_correct:
        correct_count += 1
    accuracy = (correct_count / total_attempts * 100) if total_attempts > 0 else 0

    logger.info(f"\n[PROGRESS] Total:{total_attempts} questions | Accuracy:{accuracy:.1f}% ({correct_count}/{total_attempts})")
    logger.info(f"{'-'*80}\n")

    return {
        "success": True,
        "affected_skills": affected_skills,
        "message": "Answer recorded successfully"
    }

@app.get("/api/grading-panel")
def get_grading_panel(request: Request):
    """
    Get grading panel data from Khan Academy hierarchy.
    Skills = Units, Sub-skills = Lessons (following DASH Integration Plan).
    
    Returns student performance mapped to current questions_db structure.
    This is future-proof: survives questions_db updates without data loss.
    """
    ensure_dash_system()
    # Get user_id from JWT token
    user_id = get_current_user(request)
    
    try:
        grading_data = dash_system.get_grading_panel_data(user_id)
        logger.info(f"[GRADING_PANEL] Generated grading data for user {user_id}")
        return grading_data
    except Exception as e:
        logger.error(f"[ERROR] Error getting grading panel data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    skill_states = {}
    for skill_id, score_data in scores.items():
        # Get student state to get last_practice_time
        state = dash_system.get_student_state(user_id, skill_id)
        
        skill_states[skill_id] = {
            "name": score_data["name"],  # Include skill name
            "memory_strength": score_data["memory_strength"],
            "last_practice_time": state.last_practice_time if state.last_practice_time else None,
            "practice_count": score_data["practice_count"],
            "correct_count": score_data["correct_count"]
        }
    
    return {"skill_states": skill_states}

@app.post("/api/questions/recommend-next", response_model=List[PerseusQuestion])
def recommend_next_questions(request: Request, req: RecommendNextRequest):
    """
    Recommend next questions based on currently loaded questions.
    Takes existing question IDs and recommends next batch using DASH intelligence.
    Only returns questions if they differ from current ones.
    
    Args:
        request: FastAPI request object (for JWT extraction)
        req: Request body containing current question IDs and count
    """
    ensure_dash_system()
    user_id = get_current_user(request)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"[RECOMMEND_NEXT] User: {user_id}, Current questions: {len(req.current_question_ids)}, Requesting: {req.count}")
    logger.info(f"{'='*80}\n")
    
    # Ensure the user exists and is loaded
    user_profile = dash_system.load_user_or_create(user_id)
    current_time = time.time()
    
    # Get next questions using DASH, excluding current ones
    selected_questions = []
    exclude_ids = set(req.current_question_ids)
    
    for i in range(req.count):
        next_question = dash_system.get_next_question_flexible(
            user_id,
            current_time,
            exclude_question_ids=list(exclude_ids)
        )
        if next_question:
            selected_questions.append(next_question)
            exclude_ids.add(next_question.question_id)
        else:
            logger.info(f"[RECOMMEND_NEXT] No more questions available after {len(selected_questions)}")
            break
    
    if not selected_questions:
        logger.info("[RECOMMEND_NEXT] No new questions available")
        return []  # Return empty if no new questions
    
    # Load Perseus items for selected questions
    try:
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(selected_questions)
        logger.info(f"[RECOMMEND_NEXT] Loaded {len(perseus_items)} new questions")
        
        # Verify no overlap with current questions (should not happen due to exclusion, but check for safety)
        new_question_ids = {item.get('dash_metadata', {}).get('dash_question_id') for item in perseus_items if item.get('dash_metadata', {}).get('dash_question_id')}
        current_question_ids_set = set(req.current_question_ids)
        
        # Check for any overlap (should not happen, but log warning if it does)
        overlap = new_question_ids.intersection(current_question_ids_set)
        if overlap:
            logger.warning(f"[RECOMMEND_NEXT] Warning: {len(overlap)} recommended questions overlap with current (should not happen)")
            # Filter out overlapping questions
            perseus_items = [item for item in perseus_items 
                           if item.get('dash_metadata', {}).get('dash_question_id') not in overlap]
            if not perseus_items:
                logger.info("[RECOMMEND_NEXT] All recommended questions were duplicates, returning empty")
                return []
        
        return perseus_items
    except Exception as e:
        logger.error(f"[ERROR] Failed to load recommended questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load recommended questions: {e}")


@app.get("/api/learning-assets/videos/{question_id}")
async def get_learning_videos(
    question_id: str,
    request: Request,
    preferred_language: str = "English"
):
    """
    Get learning videos for a question, filtered by language.
    
    Args:
        question_id: The dash_question_id (e.g., "41.1.1.1.1_xde8147b8edb82294")
        preferred_language: Preferred language for videos (default: "English")
    
    Returns:
        List of learning videos (max 6) filtered by language
    """
    from managers.mongodb_manager import mongo_db
    
    try:
        # Get question from scraped_questions collection
        question_doc = mongo_db.scraped_questions.find_one({"questionId": question_id})
        
        if not question_doc:
            logger.warning(f"[LEARNING_ASSETS] Question not found: {question_id}")
            return []
        
        # Extract learning_videos array
        learning_videos = question_doc.get("learning_videos", [])
        
        if not learning_videos:
            logger.info(f"[LEARNING_ASSETS] No learning videos found for question: {question_id}")
            return []
        
        # Filter by preferred_language
        filtered_videos = [
            video for video in learning_videos
            if video.get("language", "English").lower() == preferred_language.lower()
        ]
        
        # If no videos in preferred language, return all videos
        if not filtered_videos:
            logger.info(f"[LEARNING_ASSETS] No videos in {preferred_language}, returning all videos")
            filtered_videos = learning_videos
        
        # Sort by score (descending) - highest helping scores first
        filtered_videos.sort(key=lambda v: v.get("score", 0), reverse=True)
        
        # Return top 6 videos
        result = filtered_videos[:6]
        
        logger.info(f"[LEARNING_ASSETS] Returning {len(result)} videos for question {question_id} (language: {preferred_language})")
        
        return result
        
    except Exception as e:
        logger.error(f"[ERROR] Failed to get learning videos for question {question_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get learning videos: {str(e)}")


# ===== ASSESSMENT ENDPOINTS (PHASE 3) =====

@app.post("/assessment/start/{subject}")
def start_assessment(
    subject: str,
    request: Request
):
    """
    Start assessment for a subject.
    Returns 10 questions with explicit grade distribution.
    Distribution: 2 (grade-2), 4 (grade-1), 2 (current), 2 (grade+1)
    """
    ensure_dash_system()
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)
    logger.info(f"\n{'='*80}")
    logger.info(f"[ASSESSMENT] Starting assessment for subject: {subject}, user: {user_id}")
    logger.info(f"{'='*80}\n")

    try:
        # Check if already completed
        existing = mongo_db.subject_assessments.find_one({
            "user_id": user_id,
            "subject": subject,
            "assessment_completed": True
        })

        if existing:
            logger.info(f"[ASSESSMENT] User already completed {subject} assessment")
            return {
                "error": "Assessment already completed",
                "score": existing.get("score"),
                "date": existing.get("assessment_date")
            }

        # Get user's current grade
        user_profile = dash_system.load_user_or_create(user_id)
        current_grade_value = GradeLevel[user_profile.current_grade].value

        logger.info(f"[ASSESSMENT] User grade: {user_profile.current_grade} (value: {current_grade_value})")

        # Get questions with explicit grade distribution
        # Distribution: 2 (grade-2), 4 (grade-1), 2 (current), 2 (grade+1)
        questions = []
        exclude_question_ids = set()
        exclude_skill_ids = set()  # Track skills to diversify questions
        current_time = time.time()

        for grade_offset, count in [(-2, 2), (-1, 4), (0, 2), (1, 2)]:
            target_grade = max(1, current_grade_value + grade_offset)
            logger.info(f"[ASSESSMENT] Fetching {count} questions for grade offset {grade_offset} (target grade: {target_grade})")

            # Get questions from DASH system with grade filtering
            # Try to get diverse questions by limiting questions from same skill
            for i in range(count):
                attempts = 0
                max_attempts = 5  # Try up to 5 times to find a question from a different skill

                while attempts < max_attempts:
                    next_q = dash_system.get_next_question_flexible(
                        user_id,
                        current_time,
                        exclude_question_ids=list(exclude_question_ids),
                        user_profile=user_profile,
                        exclude_skill_ids=list(exclude_skill_ids) if exclude_skill_ids else None
                    )

                    if next_q:
                        skill_ids = next_q.skill_ids if next_q.skill_ids else []

                        # Accept this question and track the skill for diversity
                        if skill_ids:
                            questions.append(next_q)
                            exclude_question_ids.add(next_q.question_id)
                            # After getting first question in this grade group, exclude this skill for diversity
                            if i == 0:
                                exclude_skill_ids.add(skill_ids[0])
                            break
                        else:
                            # No skill IDs, skip this question
                            exclude_question_ids.add(next_q.question_id)
                            attempts += 1
                            continue
                    else:
                        break

                    attempts += 1

        if len(questions) < 10:
            logger.warning(f"[ASSESSMENT] Only found {len(questions)}/10 questions")
            # Pad with remaining questions if needed
            while len(questions) < 10:
                next_q = dash_system.get_next_question_flexible(
                    user_id,
                    current_time,
                    exclude_question_ids=list(exclude_question_ids),
                    user_profile=user_profile,
                    exclude_skill_ids=list(exclude_skill_ids) if exclude_skill_ids else None
                )
                if next_q:
                    questions.append(next_q)
                    exclude_question_ids.add(next_q.question_id)
                else:
                    break

        if len(questions) < 10:
            logger.error(f"[ASSESSMENT] Not enough questions available ({len(questions)}/10)")
            raise HTTPException(status_code=400, detail="Not enough questions for assessment")

        # Load Perseus items for the questions
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(questions)

        if not perseus_items or len(perseus_items) < 10:
            logger.error(f"[ASSESSMENT] Failed to load all Perseus items ({len(perseus_items)}/10)")
            raise HTTPException(status_code=400, detail="Failed to load assessment questions")

        # Mark assessment as started
        mongo_db.subject_assessments.update_one(
            {"user_id": user_id, "subject": subject},
            {
                "$set": {
                    "assessment_started_at": datetime.now(),
                    "assessment_completed": False,
                    "status": "in_progress"
                }
            },
            upsert=True
        )

        logger.info(f"[ASSESSMENT] Loaded {len(perseus_items)} questions for {subject} assessment")

        return {
            "status": "started",
            "subject": subject,
            "questions": perseus_items,
            "total": len(perseus_items)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ASSESSMENT] Error starting assessment: {e}")
        import traceback
        logger.error(f"[ASSESSMENT] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to start assessment: {str(e)}")


@app.post("/assessment/complete")
def complete_assessment(
    request: Request,
    payload: CompleteAssessmentRequest
):
    """
    Complete assessment and initialize skill states.
    Stores assessment results and initializes user's skill_states for learning plan.
    """
    ensure_dash_system()
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)
    subject = payload.subject
    answers = payload.answers

    logger.info(f"\n{'='*80}")
    logger.info(f"[ASSESSMENT_COMPLETE] Completing assessment for subject: {subject}")
    logger.info(f"  Total answers: {len(answers)}")
    logger.info(f"{'='*80}\n")

    try:
        # Calculate score and group by skill
        correct_count = sum(1 for a in answers if a.is_correct)
        skill_results = {}

        for answer in answers:
            skill_id = answer.skill_id
            if skill_id not in skill_results:
                skill_results[skill_id] = {"correct": 0, "total": 0}
            skill_results[skill_id]["total"] += 1
            if answer.is_correct:
                skill_results[skill_id]["correct"] += 1

        # Update assessment record
        mongo_db.subject_assessments.update_one(
            {"user_id": user_id, "subject": subject},
            {
                "$set": {
                    "assessment_completed": True,
                    "assessment_date": datetime.now(),
                    "score": correct_count,
                    "total": len(answers),
                    "skill_results": {k: v for k, v in skill_results.items()},
                    "answers": [a.dict() for a in answers],
                    "learning_plan_generated": True
                }
            },
            upsert=True
        )

        logger.info(f"[ASSESSMENT_COMPLETE] Score: {correct_count}/{len(answers)}")
        logger.info(f"[ASSESSMENT_COMPLETE] Skill results: {skill_results}")

        # Initialize skill_states in UserProfile from assessment results
        user_profile = dash_system.load_user_or_create(user_id)

        if not hasattr(user_profile, 'skill_states'):
            user_profile.skill_states = {}

        current_time = time.time()

        for skill_id, results in skill_results.items():
            # Calculate memory strength: 1.0 if correct, 0.5 if some correct, 0.0 if all wrong
            if results["correct"] > 0:
                memory_strength = 1.0 if results["correct"] / results["total"] >= 0.5 else 0.5
            else:
                memory_strength = 0.0

            user_profile.skill_states[skill_id] = {
                "memory_strength": memory_strength,
                "last_practice_time": current_time,
                "practice_count": results["total"],
                "correct_count": results["correct"]
            }

        # Convert SkillState objects to dictionaries for MongoDB serialization
        skill_states_dict = {}
        for skill_id, skill_state in user_profile.skill_states.items():
            # Handle both SkillState objects and dictionaries
            if hasattr(skill_state, 'to_dict'):
                skill_states_dict[skill_id] = skill_state.to_dict()
            elif isinstance(skill_state, dict):
                skill_states_dict[skill_id] = skill_state
            else:
                # Fallback: try to extract attributes
                skill_states_dict[skill_id] = {
                    "memory_strength": getattr(skill_state, 'memory_strength', 0.0),
                    "last_practice_time": getattr(skill_state, 'last_practice_time', current_time),
                    "practice_count": getattr(skill_state, 'practice_count', 0),
                    "correct_count": getattr(skill_state, 'correct_count', 0)
                }

        # Save back to MongoDB
        mongo_db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "skill_states": skill_states_dict,
                    "last_updated": current_time
                }
            }
        )

        logger.info(f"[ASSESSMENT_COMPLETE] Initialized {len(user_profile.skill_states)} skill states")

        return {
            "status": "completed",
            "score": correct_count,
            "total": len(answers),
            "percentage": (correct_count / len(answers) * 100) if answers else 0
        }

    except Exception as e:
        logger.error(f"[ASSESSMENT_COMPLETE] Error completing assessment: {e}")
        import traceback
        logger.error(f"[ASSESSMENT_COMPLETE] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to complete assessment: {str(e)}")


@app.get("/assessment/status/{subject}")
def check_assessment_status(
    subject: str,
    request: Request
):
    """
    Check if user has completed assessment for a subject.
    Used to prevent re-assessment.
    """
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)

    try:
        assessment = mongo_db.subject_assessments.find_one({
            "user_id": user_id,
            "subject": subject
        })

        if not assessment:
            return {
                "completed": False,
                "score": None,
                "date": None
            }

        return {
            "completed": assessment.get("assessment_completed", False),
            "score": assessment.get("score"),
            "date": assessment.get("assessment_date"),
            "total": assessment.get("total")
        }

    except Exception as e:
        logger.error(f"[ASSESSMENT_STATUS] Error checking status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check assessment status: {str(e)}")


# ===== VIDEO TRACKING ENDPOINTS (PHASE 3) =====

@app.post("/api/videos/mark-helpful")
def mark_video_helpful(
    request: Request,
    question_id: str,
    video_id: str,
    is_correct: bool
):
    """
    Track when video helps student answer correctly.
    Increments score and helpful_count when is_correct=true.
    Always increments views.
    """
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)

    logger.info(f"[VIDEO_TRACKING] Marking video {video_id} for question {question_id} (correct: {is_correct})")

    try:
        if is_correct:
            # Increment score and helpful_count when answer is correct
            mongo_db.scraped_questions.update_one(
                {
                    "questionId": question_id,
                    "learning_videos.video_id": video_id
                },
                {
                    "$inc": {
                        "learning_videos.$.score": 1,
                        "learning_videos.$.helpful_count": 1,
                        "learning_videos.$.views": 1
                    }
                }
            )
        else:
            # Always increment views
            mongo_db.scraped_questions.update_one(
                {
                    "questionId": question_id,
                    "learning_videos.video_id": video_id
                },
                {
                    "$inc": {"learning_videos.$.views": 1}
                }
            )

        logger.info(f"[VIDEO_TRACKING] Successfully tracked video {video_id}")
        return {"success": True, "status": "tracked"}

    except Exception as e:
        logger.error(f"[VIDEO_TRACKING] Error tracking video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track video: {str(e)}")


@app.post("/api/videos/approve")
def approve_video(
    request: Request,
    question_id: str,
    video_id: str
):
    """
    Move video from suggested_videos to learning_videos.
    Initializes tracking fields.
    """
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)

    logger.info(f"[VIDEO_APPROVAL] Approving video {video_id} for question {question_id}")

    try:
        # Find the suggested video
        doc = mongo_db.scraped_questions.find_one(
            {
                "questionId": question_id,
                "suggested_videos.video_id": video_id
            },
            {"suggested_videos.$": 1}
        )

        if not doc or not doc.get("suggested_videos"):
            logger.warning(f"[VIDEO_APPROVAL] Video not found in suggested_videos")
            raise HTTPException(status_code=404, detail="Video not found")

        video = doc["suggested_videos"][0]

        # Initialize tracking fields
        video_to_add = {
            "video_id": video.get("video_id"),
            "title": video.get("title"),
            "language": video.get("language", "en"),
            "score": 0,
            "views": 0,
            "helpful_count": 0,
            "approved_at": datetime.now()
        }

        # Move to learning_videos
        mongo_db.scraped_questions.update_one(
            {"questionId": question_id},
            {
                "$push": {"learning_videos": video_to_add},
                "$pull": {"suggested_videos": {"video_id": video_id}}
            }
        )

        logger.info(f"[VIDEO_APPROVAL] Video {video_id} approved and moved to learning_videos")
        return {"success": True, "status": "approved"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[VIDEO_APPROVAL] Error approving video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve video: {str(e)}")


@app.post("/api/videos/reject")
def reject_video(
    request: Request,
    question_id: str,
    video_id: str
):
    """
    Remove video from suggested_videos.
    """
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)

    logger.info(f"[VIDEO_REJECTION] Rejecting video {video_id} for question {question_id}")

    try:
        mongo_db.scraped_questions.update_one(
            {"questionId": question_id},
            {"$pull": {"suggested_videos": {"video_id": video_id}}}
        )

        logger.info(f"[VIDEO_REJECTION] Video {video_id} rejected and removed")
        return {"success": True, "status": "rejected"}

    except Exception as e:
        logger.error(f"[VIDEO_REJECTION] Error rejecting video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reject video: {str(e)}")


@app.get("/api/admin/videos/suggested")
def get_suggested_videos(
    request: Request,
    limit: int = 50,
    offset: int = 0
):
    """
    Get all suggested videos waiting for approval.
    Returns questions with their suggested videos.
    """
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)

    logger.info(f"[ADMIN_PANEL] Fetching suggested videos (limit: {limit}, offset: {offset})")

    try:
        # Find questions with suggested_videos
        questions = list(mongo_db.scraped_questions.find({
            "suggested_videos": {"$exists": True, "$ne": []}
        }).skip(offset).limit(limit))

        # Format response
        result = []
        for question in questions:
            question_id = question.get("questionId", "")
            suggested_videos = question.get("suggested_videos", [])

            # Get question text for context
            question_text = ""
            try:
                assessment_data = question.get("assessmentData", {})
                item_data_str = assessment_data.get("data", {}).get("assessmentItem", {}).get("item", {}).get("itemData", "")
                if item_data_str:
                    import json
                    item_data = json.loads(item_data_str)
                    question_obj = item_data.get("question", {})
                    question_text = question_obj.get("content", "")
                    # Clean up Perseus widgets
                    import re
                    question_text = re.sub(r'\[\[☃[^\]]+\]\]', '', question_text)
                    question_text = re.sub(r'\*\*', '', question_text)
                    question_text = re.sub(r'\$\\\\[^$]+\$', '', question_text).strip()[:100]
            except Exception as e:
                logger.warning(f"[ADMIN_PANEL] Error parsing question text for {question_id}: {e}")

            result.append({
                "question_id": question_id,
                "question_text": question_text,
                "suggested_videos_count": len(suggested_videos),
                "videos": suggested_videos
            })

        logger.info(f"[ADMIN_PANEL] Returning {len(result)} questions with suggested videos")
        return result

    except Exception as e:
        logger.error(f"[ADMIN_PANEL] Error fetching suggested videos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch suggested videos: {str(e)}")


@app.get("/api/admin/videos/stats")
def get_videos_stats(
    request: Request
):
    """
    Get statistics about suggested and approved videos.
    """
    from managers.mongodb_manager import mongo_db

    user_id = get_current_user(request)

    logger.info(f"[ADMIN_PANEL] Fetching video statistics")

    try:
        # Count questions with suggested videos
        questions_with_suggested = mongo_db.scraped_questions.count_documents({
            "suggested_videos": {"$exists": True, "$ne": []}
        })

        # Get total count of suggested videos
        total_suggested = 0
        suggested_questions = list(mongo_db.scraped_questions.find({
            "suggested_videos": {"$exists": True, "$ne": []}
        }))
        for q in suggested_questions:
            total_suggested += len(q.get("suggested_videos", []))

        # Count questions with approved videos
        questions_with_approved = mongo_db.scraped_questions.count_documents({
            "learning_videos": {"$exists": True, "$ne": []}
        })

        # Get total count of approved videos
        total_approved = 0
        approved_questions = list(mongo_db.scraped_questions.find({
            "learning_videos": {"$exists": True, "$ne": []}
        }))
        for q in approved_questions:
            total_approved += len(q.get("learning_videos", []))

        stats = {
            "questions_with_suggested": questions_with_suggested,
            "total_suggested_videos": total_suggested,
            "questions_with_approved": questions_with_approved,
            "total_approved_videos": total_approved
        }

        logger.info(f"[ADMIN_PANEL] Video stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"[ADMIN_PANEL] Error fetching video statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("DASH_PORT", 8000))  # DASH API on 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
