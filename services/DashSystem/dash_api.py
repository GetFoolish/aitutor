import time
import sys
import os
import json
import logging
import random
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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

from services.DashSystem.dash_system import DASHSystem, Question
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


DEFAULT_ANSWER_AREA = {
    "calculator": False,
    "chi2Table": False,
    "periodicTable": False,
    "tTable": False,
    "zTable": False,
}


def _build_dash_metadata(question_id: str, dash_q: Question, slug: str) -> Dict:
    return {
        'dash_question_id': question_id,
        'skill_ids': dash_q.skill_ids,
        'difficulty': dash_q.difficulty,
        'expected_time_seconds': dash_q.expected_time_seconds,
        'slug': slug,
        'skill_names': [dash_system.skills[sid].name for sid in dash_q.skill_ids if sid in dash_system.skills],
    }


def _normalize_choice_text(value: object) -> str:
    return str(value).strip()


def _fallback_distractor_candidates(correct_answer: str) -> List[str]:
    stripped = correct_answer.strip()
    if not stripped:
        return ["Option A", "Option B", "Option C"]

    if stripped.endswith("%"):
        raw_number = stripped[:-1]
        try:
            value = float(raw_number)
            return [f"{value + 5:g}%", f"{max(value - 5, 0):g}%", f"{value + 10:g}%"]
        except ValueError:
            pass

    try:
        numeric_value = float(stripped)
        if numeric_value.is_integer():
            base = int(numeric_value)
            return [str(base + 1), str(base - 1), str(base + 2)]
        return [f"{numeric_value + 0.1:g}", f"{numeric_value - 0.1:g}", f"{numeric_value + 0.2:g}"]
    except ValueError:
        pass

    if "/" in stripped:
        numerator, denominator, *rest = stripped.split("/")
        if not rest:
            try:
                num = int(numerator.strip())
                den = int(denominator.strip())
                return [f"{num + 1}/{den}", f"{num}/{den + 1}", f"{max(num - 1, 1)}/{den}"]
            except ValueError:
                pass

    if ":" in stripped:
        left, right, *rest = stripped.split(":")
        if not rest:
            try:
                left_num = int(left.strip())
                right_num = int(right.strip())
                return [f"{left_num + 1}:{right_num}", f"{left_num}:{right_num + 1}", f"{max(left_num - 1, 1)}:{right_num}"]
            except ValueError:
                pass

    return [f"{stripped}?", f"not {stripped}", f"{stripped} (alt)"]


def _build_legacy_radio_choices(question_id: str, correct_answer: str, candidate_answers: List[str]) -> List[Dict]:
    correct_choice = _normalize_choice_text(correct_answer)
    seen = {correct_choice.lower()}
    distractors: List[str] = []

    for candidate in candidate_answers + _fallback_distractor_candidates(correct_choice):
        normalized = _normalize_choice_text(candidate)
        if not normalized or normalized.lower() in seen:
            continue
        distractors.append(normalized)
        seen.add(normalized.lower())
        if len(distractors) == 3:
            break

    while len(distractors) < 3:
        filler = f"{correct_choice} ({len(distractors) + 1})"
        if filler.lower() not in seen:
            distractors.append(filler)
            seen.add(filler.lower())

    choice_values = [correct_choice, *distractors[:3]]
    rng = random.Random(question_id)
    rng.shuffle(choice_values)

    choices = []
    for idx, choice_value in enumerate(choice_values):
        is_correct = choice_value == correct_choice
        choices.append(
            {
                "id": f"{question_id}-choice-{idx}",
                "content": choice_value,
                "correct": is_correct,
                "isNoneOfTheAbove": False,
                "rationale": "This is the correct answer." if is_correct else "This is not the correct answer.",
            }
        )

    return choices


