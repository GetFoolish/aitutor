import hashlib
import time
import sys
import os
import json
import logging
import random
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from services.DashSystem.content_v1 import ContentV1Engine
from shared.auth_middleware import get_current_user, get_jwt_payload, require_admin
from shared.cache_middleware import CacheControlMiddleware
from shared.cors_config import ALLOWED_ORIGINS, ALLOW_CREDENTIALS, ALLOWED_METHODS, ALLOWED_HEADERS

from shared.logging_config import get_logger

logger = get_logger(__name__)


app = FastAPI()
dash_system = None  # Initialize as None, will be set in startup event
content_v1_engine = None  # Initialize as None, will be set in startup event
curriculum_generator = None  # Initialize as None, will be set in startup event
quality_tracker = None  # Initialize as None, will be set in startup event
question_analytics = None  # Initialize as None, will be set in startup event
content_service = None  # Initialize as None, will be set in startup event
_subject_lock = threading.Lock()  # Mutex for subject switching on global dash_system
_prefetch_cache: Dict[str, dict] = {}  # assessment_id → {"q_data": ..., "question_id": ..., ...}
_prefetch_lock = threading.Lock()
_learning_prefetch_cache: Dict[str, dict] = {}  # user_id → {"q_data": ..., "question_id": ..., "skill_id": ..., "ts": ...}
_learning_prefetch_lock = threading.Lock()
_warmstart_cache: Dict[str, dict] = {}  # f"{user_id}:{subject}" → {"q_data", "question_id", "skill_id", "ts"}
_warmstart_events: Dict[str, threading.Event] = {}  # signals when warm-start finishes
_warmstart_lock = threading.Lock()
WARMSTART_TTL = 300  # 5 minutes
WARMSTART_WAIT_TIMEOUT = 30  # seconds to wait for in-flight warm-start


def _snapshot_curriculum():
    """Take a consistent snapshot of curriculum state under lock.

    After Bug B1 fix, reload_curriculum() does an atomic swap so reading
    dash_system.skills gives a stable dict reference even without the lock.
    This helper is provided for any future endpoint that needs a coherent
    triplet (subject, region, skills) at a single point in time.
    """
    with _subject_lock:
        return {
            "subject": dash_system.subject,
            "region": dash_system.region,
            "skills": dash_system.skills,  # dict ref is immutable after atomic swap
        }


def _switch_subject_if_needed(subject: str, region: str = "US") -> bool:
    """Thread-safe subject switch on the global dash_system singleton.

    Acquires a lock so concurrent requests queue instead of racing.
    Returns True if a reload happened, False if already on the right subject.
    """
    # Normalize subject to title case to match extract_subject() canonical form
    # e.g. "math" -> "Math", "computer science" -> "Computer Science"
    subject = subject.title()

    with _subject_lock:
        if dash_system.subject == subject and dash_system.region == region and len(dash_system.skills) > 0:
            return False
        logger.info(f"[SUBJECT_SWITCH] {dash_system.subject}/{dash_system.region} -> {subject}/{region}")
        dash_system.subject = subject
        dash_system.region = region
        try:
            dash_system.reload_curriculum()
        except Exception as e:
            logger.error(f"[SUBJECT_SWITCH] reload_curriculum failed for {subject}/{region}: {e}")
            # Continue with whatever skills are already loaded rather than crash
            if len(dash_system.skills) == 0:
                logger.warning(f"[SUBJECT_SWITCH] No skills loaded — assessment may fail")
        return True

# Configure CORS with secure origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=ALLOW_CREDENTIALS,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["*"],
)

# Serve generated images
_static_images_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "images")
os.makedirs(_static_images_dir, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=_static_images_dir), name="static_images")

# Helper function to ensure DASH system is initialized
def ensure_dash_system():
    """Ensure DASH system is initialized before use"""
    if dash_system is None:
        raise HTTPException(status_code=503, detail="DASHSystem not initialized")


def ensure_content_v1():
    """Ensure Content V1 engine is initialized before use."""
    if content_v1_engine is None:
        raise HTTPException(status_code=503, detail="ContentV1 engine not initialized")


def trigger_content_v1_queue_fill(profile_id: str, target_depth: int = 5) -> None:
    """Top up Content V1 queue in the background so API responses stay fast."""
    if content_v1_engine is None:
        return

    def _bg_fill() -> None:
        try:
            content_v1_engine.ensure_queue_depth(profile_id, target_depth=target_depth)
        except Exception as e:
            logger.warning(f"[CONTENT_V1] Background queue fill failed for {profile_id}: {e}")

    threading.Thread(target=_bg_fill, daemon=True).start()

# Startup event to initialize DASH system
@app.on_event("startup")
async def startup_event():
    """Initialize DASHSystem on startup.

    Works even with an empty database (0 skills). Curriculum will be
    generated on first student request via /api/start-subject.
    """
    global dash_system, content_v1_engine, curriculum_generator, quality_tracker, question_analytics, content_service
    logger.info("Initializing DASHSystem...")
    try:
        from managers.mongodb_manager import mongo_db
        from services.DashSystem.curriculum_generator import CurriculumGenerator

        content_v1_engine = ContentV1Engine()
        curriculum_generator = CurriculumGenerator(mongo_db, content_v1_engine)

        from services.DashSystem.question_analytics import QuestionAnalytics
        question_analytics = QuestionAnalytics(mongo_db.db)

        # Quality tracking feedback loop
        from services.DashSystem.quality_tracker import QualityTracker
        quality_tracker = QualityTracker(mongo_db.db, mongo_db.questions_db)
        logger.info("QualityTracker initialized")

        # DASH init — tolerant of 0 skills on fresh DB
        dash_system = DASHSystem(content_engine=content_v1_engine)
        qi_count = len(dash_system.question_index) if dash_system.question_index else 0
        ai_mode = "AI" if dash_system.use_ai_questions else "Khan"
        logger.info(
            f"DASHSystem initialized ({ai_mode} mode): "
            f"{len(dash_system.skills)} skills, {qi_count} questions in index"
        )
        # ContentGenerationService for pool-based question serving
        try:
            from services.DashSystem.content_generation_service import ContentGenerationService
            content_service = ContentGenerationService(
                db_ai_tutor=mongo_db.db,
                db_questions=mongo_db.questions_db,
                content_engine=content_v1_engine,
                verifier=content_v1_engine.verifier if hasattr(content_v1_engine, "verifier") else None,
            )
            if dash_system:
                dash_system.set_content_service(content_service)
            if quality_tracker:
                quality_tracker.content_service = content_service
            logger.info("ContentGenerationService initialized")
        except ImportError:
            logger.warning("ContentGenerationService not available (module not found). Pool-based serving disabled.")
        except Exception as e_cs:
            logger.warning(f"ContentGenerationService failed to initialize: {e_cs}. Pool-based serving disabled.")
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


class AnswerSubmission(BaseModel):
    question_id: str
    skill_ids: List[str]
    is_correct: bool
    response_time_seconds: float
    selected_answer: Optional[str] = None
    selected_answer_index: Optional[int] = None


class ResponsiveHintRequest(BaseModel):
    question_id: str
    skill_id: str
    question_text: str
    selected_answer: str
    correct_answer: str


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


class AdaptiveAssessmentAnswer(BaseModel):
    assessment_id: str
    question_id: str
    skill_id: str
    is_correct: bool


class AssessmentPrefetchRequest(BaseModel):
    assessment_id: str
    current_difficulty: float


class LearningPrefetchRequest(BaseModel):
    current_question_ids: List[str] = []


class ContentV1OnboardingRequest(BaseModel):
    age: int = Field(ge=5, le=18)
    learning_goal: str = Field(min_length=3, max_length=300)


class ContentV1SubmitRequest(BaseModel):
    learner_profile_id: str
    question_id: str
    is_correct: bool
    response_time_ms: int = Field(ge=0)
    signals: Dict = Field(default_factory=dict)


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
        "questions_count": len(dash_system.question_index) if dash_system.question_index else 0,
        "ai_questions_enabled": dash_system.use_ai_questions,
    }