def _build_legacy_perseus_item(dash_q: Question, question_doc: Dict, candidate_answers: List[str]) -> Dict:
    question_id = question_doc["question_id"]
    content = question_doc.get("content", "").strip()
    correct_answer = _normalize_choice_text(question_doc.get("correct_answer", ""))

    if not content or not correct_answer:
        raise ValueError(f"Legacy question {question_id} is missing content or correct_answer")

    return {
        "question": {
            "content": f"{content}\n\n[[☃ radio 1]]\n",
            "images": {},
            "widgets": {
                "radio 1": {
                    "graded": True,
                    "version": {"major": 1, "minor": 0},
                    "static": False,
                    "type": "radio",
                    "alignment": "default",
                    "options": {
                        "choices": _build_legacy_radio_choices(question_id, correct_answer, candidate_answers),
                        "countChoices": False,
                        "hasNoneOfTheAbove": False,
                        "multipleSelect": False,
                        "randomize": False,
                        "deselectEnabled": False,
                    },
                }
            },
        },
        "answerArea": dict(DEFAULT_ANSWER_AREA),
        "hints": [],
        "itemDataVersion": {"major": 0, "minor": 0},
        "dash_metadata": _build_dash_metadata(question_id, dash_q, question_id),
    }


def _load_legacy_perseus_items(dash_questions: List[Question]) -> List[Dict]:
    from managers.mongodb_manager import mongo_db

    dash_lookup = {q.question_id: q for q in dash_questions}
    question_ids = list(dash_lookup.keys())
    legacy_docs = list(mongo_db.dash_questions.find({"question_id": {"$in": question_ids}}))
    legacy_lookup = {doc.get("question_id"): doc for doc in legacy_docs}

    skill_ids = sorted({doc.get("skill_id") for doc in legacy_docs if doc.get("skill_id")})
    skill_answer_docs = list(
        mongo_db.dash_questions.find(
            {"skill_id": {"$in": skill_ids}},
            {"question_id": 1, "skill_id": 1, "correct_answer": 1},
        )
    )

    answers_by_skill: Dict[str, List[str]] = {}
    global_answers: List[str] = []
    for answer_doc in skill_answer_docs:
        answer_text = _normalize_choice_text(answer_doc.get("correct_answer", ""))
        skill_id = answer_doc.get("skill_id")
        if not answer_text or not skill_id:
            continue
        answers_by_skill.setdefault(skill_id, []).append(answer_text)
        global_answers.append(answer_text)

    perseus_items = []
    for question_id, dash_q in dash_lookup.items():
        question_doc = legacy_lookup.get(question_id)
        if not question_doc:
            logger.warning(f"No legacy dash question found for question_id {question_id}")
            continue

        skill_id = question_doc.get("skill_id")
        candidate_answers = answers_by_skill.get(skill_id, []) + global_answers

        try:
            perseus_items.append(_build_legacy_perseus_item(dash_q, question_doc, candidate_answers))
        except ValueError as exc:
            logger.warning(str(exc))

    return perseus_items