@app.post("/api/content-v1/onboarding")
def content_v1_onboarding(request: Request, payload: ContentV1OnboardingRequest):
    """
    Start Content V1 with a learner profile, generated learning plan, and first question.
    """
    ensure_content_v1()
    user_id = get_current_user(request)

    memory = content_v1_engine._memory_context(user_id)
    plan = content_v1_engine.generate_learning_plan(payload.age, payload.learning_goal, memory)

    profile_id = f"c1p_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id[-6:]}"
    profile_doc = {
        "profile_id": profile_id,
        "learner_profile_id": profile_id,
        "user_id": user_id,
        "age": payload.age,
        "learning_goal": payload.learning_goal.strip(),
        "learning_plan": plan,
        "current_step_index": 0,
        "difficulty_cursor": 0.35,
        "topic_mastery": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    from managers.mongodb_manager import mongo_db
    mongo_db.db["content_v1_profiles"].insert_one(profile_doc)

    # Fast-path: generate first question directly so onboarding stays low-latency.
    topic, step_index = content_v1_engine._next_topic(profile_doc)
    first_doc = None
    first_error = None
    for _ in range(3):
        try:
            first_doc = content_v1_engine.create_or_reuse_question(
                user_id=user_id,
                profile_id=profile_id,
                learning_goal=payload.learning_goal.strip(),
                topic=topic,
                age=payload.age,
                difficulty=float(profile_doc.get("difficulty_cursor", 0.35)),
                fmt=random.choice(["radio_single", "radio_multi"]),
                memory=memory,
            )
            break
        except Exception as e:
            first_error = e

    if not first_doc:
        raise HTTPException(status_code=500, detail=f"Failed to generate first question for Content V1: {first_error}")

    first_question = content_v1_engine.to_question_payload(first_doc, topic, step_index)

    # Track first question as already served.
    mongo_db.db["content_v1_queue"].insert_one(
        {
            "profile_id": profile_id,
            "question_id": first_doc["question_id"],
            "step_index": step_index,
            "topic": topic,
            "status": "served",
            "created_at": datetime.utcnow(),
            "served_at": datetime.utcnow(),
        }
    )

    seed_text = (((first_doc.get("item") or {}).get("question") or {}).get("content") or "").strip()
    next_ready = 0
    if seed_text:
        try:
            next_ready = content_v1_engine.prime_queue_from_seed(
                profile_id=profile_id,
                user_id=user_id,
                learning_goal=payload.learning_goal.strip(),
                topic=topic,
                age=payload.age,
                difficulty=float(profile_doc.get("difficulty_cursor", 0.35)),
                step_index=step_index,
                seed_text=seed_text,
                count=5,
            )
        except Exception as e:
            logger.warning(f"[CONTENT_V1] Seed queue prime failed for {profile_id}: {e}")

    # Fill queue in background while user works on first question.
    trigger_content_v1_queue_fill(profile_id, target_depth=5)

    return {
        "learner_profile_id": profile_id,
        "learning_plan": plan,
        "first_question": first_question,
        "next_ready_count": next_ready,
    }


@app.get("/api/content-v1/questions/next")
def content_v1_next_question(request: Request, learner_profile_id: str):
    """
    Return next Content V1 question from queue. Queue is auto-refilled to depth 5.
    """
    ensure_content_v1()
    user_id = get_current_user(request)
    from managers.mongodb_manager import mongo_db

    profile = mongo_db.db["content_v1_profiles"].find_one(
        {"learner_profile_id": learner_profile_id, "user_id": user_id}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Content V1 learner profile not found")

    question = content_v1_engine.pop_next_question(learner_profile_id)
    if not question:
        # Fail-soft: try to materialize one question just-in-time.
        content_v1_engine.ensure_queue_depth(learner_profile_id, target_depth=1)
        question = content_v1_engine.pop_next_question(learner_profile_id)
    if not question:
        raise HTTPException(status_code=404, detail="No Content V1 question available")

    next_ready = mongo_db.db["content_v1_queue"].count_documents(
        {"profile_id": learner_profile_id, "status": "ready"}
    )
    trigger_content_v1_queue_fill(learner_profile_id, target_depth=5)
    return {"question": question, "next_ready_count": next_ready}


@app.post("/api/content-v1/questions/submit")
def content_v1_submit(request: Request, payload: ContentV1SubmitRequest):
    """
    Record Content V1 answer and update mastery/progression.
    """
    ensure_content_v1()
    user_id = get_current_user(request)
    from managers.mongodb_manager import mongo_db

    profile = mongo_db.db["content_v1_profiles"].find_one(
        {"learner_profile_id": payload.learner_profile_id, "user_id": user_id}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Content V1 learner profile not found")

    result = content_v1_engine.submit_result(
        payload.learner_profile_id,
        payload.question_id,
        payload.is_correct,
        payload.response_time_ms,
        payload.signals or {},
    )
    result["next_ready_count"] = mongo_db.db["content_v1_queue"].count_documents(
        {"profile_id": payload.learner_profile_id, "status": "ready"}
    )
    trigger_content_v1_queue_fill(payload.learner_profile_id, target_depth=5)
    return result


@app.get("/api/content-v1/plan")
def content_v1_plan(request: Request, learner_profile_id: str):
    """
    Return Content V1 plan + current progression state.
    """
    ensure_content_v1()
    user_id = get_current_user(request)
    from managers.mongodb_manager import mongo_db

    profile = mongo_db.db["content_v1_profiles"].find_one(
        {"learner_profile_id": learner_profile_id, "user_id": user_id},
        {"_id": 0},
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Content V1 learner profile not found")

    ready_count = mongo_db.db["content_v1_queue"].count_documents(
        {"profile_id": learner_profile_id, "status": "ready"}
    )
    return {
        "learner_profile_id": profile["learner_profile_id"],
        "learning_plan": profile.get("learning_plan", {}),
        "current_step_index": profile.get("current_step_index", 0),
        "difficulty_cursor": profile.get("difficulty_cursor", 0.35),
        "topic_mastery": profile.get("topic_mastery", {}),
        "next_ready_count": ready_count,
    }


def _load_ai_generated_perseus_items(ai_questions: List[Question]) -> List[Dict]:
    """Load Perseus items for AI-generated questions from ai_generated_questions collection."""
    from managers.mongodb_manager import mongo_db

    if not ai_questions:
        return []

    ai_question_ids = [q.question_id for q in ai_questions]
    ai_docs = list(mongo_db.ai_generated_questions.find(
        {"question_id": {"$in": ai_question_ids}}
    ))
    ai_lookup = {d["question_id"]: d for d in ai_docs}

    results = []
    for q in ai_questions:
        doc = ai_lookup.get(q.question_id)
        if not doc:
            logger.warning(f"[AI_LOAD] AI question {q.question_id} not found in ai_generated_questions")
            continue

        perseus_data = dict(doc["perseus_json"])
        # Build dash_metadata from stored doc
        skill_name = doc.get("skill_name", "AI Generated")
        lesson_name = doc.get("lesson_name", "")
        # Avoid duplicating skill_name as lesson_name
        if not lesson_name or lesson_name == skill_name:
            lesson_name = "Practice"

        perseus_data["dash_metadata"] = {
            "dash_question_id": doc["question_id"],
            "skill_ids": q.skill_ids,
            "difficulty": doc["difficulty"],
            "expected_time_seconds": 60.0,
            "slug": doc["question_id"],
            "skill_names": [skill_name],
            "unit_id": doc.get("skill_id", q.skill_ids[0] if q.skill_ids else "unknown"),
            "lesson_id": doc.get("lesson_id", doc.get("skill_id", "")),
            "exercise_id": "ai_generated",
            "mongodb_id": str(doc.get("_id", doc["question_id"])),
            "unit_name": skill_name,
            "lesson_name": lesson_name,
            "exercise_name": {
                "radio_single": "Multiple Choice",
                "radio_multi": "Select All",
                "orderer": "Ordering",
            }.get(doc.get("format", ""), "Practice"),
            "ai_generated": True,
            "source": doc.get("source", "gemini"),
        }
        # Patch missing/malformed widget fields before serving
        widgets = perseus_data.get("question", {}).get("widgets", {})
        for wkey, wval in widgets.items():
            if not isinstance(wval, dict):
                continue
            wtype = wval.get("type", "")
            opts = wval.get("options", {})

            # Fix radio: options is a list instead of {"choices": [...]}
            if wtype == "radio" and isinstance(opts, list):
                choices = opts
                # Preserve any extra fields that were at widget level
                multi = wval.pop("multipleSelect", False)
                rand = wval.pop("randomize", False)
                wval["options"] = {"choices": choices}
                wval["options"].setdefault("multipleSelect", multi)
                wval["options"].setdefault("randomize", rand)
                wval["options"].setdefault("deselectEnabled", False)
                wval["options"].setdefault("displayCount", None)
                wval["options"].setdefault("hasNoneOfTheAbove", False)
                wval["options"].setdefault("countChoices", False)
                logger.info(f"[AI_LOAD] Fixed radio options: list → dict for {q.question_id}")

            # Fix numeric-input: ensure required fields
            if wtype == "numeric-input":
                opts = wval.setdefault("options", {})
                opts.setdefault("coefficient", False)
                opts.setdefault("static", False)
                opts.setdefault("labelText", "")
                opts.setdefault("size", "normal")

        results.append(perseus_data)

    logger.info(f"[AI_LOAD] Loaded {len(results)} AI-generated Perseus items")
    return results


def _strip_objectids(obj):
    """Recursively convert bson ObjectId instances to strings and sanitize
    control characters so the JSON response is always parseable by browsers."""
    from bson import ObjectId
    if isinstance(obj, dict):
        return {k: _strip_objectids(v) for k, v in obj.items() if k != "_id"}
    if isinstance(obj, list):
        return [_strip_objectids(v) for v in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, str):
        # Strip ASCII control characters (0x00-0x1F except \t \n \r)
        # that could cause JSON parsing failures in browsers
        return "".join(c if c >= " " or c in "\t\n\r" else " " for c in obj)
    return obj


def load_perseus_items_for_dash_questions_from_mongodb(
    dash_questions: List[Question]
) -> List[Dict]:
    """Load Perseus items for DASH-selected questions.

    Questions with perseus_data already attached (warm-start, pool) are used directly.
    Routes AI-generated questions (ai_q_ prefix) to ai_generated_questions collection
    and Khan questions to questions_db.questions collection.
    """
    from managers.mongodb_manager import mongo_db
    import json

    results = []
    need_loading = []

    # First pass: extract questions that already have Perseus data (warm-start/pool)
    for q in dash_questions:
        pd = getattr(q, "perseus_data", None)
        if pd:
            results.append(pd)
        else:
            need_loading.append(q)

    if not need_loading:
        try:
            from pre_serve_validator import validate_pre_serve
        except Exception:
            # Validator unavailable — pass through all results
            return [_strip_objectids(r) for r in results]
        validated = []
        for r in results:
            _patch_numeric_input_widgets(r)
            dm = r.get("dash_metadata", {})
            skill_ids = dm.get("skill_ids", []) if isinstance(dm, dict) else []
            try:
                vr = validate_pre_serve(
                    r,
                    skill_id=skill_ids[0] if skill_ids else None,
                    db_collection=mongo_db.db["validation_failures"],
                )
                if vr.passed:
                    validated.append(_strip_objectids(r))
                else:
                    logger.warning(f"[LOAD_PERSEUS] Warm-start pre-serve REJECT: {vr.failures}")
            except Exception as e:
                logger.warning(f"[LOAD_PERSEUS] Warm-start validator error: {e}")
                validated.append(_strip_objectids(r))
        return validated

    # Split remaining questions by source
    ai_questions = [q for q in need_loading if q.question_id.startswith("ai_q_")]
    khan_questions = [q for q in need_loading if not q.question_id.startswith("ai_q_")]

    # Load AI-generated questions
    if ai_questions:
        results.extend(_load_ai_generated_perseus_items(ai_questions))

    # Load Khan questions via original path
    if khan_questions:
        results.extend(_load_khan_perseus_items(khan_questions))

    # Patch all widget types with required defaults, then validate
    try:
        from pre_serve_validator import validate_pre_serve
    except Exception:
        # Validator unavailable — pass through all results
        for r in results:
            _patch_numeric_input_widgets(r)
        return [_strip_objectids(r) for r in results]
    validated = []
    for r in results:
        _patch_numeric_input_widgets(r)
        dm = r.get("dash_metadata", {})
        skill_ids = dm.get("skill_ids", []) if isinstance(dm, dict) else []
        try:
            vr = validate_pre_serve(
                r,
                skill_id=skill_ids[0] if skill_ids else None,
                subject=None,
                db_collection=mongo_db.db["validation_failures"],
            )
            if vr.passed:
                validated.append(_strip_objectids(r))
            else:
                logger.warning(f"[LOAD_PERSEUS] Batch pre-serve REJECT: {vr.failures}")
        except Exception as e:
            logger.warning(f"[LOAD_PERSEUS] Batch validator error: {e}")
            validated.append(_strip_objectids(r))

    return validated


def _load_khan_perseus_items(khan_questions: List[Question]) -> List[Dict]:
    """Load Perseus items from questions_db.questions collection for Khan questions.

    OPTIMIZED: Uses batch query with $in instead of one query per question.
    """
    from managers.mongodb_manager import mongo_db
    import json

    if not khan_questions:
        return []

    # Build lookup map for DASH metadata
    dash_lookup = {q.question_id: q for q in khan_questions}
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
    if sample_size < 1 or sample_size > 50:
        raise HTTPException(status_code=422, detail="sample_size must be between 1 and 50")
    # Get user_id and age from JWT token
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age")

    logger.info(f"\n{'='*80}")
    logger.info(f"[NEW_SESSION] Requesting {sample_size} questions for user: {user_id}")
    logger.info(f"{'='*80}\n")

    # Ensure the user exists and is loaded (age from JWT fallback if not in MongoDB)
    user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
    
    # Use DASH intelligence with flexible selection to get ALL questions
    current_time = time.time()
    selected_questions = []
    selected_question_ids = []  # Track selected question IDs to avoid duplicates
    selected_content_hashes = set()  # Track content hashes to catch identical-content duplicates
    
    # --- Check warm-start cache for Q1 (pre-generated by start_subject) ---
    warmstart_key = f"{user_id}:{dash_system.subject.lower()}"
    with _warmstart_lock:
        cached = _warmstart_cache.pop(warmstart_key, None)
        pending_evt = _warmstart_events.get(warmstart_key)

    if not cached and pending_evt:
        logger.info(f"[LEARNING_PATH] Waiting for in-flight warm-start ({warmstart_key})...")
        pending_evt.wait(timeout=WARMSTART_WAIT_TIMEOUT)
        with _warmstart_lock:
            cached = _warmstart_cache.pop(warmstart_key, None)
            if not cached:
                # Timeout expired — clean up stale event to prevent memory leak
                _warmstart_events.pop(warmstart_key, None)

    if cached and time.time() - cached.get("ts", 0) < WARMSTART_TTL:
        from services.DashSystem.dash_system import Question
        q_data = cached["q_data"]
        warmstart_q = Question(
            question_id=cached["question_id"],
            skill_ids=[cached.get("skill_id", "")] if cached.get("skill_id") else [],
            content="", difficulty=0.5, expected_time_seconds=60.0,
            perseus_data=q_data,
        )
        selected_questions.append(warmstart_q)
        selected_question_ids.append(warmstart_q.question_id)
        selected_content_hashes.add(_compute_content_hash(q_data))
        logger.info(f"[LEARNING_PATH] Warm-start HIT: {warmstart_q.question_id}")

    # Get Q1 from warm-start or serial DASH call
    remaining = sample_size - len(selected_questions)
    if remaining > 0 and len(selected_questions) == 0:
        q1 = dash_system.get_next_question_flexible(
            user_id, current_time,
            exclude_question_ids=selected_question_ids,
            user_profile=user_profile,
            fast_mode=True,
        )
        if q1:
            selected_questions.append(q1)
            selected_question_ids.append(q1.question_id)
        remaining = sample_size - len(selected_questions)

    # Q2-Q5: skill-assigned parallel generation for speed
    if remaining > 0:
        # Pre-select diverse skills via DASH intelligence (fast, no Gemini)
        recommended_skills = dash_system.get_recommended_skills(
            user_id, current_time,
            cold_start_grade_filter=user_profile.current_grade if dash_system.is_cold_start(user_profile) else None,
            grade_range=1,
        )
        # Take skills beyond Q1's skill for diversity
        q1_skill_ids = set()
        if selected_questions:
            q1_skill_ids = set(selected_questions[0].skill_ids or [])
        target_skill_ids = [sid for sid in recommended_skills if sid not in q1_skill_ids][:remaining + 2]

        exclude_snapshot = set(selected_question_ids)

        def _fetch_for_skill(skill_id):
            skill = dash_system.skills.get(skill_id)
            if not skill:
                return None
            try:
                # Pool pop first
                if dash_system.content_service:
                    pool_q = dash_system.content_service.pop_question(
                        skill_id, skill.difficulty, exclude_ids=exclude_snapshot,
                        subject=dash_system.subject or "")
                    if pool_q:
                        q_id = pool_q.get("question_id", pool_q.get("dash_metadata", {}).get("dash_question_id", f"pool_{skill_id}"))
                        if "dash_metadata" not in pool_q:
                            pool_q["dash_metadata"] = {
                                "dash_question_id": q_id,
                                "skill_ids": [skill_id],
                                "difficulty": pool_q.get("difficulty", skill.difficulty),
                                "skill_names": [skill.name],
                                "unit_name": skill.name,
                                "lesson_name": "Practice",
                                "ai_generated": True,
                            }
                        from services.DashSystem.dash_system import Question
                        return Question(
                            question_id=q_id,
                            skill_ids=[skill_id],
                            content="",
                            difficulty=pool_q.get("difficulty", skill.difficulty),
                            expected_time_seconds=60.0,
                            perseus_data=pool_q,
                        )
                # JIT fallback
                if dash_system.use_ai_questions and dash_system.ai_provider:
                    ai_result = dash_system.ai_provider.get_question_for_skill(
                        skill_id=skill_id,
                        skill_name=skill.name,
                        target_difficulty=skill.difficulty,
                        grade_level=skill.grade_level.name,
                        age=user_profile.age if user_profile.age else 7,
                        exclude_question_ids=exclude_snapshot,
                        user_id=user_id,
                        subject=dash_system.subject or "",
                    )
                    if ai_result:
                        q_id = ai_result["dash_metadata"]["dash_question_id"]
                        from services.DashSystem.dash_system import Question
                        return Question(
                            question_id=q_id,
                            skill_ids=[skill_id],
                            content="",
                            difficulty=ai_result["dash_metadata"]["difficulty"],
                            expected_time_seconds=60.0,
                        )
                return None
            except Exception as e:
                logger.warning(f"[PARALLEL_FETCH] Failed for {skill_id}: {e}")
                return None

        if target_skill_ids:
            with ThreadPoolExecutor(max_workers=min(len(target_skill_ids), 4)) as pool:
                futures = [pool.submit(_fetch_for_skill, sid) for sid in target_skill_ids]
                for future in as_completed(futures):
                    if len(selected_questions) >= sample_size:
                        break
                    result = future.result()
                    if result and result.question_id not in selected_question_ids:
                        # Content-hash dedup: check for identical content from different IDs
                        q_data_check = getattr(result, "perseus_data", None)
                        if q_data_check:
                            ch = _compute_content_hash(q_data_check)
                            if ch in selected_content_hashes:
                                logger.info(f"[LEARNING_PATH] Content-hash dup: {result.question_id} — skipping")
                                continue
                            selected_content_hashes.add(ch)
                        selected_questions.append(result)
                        selected_question_ids.append(result.question_id)
        else:
            # No diverse skills found — fall back to serial DASH selection
            for i in range(remaining):
                q = dash_system.get_next_question_flexible(
                    user_id, current_time,
                    exclude_question_ids=selected_question_ids,
                    user_profile=user_profile,
                )
                if q:
                    selected_questions.append(q)
                    selected_question_ids.append(q.question_id)
                else:
                    break

        if len(selected_questions) < sample_size:
            logger.info(f"[SESSION_END] Selected {len(selected_questions)}/{sample_size} questions (no more available)")
    
    # Development bypass: if no questions selected, just get random ones from DB
    if not selected_questions and os.getenv("DEV_MODE", "true").lower() == "true":
        logger.warning(f"[DEV_BYPASS] No DASH questions selected, fetching {sample_size} random questions from Perseus DB")
        if dash_system.mongo:
            random_perseus = list(dash_system.mongo.perseus_questions.aggregate([
                {"$sample": {"size": sample_size}}
            ]))
            if random_perseus:
                logger.info(f"[DEV_BYPASS] Found {len(random_perseus)} random Perseus questions")
                return [_strip_objectids(q) for q in random_perseus]
    
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

    # Trigger learning-path prefetch for next question in background
    all_served_ids = list(selected_question_ids)
    _trigger_learning_prefetch(user_id, all_served_ids, jwt_age if jwt_age else 10)

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
    
    # Show current student state from question_attempts
    try:
        attempts_count = dash_system.mongo.question_attempts.count_documents({"user_id": user_id})
        if attempts_count > 0:
            logger.info(f"\n[STUDENT_STATE] {attempts_count} total question attempts recorded")
    except Exception as e:
        logger.debug(f"Could not fetch student state: {e}")
    
    logger.info(f"{'='*80}\n")
    return {"success": True}


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

    # Track used_count for AI-generated questions
    if answer.question_id.startswith("ai_q_"):
        try:
            mongo_db.ai_generated_questions.update_one(
                {"question_id": answer.question_id},
                {"$inc": {"used_count": 1}, "$set": {"last_served_at": datetime.now()}},
            )
        except Exception as e:
            logger.warning(f"[SUBMIT_ANSWER] AI question used_count update failed: {e}")

    # Track misconception on wrong answers (for AI-generated questions with choice data)
    if not answer.is_correct and answer.selected_answer is not None:
        try:
            q_doc = mongo_db.ai_generated_questions.find_one({"question_id": answer.question_id})
            if q_doc:
                perseus = q_doc.get("perseus_data") or q_doc
                widgets = perseus.get("question", {}).get("widgets", {})
                misconception_text = None
                for wid, wdef in widgets.items():
                    if wdef.get("type") in ("radio", "dropdown"):
                        choices = wdef.get("options", {}).get("choices", [])
                        if answer.selected_answer_index is not None and answer.selected_answer_index < len(choices):
                            misconception_text = choices[answer.selected_answer_index].get("misconception")
                        if not misconception_text:
                            # Try matching by content text
                            for c in choices:
                                if c.get("content") == answer.selected_answer and not c.get("correct"):
                                    misconception_text = c.get("misconception")
                                    break
                        break
                if misconception_text:
                    mongo_db.db["student_misconceptions"].update_one(
                        {"user_id": user_id, "misconception": misconception_text, "skill_id": answer.skill_ids[0] if answer.skill_ids else "unknown"},
                        {"$inc": {"count": 1}, "$set": {"last_seen": datetime.now()}, "$setOnInsert": {"first_seen": datetime.now()}},
                        upsert=True,
                    )
                    logger.info(f"[MISCONCEPTION] Tracked: {misconception_text[:60]} for user {user_id}")
        except Exception as e:
            logger.warning(f"[SUBMIT_ANSWER] Misconception tracking failed: {e}")

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

    # Include mastery level updates for affected skills
    mastery_update = {}
    for skill_id in answer.skill_ids:
        if skill_id in dash_system.skills:
            mastery_update[skill_id] = dash_system.get_mastery_level(user_id, skill_id, current_time)

    return {
        "success": True,
        "affected_skills": affected_skills,
        "message": "Answer recorded successfully",
        "mastery_update": mastery_update,
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

@app.get("/api/prerequisites/{skill_id}")
def get_prerequisites(skill_id: str, request: Request):
    """
    Get prerequisite status for a skill. Returns whether prerequisites are met,
    which ones are missing, and where to redirect the student.
    """
    ensure_dash_system()
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    current_time = time.time()

    try:
        result = dash_system.check_prerequisites(user_id, skill_id, current_time)
        return result
    except Exception as e:
        logger.error(f"[ERROR] Error checking prerequisites for {skill_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/responsive-hint")
def get_responsive_hint(request: Request, req: ResponsiveHintRequest):
    """
    Generate a targeted Socratic hint based on the student's specific wrong answer.
    Uses Gemini to produce a brief, error-aware hint.
    """
    ensure_dash_system()
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age", 10)

    if not content_v1_engine:
        raise HTTPException(status_code=503, detail="Content engine not available")

    from managers.mongodb_manager import mongo_db

    # Look up skill name
    skill_name = req.skill_id
    if dash_system and req.skill_id in dash_system.skills:
        skill_name = dash_system.skills[req.skill_id].name

    # Try to look up misconception from the question's Perseus data
    misconception = ""
    try:
        q_doc = mongo_db.ai_generated_questions.find_one({"question_id": req.question_id})
        if q_doc:
            perseus = q_doc.get("perseus_data") or q_doc
            widgets = perseus.get("question", {}).get("widgets", {})
            for wdef in widgets.values():
                if wdef.get("type") in ("radio", "dropdown"):
                    for c in wdef.get("options", {}).get("choices", []):
                        if c.get("content") == req.selected_answer and not c.get("correct"):
                            misconception = c.get("misconception", "") or ""
                            break
                    break
    except Exception:
        pass

    hint_text = content_v1_engine.generate_responsive_hint(
        skill_name=skill_name,
        question_text=req.question_text,
        selected_answer=req.selected_answer,
        correct_answer=req.correct_answer,
        age=int(jwt_age) if jwt_age else 10,
        misconception=misconception,
    )

    if hint_text:
        return {"hint_content": hint_text, "skill_name": skill_name}
    else:
        return {"hint_content": "Try re-reading the question carefully. Look at each answer choice and think about why it might or might not be correct.", "skill_name": skill_name}

@app.get("/api/misconceptions")
def get_misconceptions(request: Request):
    """
    Get active misconceptions for the current user, sorted by frequency.
    """
    ensure_dash_system()
    from managers.mongodb_manager import mongo_db
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")

    try:
        docs = list(
            mongo_db.db["student_misconceptions"]
            .find({"user_id": user_id}, {"_id": 0})
            .sort("count", -1)
            .limit(50)
        )
        return {"misconceptions": docs, "total": len(docs)}
    except Exception as e:
        logger.error(f"[ERROR] Error fetching misconceptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/review-status")
def get_review_status(request: Request):
    """
    Get skills due for review (previously mastered but decayed).
    Returns count and skill list for frontend review banner.
    """
    ensure_dash_system()
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    current_time = time.time()

    try:
        review_ids = dash_system.get_skills_due_for_review(user_id, current_time)
        skills_info = []
        for sid in review_ids[:10]:  # Cap at 10 for the response
            skill = dash_system.skills.get(sid)
            if skill:
                prob = dash_system.predict_correctness(user_id, sid, current_time)
                skills_info.append({
                    "skill_id": sid,
                    "skill_name": skill.name,
                    "current_probability": round(prob, 3),
                    "grade_level": skill.grade_level.name,
                })
        return {"skills_due_for_review": skills_info, "total_due": len(review_ids)}
    except Exception as e:
        logger.error(f"[ERROR] Error getting review status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age")

    logger.info(f"\n{'='*80}")
    logger.info(f"[RECOMMEND_NEXT] User: {user_id}, Current questions: {len(req.current_question_ids)}, Requesting: {req.count}")
    logger.info(f"{'='*80}\n")

    # Ensure the user exists and is loaded
    user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
    current_time = time.time()
    
    # Get next questions via skill-assigned parallel generation
    selected_questions = []
    collected_ids = set(req.current_question_ids)
    collected_content_hashes: set = set()

    # --- Check learning-path prefetch cache for Q1 ---
    with _learning_prefetch_lock:
        cached = _learning_prefetch_cache.pop(user_id, None)

    if cached and time.time() - cached.get("ts", 0) < LEARNING_PREFETCH_TTL:
        cached_qid = cached["question_id"]
        if cached_qid not in collected_ids:
            from services.DashSystem.dash_system import Question
            prefetch_q = Question(
                question_id=cached_qid,
                skill_ids=[cached.get("skill_id", "")] if cached.get("skill_id") else [],
                content="", difficulty=0.5, expected_time_seconds=60.0,
                perseus_data=cached["q_data"],
            )
            ch = _compute_content_hash(cached["q_data"])
            collected_content_hashes.add(ch)
            selected_questions.append(prefetch_q)
            collected_ids.add(cached_qid)
            logger.info(f"[RECOMMEND_NEXT] Prefetch cache HIT: {cached_qid}")
        else:
            logger.info(f"[RECOMMEND_NEXT] Prefetch cache STALE (duplicate {cached_qid}), discarding")
    elif cached:
        logger.info(f"[RECOMMEND_NEXT] Prefetch cache EXPIRED for {user_id}")

    # Pre-select diverse skills (fast, no Gemini)
    recommended_skills = dash_system.get_recommended_skills(
        user_id, current_time,
        cold_start_grade_filter=user_profile.current_grade if dash_system.is_cold_start(user_profile) else None,
        grade_range=1,
    )
    # Exclude skills from current questions to diversify
    current_skill_ids = set()
    for qid in req.current_question_ids:
        for q_doc in [dash_system.skills.get(sid) for sid in dash_system.skills]:
            pass  # Skip complex lookup — just use all recommended skills
    target_skill_ids = recommended_skills[:req.count + 2]

    def _fetch_for_skill_rec(skill_id):
        skill = dash_system.skills.get(skill_id)
        if not skill:
            return None
        try:
            if dash_system.content_service:
                pool_q = dash_system.content_service.pop_question(
                    skill_id, skill.difficulty, exclude_ids=collected_ids,
                    subject=dash_system.subject or "")
                if pool_q:
                    q_id = pool_q.get("question_id", pool_q.get("dash_metadata", {}).get("dash_question_id", f"pool_{skill_id}"))
                    if "dash_metadata" not in pool_q:
                        pool_q["dash_metadata"] = {
                            "dash_question_id": q_id,
                            "skill_ids": [skill_id],
                            "difficulty": pool_q.get("difficulty", skill.difficulty),
                            "skill_names": [skill.name],
                            "unit_name": skill.name,
                            "lesson_name": "Practice",
                            "ai_generated": True,
                        }
                    from services.DashSystem.dash_system import Question
                    return Question(
                        question_id=q_id, skill_ids=[skill_id], content="",
                        difficulty=pool_q.get("difficulty", skill.difficulty),
                        expected_time_seconds=60.0, perseus_data=pool_q,
                    )
            if dash_system.use_ai_questions and dash_system.ai_provider:
                ai_result = dash_system.ai_provider.get_question_for_skill(
                    skill_id=skill_id, skill_name=skill.name,
                    target_difficulty=skill.difficulty,
                    grade_level=skill.grade_level.name,
                    age=user_profile.age if user_profile.age else 7,
                    exclude_question_ids=collected_ids, user_id=user_id,
                    subject=dash_system.subject or "",
                )
                if ai_result:
                    q_id = ai_result["dash_metadata"]["dash_question_id"]
                    from services.DashSystem.dash_system import Question
                    return Question(
                        question_id=q_id, skill_ids=[skill_id], content="",
                        difficulty=ai_result["dash_metadata"]["difficulty"],
                        expected_time_seconds=60.0,
                    )
            return None
        except Exception as e:
            logger.warning(f"[RECOMMEND_NEXT] Fetch failed for {skill_id}: {e}")
            return None

    if target_skill_ids:
        with ThreadPoolExecutor(max_workers=min(len(target_skill_ids), 4)) as pool:
            futures = [pool.submit(_fetch_for_skill_rec, sid) for sid in target_skill_ids]
            for future in as_completed(futures):
                if len(selected_questions) >= req.count:
                    break
                result = future.result()
                if result and result.question_id not in collected_ids:
                    # Content-hash dedup for identical content from different pools
                    q_data_check = getattr(result, "perseus_data", None)
                    if q_data_check:
                        ch = _compute_content_hash(q_data_check)
                        if ch in collected_content_hashes:
                            logger.info(f"[RECOMMEND_NEXT] Content-hash dup: {result.question_id} — skipping")
                            continue
                        collected_content_hashes.add(ch)
                    selected_questions.append(result)
                    collected_ids.add(result.question_id)

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
        
        # Trigger learning-path prefetch for the next batch in background
        all_served_ids = list(collected_ids)
        _trigger_learning_prefetch(user_id, all_served_ids, jwt_age if jwt_age else 10)

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

    # Normalize subject casing to match curriculum storage (e.g. "python" → "Python")
    subject = subject.strip().title()

    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age")
    logger.info(f"\n{'='*80}")
    logger.info(f"[ASSESSMENT] Starting assessment for subject: {subject}, user: {user_id}")
    logger.info(f"{'='*80}\n")

    # Switch DASH system to requested subject if needed (thread-safe)
    region = "US"
    _switch_subject_if_needed(subject, region)

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
                "total": existing.get("total", 10),
                "date": existing.get("assessment_date")
            }

        # Get user's current grade (use JWT age as fallback for new users)
        user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
        # Normalize grade — handles "Grade 8", "GRADE_8", "grade_8", "K", int 8, etc.
        raw_grade = user_profile.current_grade
        if raw_grade is None:
            raw_grade = "GRADE_5"  # Safe default when profile has no grade
        if isinstance(raw_grade, (int, float)):
            # Numeric grade (e.g. 8 or 0 for K)
            grade_key = "K" if int(raw_grade) == 0 else f"GRADE_{int(raw_grade)}"
        else:
            grade_str = str(raw_grade).strip()
            grade_key = grade_str.upper().replace(" ", "_")
            # Handle bare numbers: "8" → "GRADE_8"
            if grade_key.isdigit():
                grade_key = f"GRADE_{grade_key}"
            elif grade_key.startswith("GRADE") and not grade_key.startswith("GRADE_"):
                grade_key = grade_key.replace("GRADE", "GRADE_", 1)
        try:
            current_grade_value = GradeLevel[grade_key].value
        except KeyError:
            logger.warning(f"[ASSESSMENT] Unknown grade '{raw_grade}', defaulting to K")
            current_grade_value = GradeLevel.K.value

        logger.info(f"[ASSESSMENT] User grade: {user_profile.current_grade} (value: {current_grade_value})")

        # Get 10 assessment questions via skill-assigned parallel generation
        questions = []
        exclude_question_ids = set()
        current_time = time.time()

        # Pre-select 10 diverse skills from curriculum (fast, no Gemini)
        all_skills = list(dash_system.skills.values())
        random.shuffle(all_skills)
        # Pick up to 10 unique skills, spread across grades
        target_skills = all_skills[:min(len(all_skills), 12)]
        logger.info(f"[ASSESSMENT] Pre-selected {len(target_skills)} target skills for parallel generation")

        student_age = user_profile.age if user_profile.age else 10

        def _generate_for_skill(skill):
            """Generate one question for an assigned skill — pool pop first, then fast JIT."""
            try:
                # Try pool pop first (fast, ~1ms)
                if dash_system.content_service:
                    pool_q = dash_system.content_service.pop_question(
                        skill.skill_id, skill.difficulty,
                        subject=dash_system.subject or "")
                    if pool_q:
                        q_id = pool_q.get("question_id", pool_q.get("dash_metadata", {}).get("dash_question_id", f"pool_{skill.skill_id}"))
                        if "dash_metadata" not in pool_q:
                            pool_q["dash_metadata"] = {
                                "dash_question_id": q_id,
                                "skill_ids": [skill.skill_id],
                                "difficulty": pool_q.get("difficulty", skill.difficulty),
                                "skill_names": [skill.name],
                                "unit_name": skill.name,
                                "lesson_name": "Assessment",
                                "ai_generated": True,
                            }
                        return Question(
                            question_id=q_id,
                            skill_ids=[skill.skill_id],
                            content="",
                            difficulty=pool_q.get("difficulty", skill.difficulty),
                            expected_time_seconds=60.0,
                            perseus_data=pool_q,
                        )

                # Pool miss — fast JIT generation (1 attempt, 10s timeout, accepts unverified)
                if dash_system.use_ai_questions and dash_system.ai_provider:
                    ai_result = dash_system.ai_provider.get_question_for_skill(
                        skill_id=skill.skill_id,
                        skill_name=skill.name,
                        target_difficulty=skill.difficulty,
                        grade_level=skill.grade_level.name,
                        age=student_age,
                        exclude_question_ids=exclude_question_ids,
                        user_id=user_id,
                        fast_mode=True,
                        subject=dash_system.subject or "",
                    )
                    if ai_result:
                        q_id = ai_result["dash_metadata"]["dash_question_id"]
                        return Question(
                            question_id=q_id,
                            skill_ids=[skill.skill_id],
                            content="",
                            difficulty=ai_result["dash_metadata"]["difficulty"],
                            expected_time_seconds=60.0,
                        )
                return None
            except Exception as e:
                logger.warning(f"[ASSESSMENT] Generation failed for {skill.name}: {e}")
                return None

        # Each thread gets a DIFFERENT skill — no competition
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(_generate_for_skill, skill): skill for skill in target_skills}
            for future in as_completed(futures):
                if len(questions) >= 10:
                    break
                result = future.result()
                if result and result.question_id not in exclude_question_ids:
                    questions.append(result)
                    exclude_question_ids.add(result.question_id)

        logger.info(f"[ASSESSMENT] Parallel generation returned {len(questions)}/10 questions")

        if len(questions) == 0:
            logger.error(f"[ASSESSMENT] No questions available after all fallbacks")
            raise HTTPException(status_code=400, detail="No questions available for assessment")

        total_questions = len(questions)
        if total_questions < 10:
            logger.warning(f"[ASSESSMENT] Only {total_questions}/10 questions — proceeding with partial assessment")

        # Load Perseus items for the questions
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(questions)

        if not perseus_items:
            logger.error(f"[ASSESSMENT] Failed to load any Perseus items")
            raise HTTPException(status_code=400, detail="Failed to load assessment questions")

        if len(perseus_items) < total_questions:
            logger.warning(f"[ASSESSMENT] Loaded {len(perseus_items)}/{total_questions} Perseus items (some missing)")

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
    subject = payload.subject.strip().title()
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
                    "answers": [a.model_dump() for a in answers],
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
    subject = subject.strip().title()

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


# ===== ADAPTIVE ASSESSMENT ENDPOINTS (CAT-style) =====

@app.post("/assessment/start-adaptive/{subject}")
def start_adaptive_assessment(subject: str, request: Request):
    """
    Start an adaptive (CAT-style) assessment. Returns assessment_id + first question.
    Questions are served one at a time; difficulty adjusts based on each answer.
    """
    try:
        ensure_dash_system()
        from managers.mongodb_manager import mongo_db
        import uuid

        # Normalize subject casing to match curriculum storage (e.g. "python" → "Python")
        subject = subject.strip().title()

        jwt_payload = get_jwt_payload(request)
        user_id = jwt_payload.get("sub")
        jwt_age = jwt_payload.get("age")

        # Switch DASH system to requested subject if needed (thread-safe)
        region = "US"
        _switch_subject_if_needed(subject, region)

        # Check if already completed
        existing = mongo_db.subject_assessments.find_one({
            "user_id": user_id, "subject": subject, "assessment_completed": True
        })
        if existing:
            return {
                "error": "Assessment already completed",
                "score": existing.get("score", 0),
                "total": existing.get("total", 0),
            }

        user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
        current_time = time.time()

        # Create assessment session
        assessment_id = f"assess_{uuid.uuid4().hex[:12]}"
        session = {
            "assessment_id": assessment_id,
            "user_id": user_id,
            "subject": subject,
            "current_difficulty": 0.5,
            "questions_asked": 0,
            "max_questions": 10,
            "answers": [],
            "used_question_ids": [],
            "used_skill_ids": [],
            "used_content_hashes": [],
            "created_at": datetime.now(),
            "status": "in_progress",
        }
        mongo_db.db["assessment_sessions"].insert_one(session)

        # --- Check warm-start cache first (pre-generated by start_subject) ---
        first_q = None
        q_data = None
        warmstart_key = f"{user_id}:{subject.lower()}"

        # Check if warm-start is still in-flight; if so, wait for it
        with _warmstart_lock:
            cached = _warmstart_cache.pop(warmstart_key, None)
            pending_evt = _warmstart_events.get(warmstart_key)

        if not cached and pending_evt:
            logger.info(f"[ADAPTIVE_ASSESSMENT] Waiting for in-flight warm-start ({warmstart_key})...")
            pending_evt.wait(timeout=WARMSTART_WAIT_TIMEOUT)
            with _warmstart_lock:
                cached = _warmstart_cache.pop(warmstart_key, None)
                if not cached:
                    # Timeout expired — clean up stale event to prevent memory leak
                    _warmstart_events.pop(warmstart_key, None)
            if cached:
                logger.info(f"[ADAPTIVE_ASSESSMENT] Warm-start completed while waiting")

        if cached and time.time() - cached.get("ts", 0) < WARMSTART_TTL:
            q_data = cached["q_data"]
            first_q = Question(
                question_id=cached["question_id"],
                skill_ids=[cached.get("skill_id", "")] if cached.get("skill_id") else [],
                content="",
                difficulty=0.5,
                expected_time_seconds=60.0,
            )
            logger.info(f"[ADAPTIVE_ASSESSMENT] Warm-start HIT: {first_q.question_id}")

        # --- Fall through to DASH pool if no warm-start ---
        if not first_q:
            first_q = dash_system.get_next_question_flexible(
                user_id, current_time, user_profile=user_profile, fast_mode=True,
                force_grade_range=True,
            )

        # JIT fallback: generate a question for new subjects without curriculum
        if not first_q and dash_system.use_ai_questions and dash_system.ai_provider:
            grade_name = user_profile.current_grade.replace("GRADE_", "Grade ").replace("K", "Kindergarten")
            synthetic_id = f"assessment_{subject.lower().replace(' ', '_')}_{user_profile.current_grade.lower()}_0"
            logger.info(f"[ADAPTIVE_ASSESSMENT] No curriculum questions — JIT generating for {subject}/{grade_name}")
            try:
                ai_result = dash_system.ai_provider.get_question_for_skill(
                    skill_id=synthetic_id,
                    skill_name=f"{subject} for {grade_name}",
                    target_difficulty=0.5,
                    grade_level=user_profile.current_grade,
                    age=user_profile.age if user_profile.age else 10,
                    exclude_question_ids=[],
                    user_id=user_id,
                    fast_mode=True,
                    subject=subject,
                )
                if ai_result:
                    first_q = Question(
                        question_id=ai_result["dash_metadata"]["dash_question_id"],
                        skill_ids=[synthetic_id],
                        content="",
                        difficulty=ai_result["dash_metadata"]["difficulty"],
                        expected_time_seconds=60.0,
                    )
                    logger.info(f"[ADAPTIVE_ASSESSMENT] JIT generated Q:{first_q.question_id}")
            except Exception as e:
                logger.warning(f"[ADAPTIVE_ASSESSMENT] JIT generation failed: {e}")

        if not first_q:
            # Last resort: try any grade (no grade range restriction)
            first_q = dash_system.get_next_question_flexible(
                user_id, current_time, user_profile=user_profile, fast_mode=True,
            )
        if not first_q:
            raise HTTPException(status_code=400, detail="No questions available for assessment")

        # Load Perseus data (warm-start already has it; pool/JIT need loading)
        if not q_data:
            q_data = getattr(first_q, "perseus_data", None) or _load_question_perseus(first_q.question_id, mongo_db)
        if not q_data:
            raise HTTPException(status_code=500, detail="Failed to load question data")

        # Skip questions with only broken widget types (orderer/matcher — unsupported in React 18)
        if _has_only_broken_widgets(q_data):
            logger.info(f"[ADAPTIVE_ASSESSMENT] Skipping broken-widget-only question {first_q.question_id} — retrying")
            q_data = None
            user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
            current_time = time.time()
            for _retry in range(3):
                alt_q = dash_system.get_next_question_flexible(
                    user_id, current_time, user_profile=user_profile, fast_mode=True,
                    exclude_question_ids=[first_q.question_id],
                )
                if alt_q:
                    alt_data = _load_question_perseus(alt_q.question_id, mongo_db)
                    if alt_data and not _has_only_broken_widgets(alt_data):
                        first_q = alt_q
                        q_data = alt_data
                        break
            if not q_data:
                raise HTTPException(status_code=400, detail="No supported questions available")

        # Update session (track content hash alongside question ID for content-level dedup)
        first_content_hash = _compute_content_hash(q_data)
        mongo_db.db["assessment_sessions"].update_one(
            {"assessment_id": assessment_id},
            {"$push": {"used_question_ids": first_q.question_id,
                       "used_skill_ids": first_q.skill_ids[0] if first_q.skill_ids else "",
                       "used_content_hashes": first_content_hash},
             "$set": {"questions_asked": 1}}
        )

        # Auto-prefetch question 2 immediately while user reads question 1
        def _start_prefetch():
            _assessment_prefetch_worker(assessment_id, user_id, 0.5, jwt_age)
        threading.Thread(target=_start_prefetch, daemon=True).start()

        # Patch widget fields before returning (prefetch/pool data may lack defaults)
        _patch_numeric_input_widgets(q_data)

        # ── Inject skill_ids from Question object into Perseus response (Bug #22) ──
        # _load_question_perseus builds dash_metadata from MongoDB docs which may
        # lack skill_ids.  The Question object always has the correct ones.
        if first_q.skill_ids and q_data:
            dm = q_data.setdefault("dash_metadata", {})
            existing = dm.get("skill_ids") or []
            # Only override if the existing list is empty or contains only empty strings
            if not existing or all(s == "" for s in existing):
                dm["skill_ids"] = first_q.skill_ids
                logger.info(f"[ADAPTIVE_ASSESSMENT] Injected skill_ids={first_q.skill_ids} into q_data")

        return {
            "assessment_id": assessment_id,
            "question_number": 1,
            "total_questions": 10,
            "question": q_data,
            "current_difficulty": 0.5,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADAPTIVE_ASSESSMENT] Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Assessment error: {str(e)}")


@app.post("/assessment/next")
def assessment_next_question(request: Request, payload: AdaptiveAssessmentAnswer):
    """
    Submit answer for current adaptive assessment question, get next question.
    Difficulty adjusts: +0.15 on correct, -0.15 on wrong, clamped to [0.1, 0.9].
    """
    ensure_dash_system()
    from managers.mongodb_manager import mongo_db

    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age", 10)

    session = mongo_db.db["assessment_sessions"].find_one({
        "assessment_id": payload.assessment_id, "user_id": user_id, "status": "in_progress"
    })
    if not session:
        raise HTTPException(status_code=404, detail="Assessment session not found")

    # Record answer
    current_diff = session.get("current_difficulty", 0.5)
    new_diff = current_diff + (0.15 if payload.is_correct else -0.15)
    new_diff = max(0.1, min(1.0, new_diff))  # 1.0 cap enables synthesis tier

    answer_record = {
        "question_id": payload.question_id,
        "skill_id": payload.skill_id,
        "is_correct": payload.is_correct,
        "difficulty_at_time": current_diff,
    }
    questions_asked = session.get("questions_asked", 0) + 1

    # ── Sync assessment answers into DASH student states for mastery tracking ──
    try:
        # Try load_user first (cheap); only create if missing
        user_profile = dash_system.user_manager.load_user(user_id)
        if not user_profile:
            user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 10)

        # ── Resolve skill_id: trust frontend, fall back to session/DB (Bug #22) ──
        resolved_skill_id = payload.skill_id or ""
        if not resolved_skill_id:
            # Try assessment session's used_skill_ids (indexed by question order)
            used_skills = session.get("used_skill_ids", [])
            q_idx = questions_asked - 2  # -1 for 0-index, -1 more because we already incremented
            if 0 <= q_idx < len(used_skills) and used_skills[q_idx]:
                resolved_skill_id = used_skills[q_idx]
                logger.info(f"[ASSESSMENT] Resolved skill_id from session: {resolved_skill_id}")
        if not resolved_skill_id:
            # Last resort: look up from the question document in MongoDB
            q_doc = mongo_db.ai_generated_questions.find_one(
                {"question_id": payload.question_id}, {"skill_id": 1, "skill_ids": 1}
            )
            if q_doc:
                resolved_skill_id = (q_doc.get("skill_ids") or [q_doc.get("skill_id", "")])[0] or ""
                if resolved_skill_id:
                    logger.info(f"[ASSESSMENT] Resolved skill_id from DB: {resolved_skill_id}")

        skill_ids = [resolved_skill_id] if resolved_skill_id else []
        if skill_ids:
            # Ensure the skill exists in user_profile.skill_states for save_user_state
            for sid in skill_ids:
                if sid not in user_profile.skill_states:
                    from managers.user_manager import SkillState
                    user_profile.skill_states[sid] = SkillState(
                        memory_strength=0.0, last_practice_time=None,
                        practice_count=0, correct_count=0
                    )
            dash_system.record_question_attempt(
                user_profile, payload.question_id, skill_ids,
                payload.is_correct, 30.0  # default response time for assessment
            )
            logger.info(f"[ASSESSMENT] Synced attempt: q={payload.question_id} skill={payload.skill_id} correct={payload.is_correct}")
        else:
            logger.warning(f"[ASSESSMENT] No skill_id in payload — skipping student state sync")
    except Exception as e:
        logger.warning(f"[ASSESSMENT] Failed to sync student state: {e}")
        import traceback
        logger.warning(traceback.format_exc())

    # Check if assessment is complete (> not >= because questions_asked already
    # includes the current answer; >= would skip the last question)
    if questions_asked > session.get("max_questions", 10):
        # Complete the assessment
        all_answers = session.get("answers", []) + [answer_record]
        correct_count = sum(1 for a in all_answers if a["is_correct"])

        mongo_db.db["assessment_sessions"].update_one(
            {"assessment_id": payload.assessment_id},
            {"$inc": {"questions_asked": 1},
             "$set": {"status": "completed", "current_difficulty": new_diff},
             "$push": {"answers": answer_record}}
        )

        # Also store in subject_assessments for compatibility
        mongo_db.subject_assessments.update_one(
            {"user_id": user_id, "subject": session["subject"]},
            {"$set": {
                "assessment_completed": True,
                "assessment_date": datetime.now(),
                "score": correct_count,
                "total": len(all_answers),
                "answers": [AssessmentAnswer(**{k: v for k, v in a.items() if k in ("question_id", "skill_id", "is_correct")}).model_dump() for a in all_answers],
                "adaptive": True,
                "final_difficulty": new_diff,
            }},
            upsert=True,
        )

        # Clean up prefetch cache for completed assessment
        with _prefetch_lock:
            _prefetch_cache.pop(payload.assessment_id, None)

        return {
            "completed": True,
            "score": correct_count,
            "total": len(all_answers),
            "final_difficulty": round(new_diff, 3),
        }

    # Check prefetch cache first — instant if available
    used_q_ids = session.get("used_question_ids", [])
    used_skill_ids = session.get("used_skill_ids", [])
    used_content_hashes = set(session.get("used_content_hashes", []))

    cached_result = None
    with _prefetch_lock:
        if payload.assessment_id in _prefetch_cache:
            cached_result = _prefetch_cache.pop(payload.assessment_id)

    q_data = None
    next_q = None

    if cached_result and cached_result.get("q_data"):
        next_q_id = cached_result.get("question_id")
        cached_q_data = cached_result["q_data"]
        cached_hash = _compute_content_hash(cached_q_data)
        # Guard: reject if question ID reused OR content already served
        if next_q_id and next_q_id not in used_q_ids and cached_hash not in used_content_hashes:
            q_data = cached_q_data
            next_skill_id = cached_result.get("skill_id", "")
            next_q = Question(
                question_id=next_q_id,
                skill_ids=[next_skill_id] if next_skill_id else [],
                content="",
                difficulty=new_diff,
                expected_time_seconds=60.0,
            )
            logger.info(f"[ADAPTIVE_NEXT] Cache HIT for {payload.assessment_id}")
        else:
            dup_reason = "id" if next_q_id in used_q_ids else "content_hash"
            logger.info(f"[ADAPTIVE_NEXT] Cache STALE ({dup_reason} duplicate {next_q_id}) — regenerating")

    if not next_q:
        logger.info(f"[ADAPTIVE_NEXT] Cache miss for {payload.assessment_id} — generating live")
        # Clear any in-flight stale prefetch so it doesn't cache an old question
        with _prefetch_lock:
            _prefetch_cache.pop(payload.assessment_id, None)

        user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
        current_time = time.time()
        subject = (session.get("subject") or "").strip().title()

        # Pin DASH system to the session's subject — prevents wrong-subject
        # questions when concurrent requests switch the global singleton
        if subject:
            _switch_subject_if_needed(subject, "US")

        # Retry loop: try pool first, then force JIT with unique IDs on duplicate
        # Total budget: 20 seconds to prevent frontend timeout
        import concurrent.futures
        JIT_TIMEOUT = 12  # seconds per JIT attempt
        MAX_RETRIES = 2   # reduced from 3 to stay within budget
        retry_start = time.time()

        for attempt in range(MAX_RETRIES):
            # Bail if we've spent too long already
            if time.time() - retry_start > 20:
                logger.warning(f"[ADAPTIVE_NEXT] Retry budget exhausted after {attempt} attempts")
                break

            if attempt == 0:
                # First attempt: try the pool via DASH
                next_q = dash_system.get_next_question_flexible(
                    user_id, current_time,
                    exclude_question_ids=used_q_ids,
                    user_profile=user_profile,
                    exclude_skill_ids=used_skill_ids[-3:] if len(used_skill_ids) >= 3 else None,
                    fast_mode=True,
                )

            # Check if we got a duplicate (pool exhausted)
            if next_q and next_q.question_id in used_q_ids:
                logger.info(f"[ADAPTIVE_NEXT] Attempt {attempt+1}: duplicate {next_q.question_id} — forcing JIT")
                next_q = None

            # If we have a valid question, we're done
            if next_q:
                break

            # Force JIT generation if pool returned None or duplicate
            if dash_system.use_ai_questions and dash_system.ai_provider:
                grade_name = user_profile.current_grade.replace("GRADE_", "Grade ").replace("K", "Kindergarten")
                # Unique synthetic ID per retry to force fresh generation
                synthetic_id = f"assessment_{subject.lower().replace(' ', '_')}_{user_profile.current_grade.lower()}_{questions_asked}_r{attempt}_{int(time.time()*1000) % 100000}"
                try:
                    # Run JIT with a timeout to prevent hanging
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            dash_system.ai_provider.get_question_for_skill,
                            skill_id=synthetic_id,
                            skill_name=f"{subject} for {grade_name}",
                            target_difficulty=new_diff,
                            grade_level=user_profile.current_grade,
                            age=user_profile.age if user_profile.age else 10,
                            exclude_question_ids=used_q_ids,
                            user_id=user_id,
                            fast_mode=True,
                            subject=subject,
                        )
                        ai_result = future.result(timeout=JIT_TIMEOUT)
                    if ai_result:
                        jit_qid = ai_result["dash_metadata"]["dash_question_id"]
                        if jit_qid not in used_q_ids:
                            next_q = Question(
                                question_id=jit_qid,
                                skill_ids=[synthetic_id],
                                content="",
                                difficulty=ai_result["dash_metadata"]["difficulty"],
                                expected_time_seconds=60.0,
                            )
                            logger.info(f"[ADAPTIVE_NEXT] JIT success on attempt {attempt+1}: {jit_qid}")
                            break
                        else:
                            logger.info(f"[ADAPTIVE_NEXT] JIT returned duplicate {jit_qid}, retrying")
                            next_q = None
                except concurrent.futures.TimeoutError:
                    logger.warning(f"[ADAPTIVE_NEXT] JIT attempt {attempt+1} timed out after {JIT_TIMEOUT}s")
                except Exception as e:
                    logger.warning(f"[ADAPTIVE_NEXT] JIT attempt {attempt+1} failed: {e}")
            else:
                break  # No AI provider available

    if not next_q:
        # No more questions — auto-complete
        all_answers = session.get("answers", []) + [answer_record]
        correct_count = sum(1 for a in all_answers if a["is_correct"])
        mongo_db.db["assessment_sessions"].update_one(
            {"assessment_id": payload.assessment_id},
            {"$set": {"status": "completed"}, "$push": {"answers": answer_record}}
        )
        with _prefetch_lock:
            _prefetch_cache.pop(payload.assessment_id, None)
        return {"completed": True, "score": correct_count, "total": len(all_answers), "final_difficulty": round(new_diff, 3)}

    if not q_data:
        q_data = getattr(next_q, "perseus_data", None) or _load_question_perseus(next_q.question_id, mongo_db)
    if not q_data:
        raise HTTPException(status_code=500, detail="Failed to load next question")

    # Content-hash dedup: reject questions with identical content even if IDs differ
    next_content_hash = _compute_content_hash(q_data)
    if next_content_hash in used_content_hashes:
        logger.warning(f"[ADAPTIVE_NEXT] Content-hash duplicate detected: {next_q.question_id} — skipping")
        # Auto-complete rather than serve duplicate content
        all_answers = session.get("answers", []) + [answer_record]
        correct_count = sum(1 for a in all_answers if a["is_correct"])
        mongo_db.db["assessment_sessions"].update_one(
            {"assessment_id": payload.assessment_id},
            {"$set": {"status": "completed"}, "$push": {"answers": answer_record}}
        )
        with _prefetch_lock:
            _prefetch_cache.pop(payload.assessment_id, None)
        return {"completed": True, "score": correct_count, "total": len(all_answers), "final_difficulty": round(new_diff, 3)}

    # Skip questions with only broken widget types (orderer/matcher — unsupported in React 18)
    if _has_only_broken_widgets(q_data):
        logger.info(f"[ADAPTIVE_NEXT] Skipping broken-widget-only question {next_q.question_id}")
        # Auto-complete rather than serve unsupported question
        all_answers = session.get("answers", []) + [answer_record]
        correct_count = sum(1 for a in all_answers if a["is_correct"])
        mongo_db.db["assessment_sessions"].update_one(
            {"assessment_id": payload.assessment_id},
            {"$set": {"status": "completed"}, "$push": {"answers": answer_record}}
        )
        with _prefetch_lock:
            _prefetch_cache.pop(payload.assessment_id, None)
        return {"completed": True, "score": correct_count, "total": len(all_answers), "final_difficulty": round(new_diff, 3)}

    # Patch widget fields before returning (prefetch/pool data may lack defaults)
    _patch_numeric_input_widgets(q_data)

    # ── Inject skill_ids from Question object into Perseus response (Bug #22) ──
    if next_q.skill_ids and q_data:
        dm = q_data.setdefault("dash_metadata", {})
        existing = dm.get("skill_ids") or []
        if not existing or all(s == "" for s in existing):
            dm["skill_ids"] = next_q.skill_ids
            logger.info(f"[ADAPTIVE_NEXT] Injected skill_ids={next_q.skill_ids} into q_data")

    # Update session AFTER Perseus load + patching succeeds (avoids inconsistent state on load failure)
    # Use $inc for questions_asked to prevent race conditions from concurrent requests
    mongo_db.db["assessment_sessions"].update_one(
        {"assessment_id": payload.assessment_id},
        {"$inc": {"questions_asked": 1},
         "$set": {"current_difficulty": new_diff},
         "$push": {"answers": answer_record, "used_question_ids": next_q.question_id,
                   "used_skill_ids": next_q.skill_ids[0] if next_q.skill_ids else "",
                   "used_content_hashes": next_content_hash}}
    )

    # Auto-chain: immediately start prefetching the NEXT question in background
    # so it's ready by the time the user answers this one
    if questions_asked < session.get("max_questions", 10) - 1:
        def _auto_prefetch():
            try:
                _assessment_prefetch_worker(
                    assessment_id=payload.assessment_id,
                    user_id=user_id,
                    current_difficulty=new_diff,
                    jwt_payload_age=jwt_age,
                )
            except Exception as e:
                logger.warning(f"[AUTO_PREFETCH] Failed (non-blocking): {e}")
        threading.Thread(target=_auto_prefetch, daemon=True).start()

    return {
        "completed": False,
        "question_number": questions_asked,
        "total_questions": session.get("max_questions", 10),
        "question": q_data,
        "current_difficulty": round(new_diff, 3),
    }


def _assessment_prefetch_worker(assessment_id: str, user_id: str, current_difficulty: float, jwt_payload_age: int = 10):
    """Shared prefetch worker — generates one question and caches it."""
    try:
        ensure_dash_system()
        from managers.mongodb_manager import mongo_db as _mongo

        # Skip if we already have a cached question for this assessment
        with _prefetch_lock:
            if assessment_id in _prefetch_cache:
                return

        session = _mongo.db["assessment_sessions"].find_one({
            "assessment_id": assessment_id, "user_id": user_id, "status": "in_progress"
        })
        if not session:
            return

        questions_asked = session.get("questions_asked", 0)
        if questions_asked >= session.get("max_questions", 10) - 1:
            return  # Last question — no next to prefetch

        used_q_ids = session.get("used_question_ids", [])
        used_skill_ids = session.get("used_skill_ids", [])
        user_profile = dash_system.load_user_or_create(user_id, age=jwt_payload_age if jwt_payload_age else 5)
        current_time = time.time()
        subject = (session.get("subject") or "").strip().title()

        # Pin DASH system to the session's subject — prevents wrong-subject
        # questions when concurrent requests switch the global singleton
        if subject:
            _switch_subject_if_needed(subject, "US")

        # Retry loop: try pool first, then JIT with unique IDs on duplicate
        q = None
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            if attempt == 0:
                q = dash_system.get_next_question_flexible(
                    user_id, current_time,
                    exclude_question_ids=used_q_ids,
                    user_profile=user_profile,
                    exclude_skill_ids=used_skill_ids[-3:] if len(used_skill_ids) >= 3 else None,
                    fast_mode=True,
                )

            # Check for duplicate
            if q and q.question_id in used_q_ids:
                logger.info(f"[PREFETCH] Attempt {attempt+1}: duplicate {q.question_id} — forcing JIT")
                q = None

            # Force JIT if pool returned None or duplicate
            if not q and dash_system.use_ai_questions and dash_system.ai_provider:
                grade_name = user_profile.current_grade.replace("GRADE_", "Grade ").replace("K", "Kindergarten")
                synthetic_id = f"assessment_{subject.lower().replace(' ', '_')}_{user_profile.current_grade.lower()}_{questions_asked + 1}_pf{attempt}_{int(time.time()*1000) % 100000}"
                try:
                    ai_result = dash_system.ai_provider.get_question_for_skill(
                        skill_id=synthetic_id,
                        skill_name=f"{subject} for {grade_name}",
                        target_difficulty=current_difficulty,
                        grade_level=user_profile.current_grade,
                        age=user_profile.age if user_profile.age else 10,
                        exclude_question_ids=used_q_ids,
                        user_id=user_id,
                        fast_mode=True,
                        subject=subject,
                    )
                    if ai_result:
                        jit_qid = ai_result["dash_metadata"]["dash_question_id"]
                        if jit_qid not in used_q_ids:
                            q = Question(
                                question_id=jit_qid,
                                skill_ids=[synthetic_id],
                                content="",
                                difficulty=current_difficulty,
                                expected_time_seconds=60.0,
                            )
                            logger.info(f"[PREFETCH] JIT success on attempt {attempt+1}: {jit_qid}")
                            break
                        else:
                            logger.info(f"[PREFETCH] JIT returned duplicate {jit_qid}, retrying")
                            q = None
                except Exception as e:
                    logger.warning(f"[PREFETCH] JIT attempt {attempt+1} failed: {e}")
            else:
                break  # Got unique question from pool

        if q:
            # Re-read session to get latest used_question_ids + content hashes (guards against race)
            fresh_session = _mongo.db["assessment_sessions"].find_one(
                {"assessment_id": assessment_id}, {"used_question_ids": 1, "used_content_hashes": 1}
            )
            fresh_used = fresh_session.get("used_question_ids", []) if fresh_session else []
            if q.question_id in fresh_used:
                logger.info(f"[PREFETCH] Skipping duplicate {q.question_id} (race detected)")
                return

            q_data = getattr(q, "perseus_data", None) or _load_question_perseus(q.question_id, _mongo)
            if q_data:
                # Inject skill_ids into Perseus dash_metadata (Bug #22)
                if q.skill_ids:
                    dm = q_data.setdefault("dash_metadata", {})
                    existing = dm.get("skill_ids") or []
                    if not existing or all(s == "" for s in existing):
                        dm["skill_ids"] = q.skill_ids

                # Content-hash dedup: reject questions with identical content
                fresh_hashes = set(fresh_session.get("used_content_hashes", [])) if fresh_session else set()
                ch = _compute_content_hash(q_data)
                if ch in fresh_hashes:
                    logger.info(f"[PREFETCH] Content-hash duplicate {q.question_id} — discarding")
                    return
                with _prefetch_lock:
                    _prefetch_cache[assessment_id] = {
                        "q_data": q_data,
                        "question_id": q.question_id,
                        "skill_id": q.skill_ids[0] if q.skill_ids else "",
                    }
                logger.info(f"[PREFETCH] Cached question {q.question_id} for {assessment_id}")

    except Exception as e:
        logger.warning(f"[PREFETCH] Background prefetch failed (non-blocking): {e}")


@app.post("/assessment/prefetch")
def assessment_prefetch(request: Request, payload: AssessmentPrefetchRequest):
    """
    Pre-generate the next question in background while user works on current one.
    Returns immediately — generation happens in a daemon thread.
    """
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age", 10)

    def _do_prefetch():
        _assessment_prefetch_worker(payload.assessment_id, user_id, payload.current_difficulty, jwt_age)

    threading.Thread(target=_do_prefetch, daemon=True).start()
    return {"status": "prefetching"}


# ===== LEARNING PATH PREFETCH =====
LEARNING_PREFETCH_TTL = 120  # 2 minutes — learning path questions stay valid shorter than warm-start


def _learning_prefetch_worker(user_id: str, exclude_question_ids: list, jwt_age: int):
    """Background worker that pre-generates the next learning-path question and caches it."""
    try:
        ensure_dash_system()
        from managers.mongodb_manager import mongo_db as _mongo

        # Skip if we already have a cached question for this user
        with _learning_prefetch_lock:
            if user_id in _learning_prefetch_cache:
                logger.info(f"[LEARNING_PREFETCH] Already cached for {user_id}, skipping")
                return

        user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
        current_time = time.time()

        q = dash_system.get_next_question_flexible(
            user_id, current_time,
            exclude_question_ids=exclude_question_ids,
            user_profile=user_profile,
            fast_mode=True,
        )

        if not q:
            logger.info(f"[LEARNING_PREFETCH] No question generated for {user_id}")
            return

        # Load Perseus data — use perseus_data attr if available, else load from MongoDB
        q_data = getattr(q, "perseus_data", None) or _load_question_perseus(q.question_id, _mongo)
        if not q_data:
            logger.info(f"[LEARNING_PREFETCH] No Perseus data for {q.question_id}")
            return

        with _learning_prefetch_lock:
            _learning_prefetch_cache[user_id] = {
                "q_data": q_data,
                "question_id": q.question_id,
                "skill_id": q.skill_ids[0] if q.skill_ids else "",
                "ts": time.time(),
            }
        logger.info(f"[LEARNING_PREFETCH] Cached question {q.question_id} for user {user_id}")

    except Exception as e:
        logger.warning(f"[LEARNING_PREFETCH] Background prefetch failed (non-blocking): {e}")


@app.post("/api/questions/prefetch")
def learning_prefetch(request: Request, payload: LearningPrefetchRequest):
    """
    Pre-generate the next learning-path question in background while user works on current batch.
    Returns immediately — generation happens in a daemon thread.
    """
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age", 10)

    exclude_ids = list(payload.current_question_ids)

    def _do_learning_prefetch():
        _learning_prefetch_worker(user_id, exclude_ids, jwt_age)

    threading.Thread(target=_do_learning_prefetch, daemon=True).start()
    return {"status": "prefetching"}


def _trigger_learning_prefetch(user_id: str, served_question_ids: list, jwt_age: int):
    """Fire-and-forget helper to trigger learning path prefetch after serving questions."""
    def _do():
        _learning_prefetch_worker(user_id, served_question_ids, jwt_age)
    threading.Thread(target=_do, daemon=True).start()


def _compute_content_hash(q_data: dict) -> str:
    """Compute SHA-256 hash of question content + widgets for duplicate detection.

    Two questions with different IDs but identical content will produce the same hash.
    """
    content_str = json.dumps(
        q_data.get("question", {}).get("content", ""),
        sort_keys=True, ensure_ascii=True,
    )
    widgets_str = json.dumps(
        q_data.get("question", {}).get("widgets", {}),
        sort_keys=True, ensure_ascii=True,
    )
    # Include answerArea so different-answer variants aren't treated as same question
    answer_str = json.dumps(
        q_data.get("answerArea", {}),
        sort_keys=True, ensure_ascii=True,
    )
    return hashlib.sha256((content_str + widgets_str + answer_str).encode()).hexdigest()


def _load_question_perseus(question_id: str, mongo_db) -> Optional[dict]:
    """Load Perseus question data from MongoDB for a given question_id."""
    # Support Khan questions too — try questions_db if not an AI/pool question
    if not question_id.startswith("ai_q_") and not question_id.startswith("pool_"):
        # Try Khan Academy questions collection
        try:
            khan_doc = mongo_db.questions.find_one({"question_id": question_id})
            if not khan_doc:
                khan_doc = mongo_db.questions.find_one({"unit_id": question_id})
            if khan_doc:
                perseus = khan_doc.get("perseus_json", {})
                if isinstance(perseus, dict):
                    perseus = dict(perseus)
                    perseus.pop("_id", None)
                    if "dash_metadata" not in perseus:
                        perseus["dash_metadata"] = {
                            "dash_question_id": question_id,
                            "skill_ids": [khan_doc.get("unit_id", question_id)],
                            "difficulty": khan_doc.get("difficulty", 0.5),
                            "skill_names": [khan_doc.get("skill_name", "")],
                            "unit_name": khan_doc.get("unit_name", ""),
                            "lesson_name": khan_doc.get("lesson_name", "Practice"),
                            "ai_generated": False,
                        }
                    _patch_numeric_input_widgets(perseus)
                    return _strip_objectids(perseus)
        except Exception as e:
            logger.warning(f"[LOAD_PERSEUS] Khan question lookup failed for {question_id}: {e}")
        return None

    # Try ai_generated_questions first (most common)
    doc = mongo_db.ai_generated_questions.find_one({"question_id": question_id})

    # Fallback: search content_pool collection (pool-served questions)
    if not doc:
        pool_col = mongo_db.db.get_collection("content_pool") if hasattr(mongo_db, "db") else None
        if pool_col:
            pool_doc = pool_col.find_one(
                {"question_data.dash_metadata.dash_question_id": question_id}
            )
            if not pool_doc:
                # Pool questions may not have dash_metadata yet — search by text match
                # The question_id was synthesized from the pool dict, try direct lookup
                pool_doc = pool_col.find_one({"question_id": question_id})
            if pool_doc:
                q_data = pool_doc.get("question_data", {})
                if q_data:
                    perseus = dict(q_data)
                    # Ensure dash_metadata exists
                    skill_id = pool_doc.get("skill_id", "")
                    if "dash_metadata" not in perseus:
                        perseus["dash_metadata"] = {
                            "dash_question_id": question_id,
                            "skill_ids": [skill_id],
                            "difficulty": pool_doc.get("difficulty", 0.5),
                            "skill_names": [skill_id],
                            "unit_name": skill_id,
                            "lesson_name": "Practice",
                            "ai_generated": True,
                        }
                    _patch_numeric_input_widgets(perseus)
                    try:
                        from pre_serve_validator import validate_pre_serve
                        vr = validate_pre_serve(
                            perseus, skill_id=skill_id,
                            db_collection=mongo_db.db["validation_failures"],
                        )
                        if not vr.passed:
                            logger.warning(f"[LOAD_PERSEUS] Pool pre-serve REJECT {question_id}: {vr.failures}")
                            return None
                    except Exception as e:
                        logger.warning(f"[LOAD_PERSEUS] Pool pre-serve validator error for {question_id}: {e}")
                    return _strip_objectids(perseus)

    if doc:
        # Use perseus_json (matching _load_ai_generated_perseus_items pattern)
        raw = doc.get("perseus_json") or doc.get("perseus_data")
        if raw:
            perseus = dict(raw)
        else:
            perseus = {k: v for k, v in doc.items() if k != "_id"}
        skill_id = doc.get("skill_id", "")
        skill_name = doc.get("skill_name", "AI Generated")
        lesson_name = doc.get("lesson_name", "") or "Practice"
        if lesson_name == skill_name:
            lesson_name = "Practice"
        perseus["dash_metadata"] = {
            "dash_question_id": question_id,
            "skill_ids": doc.get("skill_ids", [skill_id]),
            "difficulty": doc.get("difficulty", 0.5),
            "skill_names": [skill_name],
            "unit_name": skill_name,
            "lesson_name": lesson_name,
            "ai_generated": True,
            "mongodb_id": str(doc.get("_id", question_id)),
        }
        _patch_numeric_input_widgets(perseus)
        try:
            from pre_serve_validator import validate_pre_serve
            vr = validate_pre_serve(
                perseus, skill_id=skill_id,
                subject=doc.get("subject"),
                db_collection=mongo_db.db["validation_failures"],
            )
            if not vr.passed:
                logger.warning(f"[LOAD_PERSEUS] AI pre-serve REJECT {question_id}: {vr.failures}")
                return None
        except Exception as e:
            logger.warning(f"[LOAD_PERSEUS] AI pre-serve validator error for {question_id}: {e}")
        return _strip_objectids(perseus)
    return None


# Widget types broken in React 18 (string refs) — skip questions with only these
_BROKEN_WIDGET_TYPES = {"orderer", "matcher"}


def _has_only_broken_widgets(perseus: dict) -> bool:
    """Return True if question only has widget types unsupported in the frontend."""
    widgets = perseus.get("question", {}).get("widgets", {})
    scoreable = [
        w for w in widgets.values()
        if isinstance(w, dict) and w.get("type") not in (None, "image", "definition")
    ]
    if not scoreable:
        return False
    return all(w.get("type") in _BROKEN_WIDGET_TYPES for w in scoreable)


def _patch_numeric_input_widgets(perseus: dict) -> None:
    """Patch missing required fields on all widget types and validate answer presence."""
    widgets = perseus.get("question", {}).get("widgets", {})
    for wkey, wval in widgets.items():
        if not isinstance(wval, dict):
            continue
        wtype = wval.get("type")
        opts = wval.setdefault("options", {})
        if wtype == "numeric-input":
            opts.setdefault("coefficient", False)
            opts.setdefault("static", False)
            opts.setdefault("labelText", "")
            opts.setdefault("size", "normal")
        elif wtype == "expression":
            opts.setdefault("buttonSets", ["basic"])
            opts.setdefault("functions", ["f", "g", "h"])
            opts.setdefault("times", False)
            opts.setdefault("buttonsVisible", "never")
        elif wtype == "dropdown":
            opts.setdefault("placeholder", "Select an answer")
            opts.setdefault("static", False)
        elif wtype == "matcher":
            opts.setdefault("labels", ["Left", "Right"])
            opts.setdefault("orderMatters", False)
            opts.setdefault("padding", True)
        elif wtype == "sorter":
            opts.setdefault("layout", "horizontal")
            opts.setdefault("padding", True)
        elif wtype == "categorizer":
            opts.setdefault("randomizeItems", False)
            opts.setdefault("static", False)
            opts.setdefault("highlightLint", False)
        elif wtype == "number-line":
            rng = opts.get("range")
            if not isinstance(rng, list) or len(rng) != 2:
                rng = [0, 10]
            opts.setdefault("labelRange", rng)
            opts.setdefault("initialX", opts.get("correctX", 0))
            opts.setdefault("tickStep", 1)
            opts.setdefault("labelStyle", "decimal")
            opts.setdefault("labelTicks", True)
            opts.setdefault("isInequality", False)
            opts.setdefault("snapDivisions", 2)
            opts.setdefault("correctRel", "eq")
            opts.setdefault("numDivisions", 10)
            opts.setdefault("divisionRange", rng)
            opts.setdefault("isTickCtrl", False)
            opts.setdefault("static", False)
        elif wtype == "table":
            opts.setdefault("headers", [])
            opts.setdefault("rows", 4)
            opts.setdefault("columns", 2)

    # Ensure answerArea exists
    if "answerArea" not in perseus and "answer_area" not in perseus:
        perseus["answerArea"] = {
            "calculator": False,
            "options": {"content": "", "images": {}, "widgets": {}},
            "type": "multiple",
        }

    # Ensure hints is a list of dicts (not strings)
    hints = perseus.get("hints", [])
    if isinstance(hints, list):
        for i, h in enumerate(hints):
            if isinstance(h, str):
                hints[i] = {"content": h, "images": {}, "replace": False, "widgets": {}}
            elif isinstance(h, dict):
                h.setdefault("images", {})
                h.setdefault("replace", False)
                h.setdefault("widgets", {})

    # Ensure question.images exists
    q = perseus.get("question", {})
    if isinstance(q, dict):
        q.setdefault("images", {})


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

    user_id = require_admin(request)

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

    user_id = require_admin(request)

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


# ===== CURRICULUM GENERATION ENDPOINTS =====


class StartSubjectRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    region: str = Field(default="US", min_length=1, max_length=10)


def _prewarm_assessment_questions(user_id: str, subject: str, region: str):
    """Pre-generate Q1 in background and cache it so start-adaptive is instant."""
    cache_key = f"{user_id}:{subject.lower()}"

    # Create an Event so start-adaptive can wait for this warm-start
    evt = threading.Event()
    with _warmstart_lock:
        # Skip if already cached and fresh
        if cache_key in _warmstart_cache:
            cached = _warmstart_cache[cache_key]
            if time.time() - cached.get("ts", 0) < WARMSTART_TTL:
                logger.debug(f"[WARMSTART] Already cached for {cache_key}")
                evt.set()
                return
        _warmstart_events[cache_key] = evt

    def _bg():
        try:
            ensure_dash_system()
            from managers.mongodb_manager import mongo_db as _mongo

            if not dash_system:
                return

            profile = dash_system.load_user_or_create(user_id)
            current_time = time.time()

            # Try pool/DASH first (fast path)
            q = dash_system.get_next_question_flexible(
                user_id, current_time, user_profile=profile, fast_mode=True,
            )

            # JIT fallback for cold subjects
            if not q and dash_system.use_ai_questions and dash_system.ai_provider:
                grade = profile.current_grade
                age = profile.age or 10
                grade_name = grade.replace("GRADE_", "Grade ").replace("K", "Kindergarten")
                synthetic_id = f"assessment_{subject.lower().replace(' ', '_')}_{grade.lower()}_warmstart"
                try:
                    ai_result = dash_system.ai_provider.get_question_for_skill(
                        skill_id=synthetic_id,
                        skill_name=f"{subject} for {grade_name}",
                        target_difficulty=0.5,
                        grade_level=grade,
                        age=age,
                        exclude_question_ids=[],
                        user_id=user_id,
                        fast_mode=True,
                        subject=subject,
                    )
                    if ai_result:
                        q = Question(
                            question_id=ai_result["dash_metadata"]["dash_question_id"],
                            skill_ids=[synthetic_id],
                            content="",
                            difficulty=0.5,
                            expected_time_seconds=60.0,
                        )
                except Exception as e:
                    logger.warning(f"[WARMSTART] JIT failed for {subject}: {e}")

            if not q:
                return

            # Load Perseus data
            q_data = getattr(q, "perseus_data", None) or _load_question_perseus(q.question_id, _mongo)
            if not q_data:
                return

            # Inject skill_ids into Perseus dash_metadata (Bug #22)
            if q.skill_ids:
                dm = q_data.setdefault("dash_metadata", {})
                existing = dm.get("skill_ids") or []
                if not existing or all(s == "" for s in existing):
                    dm["skill_ids"] = q.skill_ids

            with _warmstart_lock:
                _warmstart_cache[cache_key] = {
                    "q_data": q_data,
                    "question_id": q.question_id,
                    "skill_id": q.skill_ids[0] if q.skill_ids else "",
                    "ts": time.time(),
                }
            logger.info(f"[WARMSTART] Cached Q1 for {cache_key}: {q.question_id}")

        except Exception as e:
            logger.warning(f"[WARMSTART] Background error: {e}")
        finally:
            evt.set()  # Always signal, even on failure
            with _warmstart_lock:
                _warmstart_events.pop(cache_key, None)
    threading.Thread(target=_bg, daemon=True).start()


@app.post("/api/start-subject")
def start_subject(request: Request, payload: StartSubjectRequest):
    """
    Main entry point: student picks a subject.

    - If curriculum exists -> reload DASH -> return ready.
    - If not -> trigger generation -> return 'generating' with poll URL.
    """
    if curriculum_generator is None or dash_system is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    user_id = get_current_user(request)
    subject = payload.subject.strip().title()
    region = payload.region.strip().upper()

    logger.info(f"[START_SUBJECT] User {user_id} requested {subject}/{region}")

    # Step 1: Try loading DASH with the requested subject/region (thread-safe)
    _switch_subject_if_needed(subject, region)

    # Fire-and-forget: pre-warm assessment questions in background
    _prewarm_assessment_questions(user_id, subject, region)

    # Check grade coverage — sparse Khan data needs AI curriculum generation
    MIN_GRADE_COVERAGE = 8  # Need skills across at least 8 of 13 grade levels (K-12)
    grades_covered = set()
    if len(dash_system.skills) > 0:
        grades_covered = {s.grade_level.value for s in dash_system.skills.values()}

    if len(grades_covered) >= MIN_GRADE_COVERAGE:
        logger.info(f"[START_SUBJECT] Good coverage: {len(grades_covered)} grades, {len(dash_system.skills)} skills")
        return {
            "status": "ready",
            "subject": subject,
            "region": region,
            "skills_count": len(dash_system.skills),
        }

    if len(grades_covered) > 0:
        logger.info(
            f"[START_SUBJECT] Sparse coverage for {subject}: "
            f"{len(grades_covered)}/13 grades ({sorted(grades_covered)}). "
            f"Triggering AI curriculum generation."
        )

    # Step 2: Coverage insufficient or no data — trigger AI curriculum generation
    result = curriculum_generator.get_or_generate(subject, region)

    if result["status"] == "complete":
        # Backfill any courses that had 0 units (Gemini JSON parse failures)
        try:
            backfilled = curriculum_generator.backfill_empty_courses(subject, region)
            if backfilled > 0:
                logger.info(f"[START_SUBJECT] Backfilled {backfilled} empty courses for {subject}/{region}")
        except Exception as exc:
            logger.warning(f"[START_SUBJECT] Backfill failed (non-fatal): {exc}")

        # AI curriculum exists — reload to pick it up (thread-safe)
        _switch_subject_if_needed(subject, region)
        return {
            "status": "ready",
            "subject": subject,
            "region": region,
            "skills_count": len(dash_system.skills),
            "stats": result.get("stats", {}),
        }

    # Generation in progress or just started
    return {
        "status": "generating",
        "subject": subject,
        "region": region,
        "poll_url": f"/api/curriculum/status/{subject}/{region}",
        "estimated_wait_seconds": result.get("estimated_wait_seconds", 35),
    }


@app.get("/api/curriculum/status/{subject}/{region}")
def curriculum_status(subject: str, region: str):
    """Poll endpoint for curriculum generation progress."""
    if curriculum_generator is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    result = curriculum_generator.check_status(subject.strip().title(), region.strip().upper())
    return result


@app.get("/api/subjects/available")
def subjects_available():
    """List subjects that have completed curricula."""
    from managers.mongodb_manager import mongo_db

    docs = list(mongo_db.generated_curricula.find(
        {"status": "complete"},
        {"subject": 1, "region": 1, "stats": 1, "curriculum_id": 1, "_id": 0},
    ))
    return {"subjects": docs}




# ===== QUESTION ANALYTICS ENDPOINTS =====

class QuestionAnalyticsRequest(BaseModel):
    question_id: str
    correct: bool
    hints_used: int = 0
    time_seconds: float = 0.0
    skipped: bool = False
    skill_id: Optional[str] = None


@app.post("/api/question-analytics")
def record_question_analytics(request: Request, payload: QuestionAnalyticsRequest):
    """Record a question attempt for analytics tracking (fire-and-forget from frontend)."""
    if question_analytics is None:
        raise HTTPException(status_code=503, detail="Question analytics not initialized")

    try:
        student_id = get_current_user(request)
    except HTTPException:
        # Silently fail for analytics -- don't block the user experience
        return {"status": "skipped", "reason": "auth_failed"}

    try:
        question_analytics.record_attempt(
            question_id=payload.question_id,
            student_id=student_id,
            correct=payload.correct,
            hints_used=payload.hints_used,
            time_seconds=payload.time_seconds,
            skipped=payload.skipped,
            skill_id=payload.skill_id,
        )
        return {"status": "recorded"}
    except Exception as e:
        logger.warning(f"[QUESTION_ANALYTICS] Failed to record attempt: {e}")
        return {"status": "error", "detail": str(e)}


@app.get("/api/question-quality/{question_id}")
def get_question_quality(question_id: str):
    """Get quality score and metrics for a specific question."""
    if question_analytics is None:
        raise HTTPException(status_code=503, detail="Question analytics not initialized")

    return question_analytics.get_quality_score(question_id)


@app.get("/api/flagged-questions")
def get_flagged_questions(request: Request, min_attempts: int = 5):
    """Get all questions flagged as low quality."""
    require_admin(request)
    if question_analytics is None:
        raise HTTPException(status_code=503, detail="Question analytics not initialized")

    return {"flagged_questions": question_analytics.get_flagged_questions(min_attempts=min_attempts)}


@app.get("/api/skill-analytics/{skill_id}")
def get_skill_analytics(skill_id: str):
    """Get aggregated analytics for all questions in a skill."""
    if question_analytics is None:
        raise HTTPException(status_code=503, detail="Question analytics not initialized")

    return question_analytics.get_skill_analytics(skill_id)


# ===== QUALITY TRACKING ENDPOINTS =====


@app.post("/api/quality-sweep")
async def run_quality_sweep(request: Request):
    """
    Run a quality sweep across all questions with enough analytics data.
    Admin action that retires, demotes, or boosts questions based on
    aggregated student performance metrics.

    Returns counts of retired, demoted, boosted, and neutral questions.
    """
    require_admin(request)
    if quality_tracker is None:
        raise HTTPException(status_code=503, detail="QualityTracker not initialized")
    results = await quality_tracker.run_quality_sweep()
    return results


@app.get("/api/quality-report")
async def get_quality_report(request: Request):
    """
    Get a summary report of question quality across the system.
    Includes average quality score, score distribution, top/bottom questions,
    recently retired questions, and action summary.
    """
    require_admin(request)
    if quality_tracker is None:
        raise HTTPException(status_code=503, detail="QualityTracker not initialized")
    report = await quality_tracker.get_quality_report()
    return report


# ===== CONTENT GENERATION SERVICE ENDPOINTS =====


@app.post("/api/ensure-pool/{skill_id}")
async def ensure_pool(skill_id: str, request: Request):
    """Trigger pool fill for a skill (admin/debug)."""
    if not content_service:
        raise HTTPException(status_code=503, detail="Content service not initialized")
    body = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()

    # Resolve skill metadata from hierarchy when not provided in body
    skill_name = body.get("skill_name", "")
    grade = body.get("grade", "")
    subject = body.get("subject", "")
    if not skill_name and dash_system and skill_id in dash_system.skills:
        skill_obj = dash_system.skills[skill_id]
        skill_name = skill_obj.name
        grade = grade or skill_obj.grade_level.name
    if not subject and dash_system:
        subject = getattr(dash_system, "subject", "")

    import asyncio
    await asyncio.to_thread(
        content_service.ensure_pool,
        skill_id,
        skill_name=skill_name,
        grade=grade,
        subject=subject,
    )
    stats = content_service.get_pool_stats(skill_id)
    return {"status": "ok", "pool_stats": stats}


@app.get("/api/pool-stats/{skill_id}")
async def get_pool_stats(skill_id: str):
    """Get pool statistics for a skill."""
    if not content_service:
        raise HTTPException(status_code=503, detail="Content service not initialized")
    stats = content_service.get_pool_stats(skill_id)
    return stats


@app.get("/api/generation-audit")
async def get_generation_audit(request: Request, skill_id: str = None, limit: int = 50):
    """Get generation audit log."""
    require_admin(request)
    if not content_service:
        raise HTTPException(status_code=503, detail="Content service not initialized")
    log = content_service.get_audit_log(skill_id, limit)
    return {"entries": log}


@app.get("/api/validation-failures")
async def get_validation_failures(request: Request, limit: int = 50, skill_id: str = None):
    """List recent pre-serve validation failures for debugging."""
    require_admin(request)
    from managers.mongodb_manager import mongo_db
    col = mongo_db.db["validation_failures"]
    query = {}
    if skill_id:
        query["skill_id"] = skill_id
    docs = list(col.find(query).sort("timestamp", -1).limit(limit))
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"failures": docs, "count": len(docs)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("DASH_PORT", 8000))  # DASH API on 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