def load_perseus_items_for_dash_questions_from_mongodb(
    dash_questions: List[Question]
) -> List[Dict]:
    """Load Perseus items from scraped_questions collection matching DASH-selected questions.

    OPTIMIZED: Uses batch query with $in instead of one query per question.
    """
    from managers.mongodb_manager import mongo_db
    import json

    if not dash_questions:
        return []

    # Build lookup map for DASH metadata
    dash_lookup = {q.question_id: q for q in dash_questions}
    question_ids = list(dash_lookup.keys())

    # BATCH QUERY: Fetch all questions in one MongoDB call instead of N calls
    scraped_docs = list(mongo_db.scraped_questions.find(
        {"questionId": {"$in": question_ids}}
    ))

    # Build lookup for scraped docs
    scraped_lookup = {doc.get('questionId'): doc for doc in scraped_docs}

    perseus_items = []
    
    # Ensure dash_system is available
    if dash_system is None:
        logger.error("DASH system not initialized when loading Perseus items")
        return perseus_items

    if getattr(dash_system, "question_data_mode", "modern") == "legacy":
        return _load_legacy_perseus_items(dash_questions)

    for question_id, dash_q in dash_lookup.items():
        scraped_doc = scraped_lookup.get(question_id)

        if not scraped_doc:
            logger.warning(f"No scraped question found for question_id {question_id}")
            continue

        # Extract assessmentData
        assessment_data = scraped_doc.get('assessmentData', {})
        if not assessment_data:
            logger.warning(f"No assessmentData found for question_id {question_id}")
            continue

        # Navigate to itemData: assessmentData.data.assessmentItem.item.itemData
        try:
            item_data_str = assessment_data.get('data', {}).get('assessmentItem', {}).get('item', {}).get('itemData', '')
            if not item_data_str:
                logger.warning(f"No itemData found for question_id {question_id}")
                continue

            # Parse JSON string to get Perseus object
            item_data = json.loads(item_data_str)

            # Extract required fields
            question = item_data.get('question', {})
            answer_area = item_data.get('answerArea', {})
            hints = item_data.get('hints', [])
            item_data_version = item_data.get('itemDataVersion', {})

            # Validate required fields
            if not question:
                logger.warning(f"Missing 'question' field in itemData for question_id {question_id}")
                continue

            # Extract slug from questionId (numeric prefix before underscore)
            # Example: "41.1.1.1.1_xde8147b8edb82294" -> "41.1.1.1.1"
            slug = question_id.split('_')[0] if '_' in question_id else question_id

            # Build Perseus data structure
            perseus_data = {
                "question": question,
                "answerArea": answer_area,
                "hints": hints,
                "itemDataVersion": item_data_version,
                "dash_metadata": _build_dash_metadata(question_id, dash_q, slug),
            }

            perseus_items.append(perseus_data)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse itemData JSON for question_id {question_id}: {e}")
            continue
        except KeyError as e:
            logger.warning(f"Missing field in assessmentData for question_id {question_id}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Failed to load Perseus from scraped_questions for question_id {question_id}: {e}")

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
    
    idx = display_info.get('question_index', 0)
    metadata = display_info.get('metadata', {})
    
    logger.info(f"\n{'='*80}")
    logger.info(f"[QUESTION_DISPLAYED] Question #{idx + 1}")
    logger.info(f"  Slug: {metadata.get('slug', 'unknown')}")
    logger.info(f"  DASH ID: {metadata.get('dash_question_id', 'unknown')}")
    logger.info(f"  Skills: {', '.join(metadata.get('skill_names', []))}")
    logger.info(f"  Difficulty: {metadata.get('difficulty', 0):.2f} | Expected: {metadata.get('expected_time_seconds', 0)}s")
    
    # Show current student state
    user_profile = dash_system.user_manager.load_user(user_id)
    if user_profile:
        current_time = time.time()
        scores = dash_system.get_skill_scores(user_id, current_time)
        
        # Only show practiced skills
        practiced = {k: v for k, v in scores.items() if v['practice_count'] > 0}
        
        if practiced:
            logger.info(f"\n[STUDENT_STATE]")
            logger.info(f"  {'Skill':<20} | {'Mem':<6} | {'Prob':<6} | {'Prac':<5} | {'Acc':<6}")
            logger.info(f"  {'-'*58}")
            for skill_id, data in list(practiced.items())[:5]:  # Show top 5
                logger.info(
                    f"  {data['name'][:20]:<20} | "
                    f"{data['memory_strength']:<6.2f} | "
                    f"{data['probability']:<6.2f} | "
                    f"{data['practice_count']:<5} | "
                    f"{data['accuracy']:<6.1%}"
                )
    
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

@app.post("/api/submit-answer")
def submit_answer(request: Request, answer: AnswerSubmission):
    """
    Record a question attempt and update DASH system.
    This enables tracking and adaptive difficulty.

    OPTIMIZED: Removed redundant user loads and expensive get_skill_scores call.
    Previous latency: 4-8 seconds. Target: < 500ms.
    """
    ensure_dash_system()
    # Get user_id from JWT token
    user_id = get_current_user(request)

    logger.info(f"\n{'-'*80}")

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

@app.get("/api/skill-scores")
def get_skill_scores(request: Request):
    """
    Get all skill scores for the current user.
    Returns skill states in the format expected by the frontend GradingSidebar.
    """
    ensure_dash_system()
    # Get user_id from JWT token
    user_id = get_current_user(request)
    
    # Get user profile to ensure it exists and sync skill states
    user_profile = dash_system.load_user_or_create(user_id)
    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get current time for calculations
    current_time = time.time()
    
    # Get all skill scores from DASH system
    scores = dash_system.get_skill_scores(user_id, current_time)
    
    # Transform to format expected by frontend
    # Frontend expects: { skill_id: { name, memory_strength, last_practice_time, practice_count, correct_count } }
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("DASH_PORT", 8000))  # DASH API on 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
