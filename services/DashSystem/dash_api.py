import hashlib
import time
import sys
import os
import json
import re
import logging
import random
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Any, List, Dict, Optional
from urllib.parse import urlsplit, urlunsplit
from fastapi import FastAPI, HTTPException, Request
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
_learning_prefetch_cache: Dict[str, dict] = {}  # f"{user_id}:{subject}" → {"q_data": ..., "question_id": ..., "skill_id": ..., "subject": ..., "ts": ...}
_learning_prefetch_lock = threading.Lock()
_warmstart_cache: Dict[str, dict] = {}  # f"{user_id}:{subject}" → {"q_data", "question_id", "skill_id", "ts"}
_warmstart_events: Dict[str, threading.Event] = {}  # signals when warm-start finishes
_warmstart_lock = threading.Lock()
WARMSTART_TTL = 300  # 5 minutes


def _env_float(name: str, default: float) -> float:
    """Read float config from env with safe fallback."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


WARMSTART_WAIT_TIMEOUT = _env_float("DASH_WARMSTART_WAIT_TIMEOUT_S", 1.5)
QUESTION_PARALLEL_BUDGET_S = _env_float("DASH_QUESTION_PARALLEL_BUDGET_S", 5.0)
RECOMMEND_PARALLEL_BUDGET_S = _env_float("DASH_RECOMMEND_PARALLEL_BUDGET_S", 12.0)
ASSESSMENT_PARALLEL_BUDGET_S = _env_float("DASH_ASSESSMENT_PARALLEL_BUDGET_S", 5.0)
LEARNING_Q_LOOKUP_TIMEOUT_S = _env_float("DASH_LEARNING_Q_LOOKUP_TIMEOUT_S", 4.0)
LEARNING_REFILL_LOOKUP_TIMEOUT_S = _env_float("DASH_LEARNING_REFILL_LOOKUP_TIMEOUT_S", 1.0)
ADAPTIVE_NEXT_TOTAL_BUDGET_S = _env_float("DASH_ADAPTIVE_NEXT_BUDGET_S", 5.0)
ADAPTIVE_NEXT_POOL_LOOKUP_TIMEOUT_S = _env_float("DASH_ADAPTIVE_NEXT_POOL_LOOKUP_TIMEOUT_S", 1.5)
ADAPTIVE_NEXT_LATE_PREFETCH_GRACE_S = _env_float("DASH_ADAPTIVE_NEXT_LATE_PREFETCH_GRACE_S", 0.25)
ADAPTIVE_NEXT_LATE_PREFETCH_POLL_S = _env_float("DASH_ADAPTIVE_NEXT_LATE_PREFETCH_POLL_S", 0.08)
ADAPTIVE_NEXT_SYNC_JIT = _env_bool("DASH_ADAPTIVE_NEXT_SYNC_JIT", False)


def _run_with_timeout(fn, timeout_s: float, *args, **kwargs):
    """Run a callable with a hard timeout and return None on timeout/failure."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = None
    try:
        future = executor.submit(fn, *args, **kwargs)
        return future.result(timeout=max(0.05, float(timeout_s)))
    except Exception:
        if future is not None:
            future.cancel()
        logger.error(f"[_run_with_timeout] Error or timeout after {timeout_s}s:")
        logger.error(traceback.format_exc())
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


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


def _persist_user_subject_selection(user_id: str, subject: str, region: str) -> None:
    """Persist the user's selected subject so later question requests can re-pin safely."""
    try:
        from managers.mongodb_manager import mongo_db
        mongo_db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "selected_subject": subject,
                    "selected_region": region,
                    "selected_subject_updated_at": datetime.now(),
                }
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"[SUBJECT_SWITCH] Failed to persist selected subject for {user_id}: {e}")


def _get_user_subject_selection(user_id: str) -> tuple[Optional[str], Optional[str]]:
    """Return (subject, region) selected by the user, if available."""
    try:
        from managers.mongodb_manager import mongo_db
        doc = mongo_db.users.find_one(
            {"user_id": user_id},
            {"selected_subject": 1, "selected_region": 1, "_id": 0},
        )
        if not doc:
            return None, None
        subject = doc.get("selected_subject")
        region = doc.get("selected_region")
        if isinstance(subject, str) and subject.strip():
            normalized_subject = subject.strip().title()
            normalized_region = region.strip().upper() if isinstance(region, str) and region.strip() else "US"
            return normalized_subject, normalized_region
    except Exception as e:
        logger.warning(f"[SUBJECT_SWITCH] Failed to read selected subject for {user_id}: {e}")
    return None, None

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


_LOCALHOST_HOSTNAMES = {"localhost", "127.0.0.1", "0.0.0.0"}


def _request_origin(request: Request) -> str:
    """Resolve request origin, honoring proxy headers when present."""
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    host = forwarded_host or (request.headers.get("host") or "").split(",")[0].strip()
    if not host:
        host = request.url.netloc

    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    scheme = forwarded_proto or request.url.scheme or "http"

    if not host:
        return ""
    return f"{scheme}://{host}"


def _rewrite_localhost_url(url: Any, request_origin: str) -> Any:
    """Rewrite absolute localhost URLs to the current request origin."""
    if not isinstance(url, str) or not url or not request_origin:
        return url

    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    if (parsed.hostname or "").lower() not in _LOCALHOST_HOSTNAMES:
        return url

    origin = urlsplit(request_origin)
    if not origin.scheme or not origin.netloc:
        return url
    return urlunsplit((origin.scheme, origin.netloc, parsed.path, parsed.query, parsed.fragment))


def _rewrite_localhost_image_urls(payload: Any, request: Request) -> Any:
    """Patch image widget URLs in response payloads so localhost doesn't leak to clients."""
    request_origin = _request_origin(request)
    if not request_origin:
        return payload

    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        widgets = (((item.get("question") or {}).get("widgets")) or {})
        if not isinstance(widgets, dict):
            continue
        for widget in widgets.values():
            if not isinstance(widget, dict) or widget.get("type") != "image":
                continue
            options = widget.get("options") or {}
            if not isinstance(options, dict):
                continue
            background = options.get("backgroundImage") or {}
            if not isinstance(background, dict):
                continue
            existing_url = background.get("url")
            rewritten_url = _rewrite_localhost_url(existing_url, request_origin)
            if rewritten_url != existing_url:
                background["url"] = rewritten_url
    return payload


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

            # Pre-warm pools for popular subjects (background task)
            def _warmup_popular_subjects():
                """Background task to pre-warm question pools for popular subjects."""
                import time
                time.sleep(5)  # Wait for startup to complete
                popular_subjects = ["Math", "Science", "English", "Biology"]
                popular_grades = [5, 6, 7, 8]  # Middle school focus
                logger.info(f"[POOL_WARMUP] Starting background warmup for {len(popular_subjects)} subjects...")

                for subject in popular_subjects:
                    try:
                        # Get sample skills for this subject
                        skills = list(mongo_db.questions_db.skills.find({
                            "subject": subject
                        }).limit(10))

                        for skill_doc in skills[:5]:  # Warm first 5 skills per subject
                            skill_id = skill_doc.get("unit_id") or skill_doc.get("_id")
                            if not skill_id:
                                continue

                            # Warm medium difficulty bucket (most common)
                            try:
                                content_service.ensure_pool_sync(
                                    skill_id=str(skill_id),
                                    difficulty_bucket="medium",
                                    count=3  # Small initial pool
                                )
                                logger.info(f"[POOL_WARMUP] Warmed {subject} skill: {skill_id}")
                            except Exception as e_skill:
                                logger.warning(f"[POOL_WARMUP] Failed to warm {subject}/{skill_id}: {e_skill}")

                    except Exception as e_subj:
                        logger.warning(f"[POOL_WARMUP] Failed to warm subject {subject}: {e_subj}")

                logger.info("[POOL_WARMUP] Background warmup complete")

            # Start warmup in background thread
            import threading
            threading.Thread(target=_warmup_popular_subjects, daemon=True).start()

        except ImportError:
            logger.warning("ContentGenerationService not available (module not found). Pool-based serving disabled.")
        except Exception as e_cs:
            logger.warning(f"ContentGenerationService failed to initialize: {e_cs}. Pool-based serving disabled.")
    except Exception as e:
        logger.error(f"Failed to initialize DASHSystem: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # In non-production, allow the server to start even if DASH init fails
        # so health checks and basic endpoints still work for dev/QA.
        is_prod = (os.getenv('ENVIRONMENT') or os.getenv('APP_ENV') or '').lower() in {'prod', 'production'}
        if is_prod:
            raise
        logger.warning("DASHSystem init failed — server starting in degraded mode (dev)")
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
    question_id: str = Field(..., max_length=200)
    skill_ids: List[str]
    is_correct: bool
    response_time_seconds: float = Field(..., ge=0, le=3600)
    selected_answer: Optional[str] = Field(default=None, max_length=5000)
    selected_answer_index: Optional[int] = None


class ResponsiveHintRequest(BaseModel):
    question_id: str = Field(..., max_length=200)
    skill_id: str = Field(..., max_length=200)
    question_text: str = Field(..., max_length=10000)
    selected_answer: str = Field(..., max_length=5000)
    correct_answer: str = Field(..., max_length=5000)


class RecommendNextRequest(BaseModel):
    current_question_ids: List[str]
    count: int = Field(default=5, ge=1, le=50)


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
    first_question = _rewrite_localhost_image_urls(first_question, request)

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
    question = _rewrite_localhost_image_urls(question, request)
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
    dash_questions: List[Question],
    subject: Optional[str] = None,
) -> List[Dict]:
    """Load Perseus items for DASH-selected questions.

    Questions with perseus_data already attached (warm-start, pool) are used directly.
    Routes AI-generated questions (ai_q_ prefix) to ai_generated_questions collection
    and Khan questions to questions_db.questions collection.
    """
    from managers.mongodb_manager import mongo_db

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
            from services.DashSystem.pre_serve_validator import validate_pre_serve
        except Exception as e:
            # Validator unavailable — pass through all results
            logger.debug(f"[VALIDATOR] Pre-serve validator unavailable: {e}")
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
                    subject=subject,
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
        from services.DashSystem.pre_serve_validator import validate_pre_serve
    except Exception as e:
        # Validator unavailable — pass through all results
        logger.warning(f"[VALIDATOR] Pre-serve validator unavailable: {e}")
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
                subject=subject,
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
                    'unit_id': question_doc.get('unit_id') or (dash_q.skill_ids[0] if dash_q.skill_ids else None),  # Current module (unit) ID — fallback to skill_id
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
        jwt_payload = get_jwt_payload(request)
        user_id = jwt_payload.get("sub")
        jwt_age = jwt_payload.get("age")
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
        active_subject, _ = _get_user_subject_selection(user_id)
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(
            selected_questions,
            subject=active_subject or dash_system.subject,
        )
        perseus_items = _post_process_with_age_fallback(
            perseus_items,
            active_subject or dash_system.subject,
            jwt_age if jwt_age else None,
            "preloaded_questions",
        )
        logger.info(f"[PRELOADED] Loaded {len(perseus_items)} Perseus questions from MongoDB (after widget filter)")

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
    selected_subject, selected_region = _get_user_subject_selection(user_id)
    if selected_subject:
        _switch_subject_if_needed(selected_subject, selected_region or "US")
    active_subject = (selected_subject or dash_system.subject or "").strip()
    active_subject_lower = active_subject.lower()

    logger.info(f"\n{'='*80}")
    logger.info(f"[NEW_SESSION] Requesting {sample_size} questions for user: {user_id}")
    if active_subject:
        logger.info(f"[NEW_SESSION] Subject pinned to {active_subject}/{selected_region or dash_system.region}")
    logger.info(f"{'='*80}\n")

    # Ensure the user exists and is loaded (age from JWT fallback if not in MongoDB)
    user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
    
    # Use DASH intelligence with flexible selection to get ALL questions
    current_time = time.time()
    selected_questions = []
    selected_question_ids = []  # Track selected question IDs to avoid duplicates
    selected_content_hashes = set()  # Track content hashes to catch identical-content duplicates
    
    # --- Check warm-start cache for Q1 (pre-generated by start_subject) ---
    warmstart_key = f"{user_id}:{active_subject_lower}"
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
        q1 = _run_with_timeout(
            dash_system.get_next_question_flexible,
            LEARNING_Q_LOOKUP_TIMEOUT_S,
            user_id,
            current_time,
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
                # 1. Immediate Pool/Reuse/Khan Fallback
                if dash_system.content_service:
                    pool_q = dash_system.content_service.pop_question(
                        skill_id, skill.difficulty, exclude_ids=exclude_snapshot,
                        subject=active_subject)
                    if pool_q:
                        logger.info(f"[LEARNING_PATH] QUICK HIT for {skill_id}")
                        q_id = pool_q.get("question_id") or pool_q.get("dash_metadata", {}).get("dash_question_id", f"q_{skill_id}")
                        if "dash_metadata" not in pool_q:
                            pool_q["dash_metadata"] = {
                                "dash_question_id": q_id,
                                "skill_ids": [skill_id],
                                "difficulty": pool_q.get("difficulty", skill.difficulty),
                                "skill_names": [skill.name],
                                "ai_generated": pool_q.get("ai_generated", False),
                            }
                        from services.DashSystem.dash_system import Question
                        return Question(
                            question_id=q_id, skill_ids=[skill_id], content="",
                            difficulty=pool_q.get("difficulty", skill.difficulty),
                            expected_time_seconds=60.0, perseus_data=pool_q,
                        )
                
                # 2. Miss? Trigger background AI generation but don't wait.
                if dash_system.use_ai_questions and dash_system.ai_provider:
                    logger.info(f"[LEARNING_PATH] Background refill triggered for {skill_id}")
                    dash_system.ai_provider._trigger_background_refill(
                        skill_id, skill.name, skill.name, skill.difficulty,
                        skill.grade_level.name, user_profile.age or 10, user_id,
                        subject=active_subject
                    )
                return None
            except Exception as e:
                logger.warning(f"[LEARNING_PATH] Parallel fetch failed for {skill_id}: {e}")
                return None

        if target_skill_ids:
            max_workers = min(len(target_skill_ids), 4)
            executor = ThreadPoolExecutor(max_workers=max_workers)
            pending = set()
            deadline = time.time() + QUESTION_PARALLEL_BUDGET_S
            try:
                pending = {executor.submit(_fetch_for_skill, sid) for sid in target_skill_ids}
                while pending and len(selected_questions) < sample_size:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        logger.warning(
                            f"[LEARNING_PATH] Parallel fetch timed out with {len(pending)} pending skill jobs"
                        )
                        break
                    done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                    if not done:
                        logger.warning(
                            f"[LEARNING_PATH] Parallel fetch made no progress before timeout with {len(pending)} pending"
                        )
                        break
                    for future in done:
                        try:
                            result = future.result()
                        except Exception as e:
                            logger.warning(f"[PARALLEL_FETCH] Future failed: {e}")
                            continue
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
                            if len(selected_questions) >= sample_size:
                                break
            finally:
                for future in pending:
                    future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
        else:
            # No diverse skills found — fall back to serial DASH selection
            for i in range(remaining):
                q = _run_with_timeout(
                    dash_system.get_next_question_flexible,
                    LEARNING_Q_LOOKUP_TIMEOUT_S,
                    user_id,
                    current_time,
                    exclude_question_ids=selected_question_ids,
                    user_profile=user_profile,
                    fast_mode=True,
                )
                if q:
                    selected_questions.append(q)
                    selected_question_ids.append(q.question_id)
                else:
                    break

        if len(selected_questions) < sample_size:
            logger.info(f"[SESSION_END] Selected {len(selected_questions)}/{sample_size} questions (no more available)")
    
    # If no questions were selected, never serve cross-subject random content.
    # Optionally allow a subject-scoped AI fallback in DEV_MODE.
    if not selected_questions:
        current_subject = active_subject
        if os.getenv("DEV_MODE", "false").lower() == "true" and dash_system.mongo and current_subject:
            logger.warning(
                f"[DEV_BYPASS] No DASH questions selected, trying subject-scoped AI fallback for {current_subject}"
            )
            ai_docs = list(dash_system.mongo.ai_generated_questions.aggregate([
                {"$match": {"subject": current_subject}},
                {"$sample": {"size": sample_size * 3}},
            ]))
            ai_questions = []
            for doc in ai_docs:
                qid = doc.get("question_id")
                if not qid:
                    continue
                ai_questions.append(
                    Question(
                        question_id=qid,
                        skill_ids=[doc.get("skill_id", "unknown")],
                        content="",
                        difficulty=float(doc.get("difficulty", 0.5)),
                        expected_time_seconds=60.0,
                    )
                )
            if ai_questions:
                random_perseus = _load_ai_generated_perseus_items(ai_questions)
                random_perseus = [q for q in random_perseus if not _has_only_broken_widgets(q)][:sample_size]
                if random_perseus:
                    logger.info(
                        f"[DEV_BYPASS] Served {len(random_perseus)} subject-scoped fallback questions for {current_subject}"
                    )
                    return _rewrite_localhost_image_urls([_strip_objectids(q) for q in random_perseus], request)
        emergency_items: List[Dict[str, Any]] = []
        for idx in range(max(1, sample_size)):
            emergency_items.append(
                _build_emergency_subject_question(
                    subject=current_subject or active_subject or dash_system.subject or "General",
                    age=user_profile.age if user_profile and user_profile.age else (jwt_age if jwt_age else None),
                    current_grade=user_profile.current_grade if user_profile else None,
                    question_number=idx + 1,
                    question_id_prefix=f"learning_emg_{user_id}",
                )
            )
        emergency_items = _post_process_with_age_fallback(
            emergency_items,
            current_subject or active_subject,
            jwt_age if jwt_age else None,
            "learning_emergency_fallback",
            allow_age_relax=False,
        ) or emergency_items
        logger.warning(
            f"[CONTENT_PIPELINE] No selected questions for subject={current_subject or 'unknown'}; "
            f"serving {len(emergency_items)} emergency fallback question(s)"
        )
        return _rewrite_localhost_image_urls(emergency_items[:sample_size], request)
    
    # Load Perseus items from MongoDB for all DASH-selected questions
    try:
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(
            selected_questions,
            subject=active_subject,
        )
        logger.info(f"[MONGODB] Loaded {len(perseus_items)} Perseus questions from MongoDB with full metadata")
    except Exception as e:
        logger.error(f"[ERROR] MongoDB Perseus load failed: {e}. Local fallback disabled.")
        raise HTTPException(status_code=500, detail=f"Failed to load Perseus questions from MongoDB: {e}")

    # Final content-pipeline safety gate: dedupe + scope + renderability.
    perseus_items = _post_process_with_age_fallback(
        perseus_items,
        active_subject,
        jwt_age if jwt_age else None,
        "learning_initial_batch",
        allow_age_relax=False,
    )

    # The system now relies on the initial parallel pool/fallback batch.
    # Background generation will refill the pool for subsequent requests.

    # Subject-scoped Mongo fallback for sparse pools: keeps correctness while avoiding 1-2 question sessions.
    if len(perseus_items) < sample_size and dash_system.mongo and active_subject:
        deficit = sample_size - len(perseus_items)
        try:
            raw_docs = list(dash_system.mongo.ai_generated_questions.aggregate([
                {"$match": {"subject": active_subject}},
                {"$sample": {"size": max(deficit * 8, 8)}},
            ]))
            fallback_items = []
            for doc in raw_docs:
                raw = doc.get("perseus_json") or doc.get("perseus_data")
                if not isinstance(raw, dict):
                    continue
                item = dict(raw)
                skill_id = doc.get("skill_id", "")
                skill_ids = doc.get("skill_ids", [skill_id])
                item["dash_metadata"] = {
                    "dash_question_id": doc.get("question_id", ""),
                    "skill_ids": skill_ids,
                    "difficulty": doc.get("difficulty", 0.5),
                    "skill_names": [doc.get("skill_name", "AI Generated")],
                    "unit_name": doc.get("skill_name", "AI Generated"),
                    "lesson_name": doc.get("lesson_name", "Practice") or "Practice",
                    "ai_generated": True,
                    "mongodb_id": str(doc.get("_id", "")),
                }
                fallback_items.append(item)

            processed_fallback = _post_process_with_age_fallback(
                fallback_items,
                active_subject,
                jwt_age if jwt_age else None,
                "learning_subject_fallback",
                allow_age_relax=False,
            )
            existing_hashes = {_compute_content_hash(i) for i in perseus_items}
            existing_ids = {
                str((i.get("dash_metadata") or {}).get("dash_question_id") or "")
                for i in perseus_items
            }
            added = 0
            for item in processed_fallback:
                qid = str((item.get("dash_metadata") or {}).get("dash_question_id") or "")
                ch = _compute_content_hash(item)
                if (qid and qid in existing_ids) or ch in existing_hashes:
                    continue
                perseus_items.append(item)
                if qid:
                    existing_ids.add(qid)
                existing_hashes.add(ch)
                added += 1
                if len(perseus_items) >= sample_size:
                    break
            if added:
                logger.info(f"[CONTENT_PIPELINE] Mongo fallback added {added} subject-scoped questions")
        except Exception as e:
            logger.warning(f"[CONTENT_PIPELINE] Mongo fallback failed: {e}")

    # Trim to requested size after all safeguards.
    if len(perseus_items) > sample_size:
        perseus_items = perseus_items[:sample_size]

    if not perseus_items:
        logger.error("[CONTENT_PIPELINE] No valid Perseus questions survived serving pipeline")
        raise HTTPException(status_code=404, detail="No valid questions available right now")

    logger.info(
        f"[SESSION_READY] Returning {len(perseus_items)}/{sample_size} questions "
        f"after pipeline validation\n"
    )

    # Trigger learning-path prefetch for next question in background
    all_served_ids = list(selected_question_ids)
    _trigger_learning_prefetch(user_id, active_subject, all_served_ids, jwt_age if jwt_age else 10)

    return _rewrite_localhost_image_urls(perseus_items, request)

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
        logger.warning(f"Could not fetch student state: {e}")
    
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

    logger.info(f"[SUBMIT_ANSWER] User: {user_id} | Q: {answer.question_id} | Correct: {answer.is_correct}")
    
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

    # Background non-critical tracking (misconceptions, used_count)
    def _do_background_tracking():
        try:
            # Track used_count for AI-generated questions
            if answer.question_id.startswith("ai_q_"):
                mongo_db.ai_generated_questions.update_one(
                    {"question_id": answer.question_id},
                    {"$inc": {"used_count": 1}, "$set": {"last_served_at": datetime.now()}},
                )

            # Track misconception on wrong answers
            if not answer.is_correct and answer.selected_answer is not None:
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
        except Exception as e_bg:
            logger.warning(f"[SUBMIT_ANSWER] Background tracking failed: {e_bg}")

    threading.Thread(target=_do_background_tracking, daemon=True).start()

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
    except Exception as e:
        logger.warning(f"[RESPONSIVE_HINT] Failed to extract misconception for question_id={req.question_id}: {e}")

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
    from managers.mongodb_manager import mongo_db

    ensure_dash_system()
    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")
    jwt_age = jwt_payload.get("age")
    selected_subject, selected_region = _get_user_subject_selection(user_id)
    if selected_subject:
        _switch_subject_if_needed(selected_subject, selected_region or "US")
    active_subject = (selected_subject or dash_system.subject or "").strip()

    logger.info(f"\n{'='*80}")
    logger.info(f"[RECOMMEND_NEXT] User: {user_id}, Current questions: {len(req.current_question_ids)}, Requesting: {req.count}")
    if active_subject:
        logger.info(f"[RECOMMEND_NEXT] Subject pinned to {active_subject}/{selected_region or dash_system.region}")
    logger.info(f"{'='*80}\n")

    # Ensure the user exists and is loaded
    user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
    current_time = time.time()
    
    # Get next questions via skill-assigned parallel generation
    selected_questions = []
    collected_ids = set(req.current_question_ids)
    collected_content_hashes: set = set()

    # --- Check learning-path prefetch cache for Q1 ---
    learning_prefetch_key = f"{user_id}:{active_subject.lower()}" if active_subject else user_id
    with _learning_prefetch_lock:
        cached = _learning_prefetch_cache.pop(learning_prefetch_key, None)
        # Best-effort cleanup for legacy cache entries keyed only by user_id
        if active_subject:
            _learning_prefetch_cache.pop(user_id, None)

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
    # Exclude skills from current questions to diversify (optimized batch lookup)
    current_skill_ids = set()
    if req.current_question_ids:
        docs = list(mongo_db.ai_generated_questions.find(
            {"question_id": {"$in": req.current_question_ids}},
            {"skill_id": 1, "skill_ids": 1}
        ))
        for d in docs:
            if d.get("skill_ids"):
                current_skill_ids.update(d["skill_ids"])
            elif d.get("skill_id"):
                current_skill_ids.add(d["skill_id"])

    # Filter out skills already represented in the current question set
    filtered_skills = [s for s in recommended_skills if s not in current_skill_ids]
    target_skill_ids = (filtered_skills or recommended_skills)[:req.count + 2]
    
    # Trim to avoid excessive parallel jobs if we already have some from prefetch
    needed = max(0, req.count - len(selected_questions))
    if needed == 0:
        target_skill_ids = []
    else:
        target_skill_ids = target_skill_ids[:needed + 2]

    def _fetch_for_skill_rec(skill_id):
        skill = dash_system.skills.get(skill_id)
        if not skill:
            logger.warning(f"[RECOMMEND_NEXT] Skill not found: {skill_id}")
            return None
        try:
            # RECOMMENDATIONS: Instant-only. Use content_service (Pool -> Reuse -> Khan Fallback)
            if dash_system.content_service:
                pool_q = dash_system.content_service.pop_question(
                    skill_id, skill.difficulty, exclude_ids=collected_ids,
                    subject=active_subject)
                
                if pool_q:
                    logger.info(f"[RECOMMEND_NEXT] QUICK HIT for {skill_id} (source: {'AI' if pool_q.get('ai_generated') else 'Khan'})")
                    q_id = pool_q.get("question_id") or pool_q.get("dash_metadata", {}).get("dash_question_id", f"q_{skill_id}_{int(time.time()*1000)}")
                    if "dash_metadata" not in pool_q:
                        pool_q["dash_metadata"] = {
                            "dash_question_id": q_id,
                            "skill_ids": [skill_id],
                            "difficulty": pool_q.get("difficulty", skill.difficulty),
                            "skill_names": [skill.name],
                            "unit_name": skill.name,
                            "lesson_name": "Practice",
                            "ai_generated": pool_q.get("ai_generated", False),
                        }
                    
                    from services.DashSystem.dash_system import Question
                    return Question(
                        question_id=q_id, skill_ids=[skill_id], content="",
                        difficulty=pool_q.get("difficulty", skill.difficulty),
                        expected_time_seconds=60.0, perseus_data=pool_q,
                    )
            
            # If no content immediately available (rare with Khan fallback), trigger background refill but don't wait
            if dash_system.use_ai_questions and dash_system.ai_provider:
                logger.info(f"[RECOMMEND_NEXT] Background warm-up triggered for {skill_id}")
                dash_system.ai_provider._trigger_background_refill(
                    skill_id, skill.name, skill.name, skill.difficulty,
                    skill.grade_level.name, user_profile.age or 10, user_id,
                    subject=active_subject
                )
            
            return None
        except Exception as e:
            logger.warning(f"[RECOMMEND_NEXT] Fetch failed for {skill_id}: {e}", exc_info=True)
            return None

    if target_skill_ids:
        max_workers = min(len(target_skill_ids), 4)
        executor = ThreadPoolExecutor(max_workers=max_workers)
        pending = set()
        deadline = time.time() + RECOMMEND_PARALLEL_BUDGET_S
        try:
            pending = {executor.submit(_fetch_for_skill_rec, sid) for sid in target_skill_ids}
            while pending and len(selected_questions) < req.count:
                remaining = deadline - time.time()
                if remaining <= 0:
                    logger.warning(
                        f"[RECOMMEND_NEXT] Parallel fetch timed out with {len(pending)} pending skill jobs"
                    )
                    break
                done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                if not done:
                    logger.warning(
                        f"[RECOMMEND_NEXT] Parallel fetch made no progress before timeout with {len(pending)} pending"
                    )
                    break
                for future in done:
                    try:
                        result = future.result()
                    except Exception as e:
                        logger.warning(f"[RECOMMEND_NEXT] Future failed: {e}")
                        continue
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
                        if len(selected_questions) >= req.count:
                            break
        finally:
            for future in pending:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

    if not selected_questions:
        logger.info("[RECOMMEND_NEXT] No new questions available")
        return []  # Return empty if no new questions
    
    # Load Perseus items for selected questions
    try:
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(
            selected_questions,
            subject=active_subject,
        )
        perseus_items = _post_process_with_age_fallback(
            perseus_items,
            active_subject,
            jwt_age if jwt_age else None,
            "recommend_next",
        )
        logger.info(f"[RECOMMEND_NEXT] Loaded {len(perseus_items)} new questions (after widget filter)")

        # Verify no overlap with current questions (should not happen due to exclusion, but check for safety)
        new_question_ids = {item.get('dash_metadata', {}).get('dash_question_id') for item in perseus_items if item.get('dash_metadata', {}).get('dash_question_id')}
        current_question_ids_set = set(req.current_question_ids)
        
        # Check for any overlap (should not happen, but log warning if it does)
        overlap = new_question_ids.intersection(current_question_ids_set)
        if overlap:
            logger.warning(f"[RECOMMEND_NEXT] Warning: {len(overlap)} recommended questions overlap with current (should not happen)")
            # Filter out overlapping questions
            perseus_items = [
                item for item in perseus_items
                if item.get('dash_metadata', {}).get('dash_question_id') not in overlap
            ]
            if not perseus_items:
                logger.info("[RECOMMEND_NEXT] All recommended questions were duplicates, returning empty")
                return []
        
        # Trigger learning-path prefetch for the next batch in background
        all_served_ids = list(collected_ids)
        _trigger_learning_prefetch(user_id, active_subject, all_served_ids, jwt_age if jwt_age else 10)

        return _rewrite_localhost_image_urls(perseus_items, request)
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

    # Validate subject is non-empty
    if not subject or not subject.strip():
        raise HTTPException(status_code=400, detail="Subject name is required")

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

        # Pre-select 10 diverse skills from curriculum, filtered by grade (±1 grade range)
        all_skills = list(dash_system.skills.values())

        if not all_skills:
            logger.warning(f"[ASSESSMENT] No skills found for {subject}. Using JIT fallback.")
            from services.DashSystem.dash_system import Skill
            # Create synthetic skill objects to drive JIT generation
            grade_level_enum = list(GradeLevel)[current_grade_value]
            target_skills = [
                Skill(
                    skill_id=f"jit_{subject.lower().replace(' ', '_')}_{i}",
                    name=f"{subject} Concept {i+1}",
                    grade_level=grade_level_enum,
                    difficulty=0.5
                ) for i in range(12)
            ]
            grade_filtered_skills = target_skills
        else:
            # Filter skills to be within ±1 grade of current student grade
            grade_filtered_skills = [
                skill for skill in all_skills
                if abs(skill.grade_level.value - current_grade_value) <= 1
            ]

            # If not enough skills in grade range, expand to ±2 grades
            if len(grade_filtered_skills) < 10:
                logger.warning(f"[ASSESSMENT] Only {len(grade_filtered_skills)} skills in ±1 grade range, expanding to ±2")
                grade_filtered_skills = [
                    skill for skill in all_skills
                    if abs(skill.grade_level.value - current_grade_value) <= 2
                ]

            # If still not enough, use all skills
            if len(grade_filtered_skills) < 10:
                logger.warning(f"[ASSESSMENT] Only {len(grade_filtered_skills)} skills in ±2 grade range, using all skills")
                grade_filtered_skills = all_skills

            random.shuffle(grade_filtered_skills)
            # Pick up to 12 unique skills for parallel generation (to get 10 successful ones)
            target_skills = grade_filtered_skills[:min(len(grade_filtered_skills), 12)]
        logger.info(f"[ASSESSMENT] Pre-selected {len(target_skills)} grade-appropriate skills (student grade: {current_grade_value})")

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

        # Each thread gets a DIFFERENT skill — no competition.
        # Bound total wait so one stuck generation cannot freeze assessment start.
        executor = ThreadPoolExecutor(max_workers=5)
        pending = set()
        deadline = time.time() + ASSESSMENT_PARALLEL_BUDGET_S
        try:
            pending = {executor.submit(_generate_for_skill, skill) for skill in target_skills}
            while pending and len(questions) < 10:
                remaining = deadline - time.time()
                if remaining <= 0:
                    logger.warning(f"[ASSESSMENT] Parallel generation timed out with {len(pending)} pending jobs")
                    break
                done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
                if not done:
                    logger.warning(
                        f"[ASSESSMENT] Parallel generation made no progress before timeout with {len(pending)} pending"
                    )
                    break
                for future in done:
                    try:
                        result = future.result()
                    except Exception as e:
                        logger.warning(f"[ASSESSMENT] Future failed: {e}")
                        continue
                    if result and result.question_id not in exclude_question_ids:
                        questions.append(result)
                        exclude_question_ids.add(result.question_id)
                        if len(questions) >= 10:
                            break
        finally:
            for future in pending:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

        logger.info(f"[ASSESSMENT] Parallel generation returned {len(questions)}/10 questions")

        if len(questions) == 0:
            logger.error(f"[ASSESSMENT] No questions available after all fallbacks")
            raise HTTPException(status_code=400, detail="No questions available for assessment")

        total_questions = len(questions)
        if total_questions < 10:
            logger.warning(f"[ASSESSMENT] Only {total_questions}/10 questions — proceeding with partial assessment")

        # Load Perseus items for the questions
        perseus_items = load_perseus_items_for_dash_questions_from_mongodb(questions, subject=subject)
        perseus_items = _post_process_with_age_fallback(
            perseus_items,
            subject,
            user_profile.age if user_profile and user_profile.age else None,
            "assessment_start_static",
        )

        if not perseus_items:
            logger.error(f"[ASSESSMENT] Failed to load any Perseus items")
            import traceback
            logger.error(traceback.format_exc())
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
        grade_name = user_profile.current_grade.replace("GRADE_", "Grade ").replace("K", "Kindergarten")

        def _jit_first_question(
            exclude_question_ids: Optional[List[str]] = None,
            target_difficulty: float = 0.5,
        ) -> tuple[Optional[Question], Optional[dict]]:
            """Best-effort subject-scoped JIT question for adaptive start."""
            if not dash_system.use_ai_questions or not dash_system.ai_provider:
                return None, None
            synthetic_id = (
                f"assessment_{subject.lower().replace(' ', '_')}_"
                f"{user_profile.current_grade.lower()}_{int(time.time()*1000) % 100000}"
            )
            try:
                ai_result = dash_system.ai_provider.get_question_for_skill(
                    skill_id=synthetic_id,
                    skill_name=f"{subject} for {grade_name}",
                    target_difficulty=target_difficulty,
                    grade_level=user_profile.current_grade,
                    age=user_profile.age if user_profile.age else 10,
                    exclude_question_ids=exclude_question_ids or [],
                    user_id=user_id,
                    fast_mode=True,
                    subject=subject,
                )
            except Exception as e:
                logger.warning(f"[ADAPTIVE_ASSESSMENT] JIT generation failed: {e}")
                return None, None

            if not ai_result:
                return None, None

            dm = ai_result.get("dash_metadata", {})
            qid = dm.get("dash_question_id")
            if not qid:
                return None, None
            if exclude_question_ids and qid in exclude_question_ids:
                return None, None

            q = Question(
                question_id=qid,
                skill_ids=[synthetic_id],
                content="",
                difficulty=dm.get("difficulty", target_difficulty),
                expected_time_seconds=60.0,
            )
            return q, ai_result

        def _subject_fallback_first_question(
            exclude_question_ids: Optional[List[str]] = None,
            target_difficulty: float = 0.5,
        ) -> tuple[Optional[Question], Optional[dict]]:
            """Best-effort subject-scoped Mongo fallback for adaptive assessment start."""
            excluded = {str(qid).strip() for qid in (exclude_question_ids or []) if qid}
            try:
                docs = list(mongo_db.ai_generated_questions.aggregate([
                    {"$match": {"subject": subject}},
                    {"$sample": {"size": 40}},
                    {"$project": {"question_id": 1, "skill_ids": 1, "skill_id": 1}},
                ]))
            except Exception as e:
                logger.warning(f"[ADAPTIVE_ASSESSMENT] Subject fallback sample failed: {e}")
                return None, None

            for doc in docs:
                source_qid = str(doc.get("question_id") or "").strip()
                if not source_qid or source_qid in excluded:
                    continue

                candidate_data = _load_question_perseus(source_qid, mongo_db)
                if not candidate_data:
                    continue
                if (
                    _has_only_broken_widgets(candidate_data)
                    or not _has_answer_space(candidate_data)
                    or not _is_subject_scoped_question(candidate_data, subject)
                ):
                    continue

                cleaned = _post_process_with_age_fallback(
                    [candidate_data],
                    subject,
                    jwt_age if jwt_age else None,
                    "assessment_start_subject_fallback",
                )
                if not cleaned:
                    continue
                candidate_data = cleaned[0]

                dm = candidate_data.setdefault("dash_metadata", {})
                dm["source_question_id"] = source_qid
                raw_skill_ids = dm.get("skill_ids") or doc.get("skill_ids") or []
                if isinstance(raw_skill_ids, str):
                    raw_skill_ids = [raw_skill_ids]
                skill_id = ""
                if isinstance(raw_skill_ids, list):
                    for sid in raw_skill_ids:
                        sid_text = str(sid or "").strip()
                        if sid_text:
                            skill_id = sid_text
                            break
                if not skill_id:
                    skill_id = str(doc.get("skill_id") or "").strip()
                if not dm.get("skill_ids"):
                    dm["skill_ids"] = [skill_id] if skill_id else []
                dm["dash_question_id"] = source_qid

                return Question(
                    question_id=source_qid,
                    skill_ids=[skill_id] if skill_id else [],
                    content="",
                    difficulty=target_difficulty,
                    expected_time_seconds=60.0,
                ), candidate_data

            return None, None

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
            "updated_at": datetime.now(),
            "status": "in_progress",
        }
        insert_result = mongo_db.db["assessment_sessions"].insert_one(session)
        logger.info(f"[ADAPTIVE_ASSESSMENT] Created session {assessment_id} for user {user_id}, subject={subject}. MongoDB _id={insert_result.inserted_id}")

        # Verify session was created
        verify_session = mongo_db.db["assessment_sessions"].find_one({"assessment_id": assessment_id})
        if not verify_session:
            logger.error(f"[ADAPTIVE_ASSESSMENT] CRITICAL: Session {assessment_id} not found immediately after insert!")
        else:
            logger.info(f"[ADAPTIVE_ASSESSMENT] Verified session exists: {verify_session.get('assessment_id')}, status={verify_session.get('status')}")

        def _promote_emergency_first_question(reason: str) -> tuple[Question, dict]:
            emergency_data = _build_emergency_subject_question(
                subject=subject,
                age=jwt_age if jwt_age else user_profile.age,
                current_grade=user_profile.current_grade,
                question_number=1,
                question_id_prefix=f"{assessment_id}_{reason}",
            )
            cleaned = _post_process_with_age_fallback(
                [emergency_data],
                subject,
                jwt_age if jwt_age else None,
                f"assessment_start_emergency_{reason}",
                allow_age_relax=False,
            )
            if cleaned:
                emergency_data = cleaned[0]

            dm = emergency_data.setdefault("dash_metadata", {})
            emergency_qid = str(dm.get("dash_question_id") or f"{assessment_id}_emergency_start")
            raw_skill_ids = dm.get("skill_ids")
            if isinstance(raw_skill_ids, list):
                emergency_skill_ids = [str(s).strip() for s in raw_skill_ids if str(s).strip()]
            elif isinstance(raw_skill_ids, str) and raw_skill_ids.strip():
                emergency_skill_ids = [raw_skill_ids.strip()]
            else:
                emergency_skill_ids = [f"{subject.lower().replace(' ', '_')}_emergency_start"]
            dm["dash_question_id"] = emergency_qid
            dm["skill_ids"] = emergency_skill_ids

            logger.warning(
                f"[ADAPTIVE_ASSESSMENT] Using emergency first question ({reason}) qid={emergency_qid}"
            )
            return Question(
                question_id=emergency_qid,
                skill_ids=emergency_skill_ids,
                content="",
                difficulty=float(dm.get("difficulty", 0.5)),
                expected_time_seconds=float(dm.get("expected_time_seconds", 60.0)),
            ), emergency_data

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
            first_q = _run_with_timeout(
                dash_system.get_next_question_flexible,
                LEARNING_Q_LOOKUP_TIMEOUT_S,
                user_id,
                current_time,
                user_profile=user_profile,
                fast_mode=True,
                force_grade_range=True,
            )

        if not first_q:
            # Last resort: try any grade (no grade range restriction)
            first_q = _run_with_timeout(
                dash_system.get_next_question_flexible,
                LEARNING_Q_LOOKUP_TIMEOUT_S,
                user_id,
                current_time,
                user_profile=user_profile,
                fast_mode=True,
            )

        # Final fallback: subject-scoped JIT question for sparse/new subjects.
        if not first_q:
            logger.info(f"[ADAPTIVE_ASSESSMENT] No pool question — JIT generating for {subject}/{grade_name}")
            first_q, q_data = _jit_first_question(exclude_question_ids=[], target_difficulty=0.5)
            if first_q:
                logger.info(f"[ADAPTIVE_ASSESSMENT] JIT generated first question {first_q.question_id}")

        if not first_q:
            fallback_q, fallback_data = _subject_fallback_first_question(
                exclude_question_ids=[],
                target_difficulty=0.5,
            )
            if fallback_q and fallback_data:
                first_q = fallback_q
                q_data = fallback_data
                logger.warning(f"[ADAPTIVE_ASSESSMENT] Promoted subject fallback {first_q.question_id} after pool/JIT miss")
            else:
                first_q, q_data = _promote_emergency_first_question("pool_jit_miss")

        # Load Perseus data (warm-start already has it; pool/JIT need loading)
        if not q_data:
            q_data = getattr(first_q, "perseus_data", None) or _load_question_perseus(first_q.question_id, mongo_db)
        if not q_data:
            fallback_q, fallback_data = _subject_fallback_first_question(
                exclude_question_ids=[first_q.question_id],
                target_difficulty=0.5,
            )
            if fallback_q and fallback_data:
                first_q = fallback_q
                q_data = fallback_data
                logger.warning(f"[ADAPTIVE_ASSESSMENT] Promoted subject fallback {first_q.question_id} after load failure")
            else:
                first_q, q_data = _promote_emergency_first_question("perseus_load")

        # Skip questions that fail render/scope guards
        if (
            _has_only_broken_widgets(q_data)
            or not _has_answer_space(q_data)
            or not _is_subject_scoped_question(q_data, subject)
        ):
            logger.info(f"[ADAPTIVE_ASSESSMENT] Skipping invalid first question {first_q.question_id} — retrying")
            q_data = None
            user_profile = dash_system.load_user_or_create(user_id, age=jwt_age if jwt_age else 5)
            current_time = time.time()
            for _retry in range(3):
                alt_q = _run_with_timeout(
                    dash_system.get_next_question_flexible,
                    LEARNING_REFILL_LOOKUP_TIMEOUT_S,
                    user_id,
                    current_time,
                    user_profile=user_profile,
                    fast_mode=True,
                    exclude_question_ids=[first_q.question_id],
                )
                if alt_q:
                    alt_data = _load_question_perseus(alt_q.question_id, mongo_db)
                    if (
                        alt_data
                        and not _has_only_broken_widgets(alt_data)
                        and _has_answer_space(alt_data)
                        and _is_subject_scoped_question(alt_data, subject)
                    ):
                        first_q = alt_q
                        q_data = alt_data
                        break

            # If pool retries still fail validation, do one explicit JIT fallback.
            if not q_data:
                fallback_q, fallback_data = _jit_first_question(
                    exclude_question_ids=[first_q.question_id],
                    target_difficulty=0.5,
                )
                if (
                    fallback_q
                    and fallback_data
                    and not _has_only_broken_widgets(fallback_data)
                    and _has_answer_space(fallback_data)
                    and _is_subject_scoped_question(fallback_data, subject)
                ):
                    first_q = fallback_q
                    q_data = fallback_data

            if not q_data:
                fallback_q, fallback_data = _subject_fallback_first_question(
                    exclude_question_ids=[first_q.question_id],
                    target_difficulty=0.5,
                )
                if fallback_q and fallback_data:
                    first_q = fallback_q
                    q_data = fallback_data
                    logger.warning(f"[ADAPTIVE_ASSESSMENT] Promoted subject fallback {first_q.question_id} after validation retries")
                else:
                    first_q, q_data = _promote_emergency_first_question("validation_retries")

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
        q_data = _post_process_with_age_fallback(
            [q_data],
            subject,
            jwt_age if jwt_age else None,
            "assessment_start_adaptive",
        )
        if not q_data:
            fallback_q, fallback_data = _subject_fallback_first_question(
                exclude_question_ids=[first_q.question_id],
                target_difficulty=0.5,
            )
            if fallback_q and fallback_data:
                first_q = fallback_q
                q_data = [fallback_data]
                logger.warning(f"[ADAPTIVE_ASSESSMENT] Promoted subject fallback {first_q.question_id} after post-process drop")
            else:
                first_q, emergency_data = _promote_emergency_first_question("post_process")
                q_data = [emergency_data]
        q_data = q_data[0]

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


@app.get("/assessment/resume/{assessment_id}")
def resume_assessment(
    request: Request,
    assessment_id: str
):
    """
    Resume an in-progress assessment session after page refresh.
    Returns current question and progress info.
    """
    ensure_dash_system()
    from managers.mongodb_manager import mongo_db

    jwt_payload = get_jwt_payload(request)
    user_id = jwt_payload.get("sub")

    # Find the session
    session = mongo_db.db["assessment_sessions"].find_one({
        "assessment_id": assessment_id,
        "user_id": user_id,
        "status": "in_progress"
    })

    if not session:
        logger.warning(f"[RESUME_ASSESSMENT] Session {assessment_id} not found or already completed for user {user_id}")
        raise HTTPException(status_code=404, detail="Assessment session not found or already completed")

    questions_asked = session.get("questions_asked", 0)
    max_questions = session.get("max_questions", 10)
    current_diff = session.get("current_difficulty", 0.5)
    subject = session.get("subject", "")

    # If no questions answered yet, they can just restart
    if questions_asked == 0:
        raise HTTPException(status_code=404, detail="No progress to resume. Please start a new assessment.")

    # If already completed all questions
    if questions_asked >= max_questions:
        raise HTTPException(status_code=404, detail="Assessment already completed")

    # Get the next question for them to answer
    # Use the existing get_next_question_flexible logic
    # Signature: (student_id, current_time, exclude_question_ids, force_grade_range, user_profile, exclude_skill_ids, fast_mode)
    current_time = time.time()
    try:
        next_q = dash_system.get_next_question_flexible(
            user_id,
            current_time,
            exclude_question_ids=session.get("used_question_ids", []),
            fast_mode=True,
        )

        if not next_q:
            raise HTTPException(status_code=503, detail="No questions available to resume")

        # Load and patch the question
        q_data = _load_question_perseus(next_q.question_id, mongo_db)
        if not q_data:
            raise HTTPException(status_code=500, detail="Failed to load question")

        _patch_numeric_input_widgets(q_data)
        cleaned = _post_process_with_age_fallback(
            [q_data],
            subject,
            jwt_age if jwt_age else None,
            "assessment_resume",
        )
        if not cleaned:
            raise HTTPException(status_code=500, detail="Question processing failed")

        q_data = cleaned[0]
        q_data.setdefault("dash_metadata", {})["dash_question_id"] = next_q.question_id
        if next_q.skill_ids:
            q_data["dash_metadata"]["skill_ids"] = next_q.skill_ids

        return {
            "assessment_id": assessment_id,
            "subject": subject,
            "question_number": questions_asked + 1,
            "total_questions": max_questions,
            "current_difficulty": round(current_diff, 3),
            "question": q_data,
            "resumed": True,
        }

    except Exception as e:
        logger.error(f"[RESUME_ASSESSMENT] Error getting next question: {e}")
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(e)}")


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
        # Defensive logging: check if session exists with different status or wrong user_id
        all_matching = list(mongo_db.db["assessment_sessions"].find({"assessment_id": payload.assessment_id}))
        user_sessions = list(mongo_db.db["assessment_sessions"].find({"user_id": user_id}).limit(5))
        logger.error(
            f"[ASSESSMENT_NEXT] Session not found for assessment_id={payload.assessment_id}, user_id={user_id}. "
            f"Found {len(all_matching)} sessions with this assessment_id (any user/status): {all_matching}. "
            f"User has {len(user_sessions)} recent sessions: {user_sessions}"
        )
        # Attempt recovery: if session exists but with different status, update it
        recovery_session = mongo_db.db["assessment_sessions"].find_one({"assessment_id": payload.assessment_id, "user_id": user_id})
        if recovery_session:
            logger.warning(f"[ASSESSMENT_NEXT] Found session with status={recovery_session.get('status')}. Updating to 'in_progress'.")
            mongo_db.db["assessment_sessions"].update_one(
                {"assessment_id": payload.assessment_id, "user_id": user_id},
                {"$set": {"status": "in_progress"}}
            )
            session = mongo_db.db["assessment_sessions"].find_one({"assessment_id": payload.assessment_id, "user_id": user_id})
        else:
            raise HTTPException(status_code=404, detail=f"Assessment session not found. assessment_id={payload.assessment_id}")

    def _resolve_source_question_id(raw_qid: Optional[str]) -> Optional[str]:
        """
        Resolve synthetic fallback IDs back to their source Mongo question_id.
        This avoids dead-ends when emergency fallback tries to load a synthetic ID.
        """
        qid = str(raw_qid or "").strip()
        if not qid:
            return None

        # Unwrap nested fallback IDs up to a few levels.
        for _ in range(4):
            prefix = None
            if qid.startswith("fallback_repeat_"):
                prefix = "fallback_repeat_"
            elif qid.startswith("fallback_"):
                prefix = "fallback_"
            if not prefix:
                break
            tail = qid[len(prefix):]
            parts = tail.rsplit("_", 2)
            if len(parts) != 3:
                break
            source_part = parts[0].strip()
            qid = source_part if source_part else qid
            if not source_part:
                break
        return qid

    # Idempotency guard: if this question was already answered, return the most
    # recently served question instead of recording another attempt.
    existing_answers = session.get("answers", [])
    if isinstance(existing_answers, list) and any(
        isinstance(a, dict) and a.get("question_id") == payload.question_id
        for a in existing_answers
    ):
        logger.warning(
            f"[ADAPTIVE_NEXT] Duplicate answer replay detected for {payload.assessment_id} q={payload.question_id}"
        )
        used_q_ids = session.get("used_question_ids", [])
        latest_served_qid = used_q_ids[-1] if isinstance(used_q_ids, list) and used_q_ids else None
        if latest_served_qid and latest_served_qid != payload.question_id:
            source_qid = _resolve_source_question_id(latest_served_qid)
            q_data = _load_question_perseus(source_qid, mongo_db) if source_qid else None
            if q_data:
                _patch_numeric_input_widgets(q_data)
                subject = (session.get("subject") or "").strip().title()
                cleaned = _post_process_with_age_fallback(
                    [q_data],
                    subject,
                    jwt_age if jwt_age else None,
                    "assessment_replay",
                )
                if cleaned:
                    cleaned[0].setdefault("dash_metadata", {})["dash_question_id"] = latest_served_qid
                    return {
                        "completed": False,
                        "question_number": session.get("questions_asked", 1),
                        "total_questions": session.get("max_questions", 10),
                        "question": cleaned[0],
                        "current_difficulty": round(session.get("current_difficulty", 0.5), 3),
                        "replayed": True,
                    }
        replay_subject = (session.get("subject") or "").strip().title()
        emergency_replay = _build_emergency_subject_question(
            subject=replay_subject,
            age=jwt_age if jwt_age else None,
            question_number=max(1, int(session.get("questions_asked", 1))),
            question_id_prefix=f"{payload.assessment_id}_replay_emergency",
        )
        cleaned_emergency = _post_process_with_age_fallback(
            [emergency_replay],
            replay_subject,
            jwt_age if jwt_age else None,
            "assessment_replay_emergency",
            allow_age_relax=False,
        )
        if cleaned_emergency:
            emergency_replay = cleaned_emergency[0]
        logger.warning(
            f"[ADAPTIVE_NEXT] Returning emergency replay question for {payload.assessment_id}"
        )
        return {
            "completed": False,
            "question_number": session.get("questions_asked", 1),
            "total_questions": session.get("max_questions", 10),
            "question": emergency_replay,
            "current_difficulty": round(session.get("current_difficulty", 0.5), 3),
            "replayed": True,
            "emergency": True,
        }

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
             "$set": {"status": "completed", "current_difficulty": new_diff, "updated_at": datetime.now()},
             "$push": {"answers": answer_record}}
        )
        logger.info(f"[ADAPTIVE_NEXT] Assessment {payload.assessment_id} completed. Total answers: {len(all_answers)}, correct: {correct_count}")

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
    subject = (session.get("subject") or "").strip().title()
    used_q_ids = session.get("used_question_ids", [])
    used_skill_ids = session.get("used_skill_ids", [])
    used_content_hashes = set(session.get("used_content_hashes", []))
    allow_duplicate_content = False

    def _try_assessment_fallback(allow_reuse: bool = False) -> tuple[Optional[Question], Optional[dict], bool]:
        """
        Last-resort subject-scoped fallback for adaptive assessment continuity.
        Returns (next_question, perseus_data, content_reused).
        """
        if not subject:
            return None, None, False
        try:
            sample_size = 48 if allow_reuse else 32
            docs = list(mongo_db.ai_generated_questions.aggregate([
                {"$match": {"subject": subject}},
                {"$sample": {"size": sample_size}},
                {"$project": {"question_id": 1, "skill_ids": 1, "skill_id": 1}},
            ]))
        except Exception as e:
            logger.warning(f"[ADAPTIVE_NEXT] Fallback sample failed: {e}")
            return None, None, False

        for doc in docs:
            source_qid = str(doc.get("question_id") or "").strip()
            if not source_qid:
                continue
            if not allow_reuse and source_qid in used_q_ids:
                continue

            candidate_data = _load_question_perseus(source_qid, mongo_db)
            if not candidate_data:
                continue

            candidate_hash = _compute_content_hash(candidate_data)
            if not allow_reuse and candidate_hash in used_content_hashes:
                continue
            if (
                _has_only_broken_widgets(candidate_data)
                or not _has_answer_space(candidate_data)
                or not _is_subject_scoped_question(candidate_data, subject)
            ):
                continue

            dm = candidate_data.setdefault("dash_metadata", {})
            dm["source_question_id"] = source_qid
            raw_skill_ids = dm.get("skill_ids") or doc.get("skill_ids") or []
            skill_id = ""
            if isinstance(raw_skill_ids, list):
                for sid in raw_skill_ids:
                    sid_text = str(sid or "").strip()
                    if sid_text:
                        skill_id = sid_text
                        break
            elif isinstance(raw_skill_ids, str) and raw_skill_ids.strip():
                skill_id = raw_skill_ids.strip()

            # Ensure a unique served ID so idempotency guard doesn't deadlock on reused content.
            served_qid = source_qid
            reused = source_qid in used_q_ids or candidate_hash in used_content_hashes
            if reused:
                served_qid = f"fallback_{source_qid}_{questions_asked}_{int(time.time() * 1000) % 100000}"

            dm["dash_question_id"] = served_qid
            if not dm.get("skill_ids"):
                dm["skill_ids"] = [skill_id] if skill_id else []

            candidate_q = Question(
                question_id=served_qid,
                skill_ids=[skill_id] if skill_id else [],
                content="",
                difficulty=new_diff,
                expected_time_seconds=60.0,
            )
            return candidate_q, candidate_data, reused

        return None, None, False

    cached_result = None
    with _prefetch_lock:
        if payload.assessment_id in _prefetch_cache:
            cached_result = _prefetch_cache.pop(payload.assessment_id)

    q_data = None
    next_q = None

    def _promote_emergency(reason: str) -> bool:
        nonlocal next_q, q_data, allow_duplicate_content
        emergency_data = _build_emergency_subject_question(
            subject=subject or "General",
            age=jwt_age if jwt_age else None,
            question_number=max(1, questions_asked),
            question_id_prefix=f"{payload.assessment_id}_{reason}",
            difficulty=new_diff,
        )
        cleaned_emergency = _post_process_with_age_fallback(
            [emergency_data],
            subject,
            jwt_age if jwt_age else None,
            f"assessment_next_emergency_{reason}",
            allow_age_relax=False,
        )
        if cleaned_emergency:
            emergency_data = cleaned_emergency[0]

        dm = emergency_data.setdefault("dash_metadata", {})
        emergency_qid = str(dm.get("dash_question_id") or f"{payload.assessment_id}_{reason}_{questions_asked}")
        raw_skill_ids = dm.get("skill_ids")
        if isinstance(raw_skill_ids, list):
            emergency_skill_ids = [str(s).strip() for s in raw_skill_ids if str(s).strip()]
        elif isinstance(raw_skill_ids, str) and raw_skill_ids.strip():
            emergency_skill_ids = [raw_skill_ids.strip()]
        else:
            emergency_skill_ids = [f"{(subject or 'general').lower().replace(' ', '_')}_emergency_next"]
        dm["dash_question_id"] = emergency_qid
        dm["skill_ids"] = emergency_skill_ids

        next_q = Question(
            question_id=emergency_qid,
            skill_ids=emergency_skill_ids,
            content="",
            difficulty=float(dm.get("difficulty", new_diff)),
            expected_time_seconds=float(dm.get("expected_time_seconds", 60.0)),
        )
        q_data = emergency_data
        allow_duplicate_content = True
        logger.warning(f"[ADAPTIVE_NEXT] Promoted emergency next question ({reason}) qid={emergency_qid}")
        return True

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
        # Pin DASH system to the session's subject — prevents wrong-subject
        # questions when concurrent requests switch the global singleton
        if subject:
            _switch_subject_if_needed(subject, "US")

        # Fast-settle retry loop: keep next-question transitions responsive.
        # Heavy generation is moved to background prefetch; request path should stay near-instant.
        import concurrent.futures
        MAX_RETRIES = 1
        retry_start = time.time()

        for attempt in range(MAX_RETRIES):
            # Bail if we've spent too long already
            elapsed = time.time() - retry_start
            if elapsed > ADAPTIVE_NEXT_TOTAL_BUDGET_S:
                logger.warning(f"[ADAPTIVE_NEXT] Retry budget exhausted after {attempt} attempts")
                break

            if attempt == 0:
                # First attempt: bounded pool lookup via DASH.
                # get_next_question_flexible can cascade into slow AI paths, so cap it hard.
                pool_lookup_timeout = max(
                    0.2,
                    min(ADAPTIVE_NEXT_POOL_LOOKUP_TIMEOUT_S, ADAPTIVE_NEXT_TOTAL_BUDGET_S),
                )
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = None
                try:
                    future = executor.submit(
                        dash_system.get_next_question_flexible,
                        user_id,
                        current_time,
                        used_q_ids,  # exclude_question_ids
                        False,       # force_grade_range
                        user_profile,
                        used_skill_ids[-3:] if len(used_skill_ids) >= 3 else None,
                        True,        # fast_mode
                    )
                    next_q = future.result(timeout=pool_lookup_timeout)
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        f"[ADAPTIVE_NEXT] Pool lookup timed out after {pool_lookup_timeout:.2f}s; using fast fallback path"
                    )
                    next_q = None
                except Exception as e:
                    logger.warning(f"[ADAPTIVE_NEXT] Pool lookup failed: {e}")
                    next_q = None
                finally:
                    if future is not None:
                        future.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)

            # Check if we got a duplicate (pool exhausted)
            if next_q and next_q.question_id in used_q_ids:
                logger.info(f"[ADAPTIVE_NEXT] Attempt {attempt+1}: duplicate {next_q.question_id} — forcing JIT")
                next_q = None

            # If we have a valid question, we're done
            if next_q:
                break

            # Prefer a fast subject-scoped fallback before blocking on JIT.
            fallback_q, fallback_data, reused_content = _try_assessment_fallback(allow_reuse=False)
            if fallback_q and fallback_data:
                next_q = fallback_q
                q_data = fallback_data
                allow_duplicate_content = reused_content
                logger.info(
                    f"[ADAPTIVE_NEXT] Fast subject fallback selected: {next_q.question_id} "
                    f"(reused_content={reused_content})"
                )
                break

            # Optional sync JIT fallback (off by default). Keeping this off preserves fast UX.
            if ADAPTIVE_NEXT_SYNC_JIT and dash_system.use_ai_questions and dash_system.ai_provider:
                grade_name = user_profile.current_grade.replace("GRADE_", "Grade ").replace("K", "Kindergarten")
                # Unique synthetic ID per retry to force fresh generation
                synthetic_id = f"assessment_{subject.lower().replace(' ', '_')}_{user_profile.current_grade.lower()}_{questions_asked}_r{attempt}_{int(time.time()*1000) % 100000}"
                try:
                    remaining_budget = ADAPTIVE_NEXT_TOTAL_BUDGET_S - (time.time() - retry_start)
                    if remaining_budget <= 0.5:
                        logger.warning("[ADAPTIVE_NEXT] No remaining retry budget for JIT")
                        break
                    jit_timeout = min(0.8, remaining_budget)
                    # Run JIT with a timeout to prevent hanging
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    future = None
                    try:
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
                        ai_result = future.result(timeout=jit_timeout)
                    finally:
                        if future is not None:
                            future.cancel()
                        executor.shutdown(wait=False, cancel_futures=True)
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
                    logger.warning(f"[ADAPTIVE_NEXT] JIT attempt {attempt+1} timed out after {jit_timeout:.2f}s")
                except Exception as e:
                    logger.warning(f"[ADAPTIVE_NEXT] JIT attempt {attempt+1} failed: {e}")
            else:
                break

    if not next_q:
        # Give background prefetch a very short grace window only.
        # Keep UI snappy and promote fallback quickly if prefetch is not ready.
        LATE_PREFETCH_GRACE_S = ADAPTIVE_NEXT_LATE_PREFETCH_GRACE_S
        LATE_PREFETCH_POLL_S = ADAPTIVE_NEXT_LATE_PREFETCH_POLL_S
        prefetch_wait_start = time.time()
        while time.time() - prefetch_wait_start < LATE_PREFETCH_GRACE_S:
            with _prefetch_lock:
                late_cached = _prefetch_cache.pop(payload.assessment_id, None)
            if not late_cached or not late_cached.get("q_data"):
                time.sleep(LATE_PREFETCH_POLL_S)
                continue

            late_qid = late_cached.get("question_id")
            late_q_data = late_cached.get("q_data")
            late_hash = _compute_content_hash(late_q_data)
            if not late_qid or late_qid in used_q_ids or late_hash in used_content_hashes:
                logger.info(
                    f"[ADAPTIVE_NEXT] Late prefetch stale (dup) {late_qid} — waiting for a fresh item"
                )
                time.sleep(LATE_PREFETCH_POLL_S)
                continue

            next_skill_id = late_cached.get("skill_id", "")
            q_data = late_q_data
            next_q = Question(
                question_id=late_qid,
                skill_ids=[next_skill_id] if next_skill_id else [],
                content="",
                difficulty=new_diff,
                expected_time_seconds=60.0,
            )
            logger.info(f"[ADAPTIVE_NEXT] Late prefetch HIT for {payload.assessment_id}: {late_qid}")
            break

    if not next_q:
        # Last-resort fallback before surfacing a retry error to the frontend.
        fallback_q, fallback_data, reused_content = _try_assessment_fallback(allow_reuse=False)
        if not fallback_q:
            fallback_q, fallback_data, reused_content = _try_assessment_fallback(allow_reuse=True)

        if fallback_q and fallback_data:
            next_q = fallback_q
            q_data = fallback_data
            allow_duplicate_content = reused_content
            logger.warning(
                f"[ADAPTIVE_NEXT] Using subject fallback question {next_q.question_id} (reused_content={reused_content})"
            )
        else:
            # Emergency continuity fallback: reuse latest served question content with a unique ID.
            # This prevents hard stalls while still preserving answer progression.
            latest_qid = used_q_ids[-1] if used_q_ids else None
            source_latest_qid = _resolve_source_question_id(latest_qid)
            emergency_data = _load_question_perseus(source_latest_qid, mongo_db) if source_latest_qid else None
            if emergency_data and _has_answer_space(emergency_data):
                emergency_qid = f"fallback_repeat_{source_latest_qid}_{questions_asked}_{int(time.time() * 1000) % 100000}"
                dm = emergency_data.setdefault("dash_metadata", {})
                dm["dash_question_id"] = emergency_qid
                dm["source_question_id"] = source_latest_qid
                skill_ids = dm.get("skill_ids") or []
                skill_id = skill_ids[0] if isinstance(skill_ids, list) and skill_ids else ""
                next_q = Question(
                    question_id=emergency_qid,
                    skill_ids=[skill_id] if skill_id else [],
                    content="",
                    difficulty=new_diff,
                    expected_time_seconds=60.0,
                )
                q_data = emergency_data
                allow_duplicate_content = True
                logger.warning(f"[ADAPTIVE_NEXT] Emergency repeat fallback used: {emergency_qid}")
            else:
                # Do not auto-complete on generation depletion. Keep assessment in-progress and ask client to retry.
                logger.warning(
                    f"[ADAPTIVE_NEXT] No valid next question generated for {payload.assessment_id}; keeping session in progress"
                )
                _promote_emergency("generation_depletion")

    def _promote_fallback(reason: str) -> bool:
        nonlocal next_q, q_data, allow_duplicate_content
        fb_q, fb_data, reused = _try_assessment_fallback(allow_reuse=False)
        if not fb_q:
            fb_q, fb_data, reused = _try_assessment_fallback(allow_reuse=True)
        if not fb_q or not fb_data:
            return False
        next_q = fb_q
        q_data = fb_data
        allow_duplicate_content = allow_duplicate_content or reused
        logger.warning(
            f"[ADAPTIVE_NEXT] Fallback promoted ({reason}) -> {next_q.question_id} reused={reused}"
        )
        return True

    next_content_hash = ""
    for validation_pass in range(2):
        if not q_data:
            q_data = getattr(next_q, "perseus_data", None) or _load_question_perseus(next_q.question_id, mongo_db)
        if not q_data:
            logger.warning(f"[ADAPTIVE_NEXT] Failed to load Perseus data for {getattr(next_q, 'question_id', 'unknown')}")
            if validation_pass == 0 and _promote_fallback("missing_perseus_data"):
                continue
            _promote_emergency("missing_perseus_data")
            continue

        # Content-hash dedup: reject identical content unless fallback explicitly allows reuse.
        next_content_hash = _compute_content_hash(q_data)
        if next_content_hash in used_content_hashes and not allow_duplicate_content:
            logger.warning(f"[ADAPTIVE_NEXT] Content-hash duplicate detected: {next_q.question_id} — skipping")
            if validation_pass == 0 and _promote_fallback("duplicate_content_hash"):
                continue
            _promote_emergency("duplicate_content_hash")
            continue

        if (
            _has_only_broken_widgets(q_data)
            or not _has_answer_space(q_data)
            or not _is_subject_scoped_question(q_data, subject)
        ):
            logger.info(f"[ADAPTIVE_NEXT] Skipping invalid next question {next_q.question_id}")
            if validation_pass == 0 and _promote_fallback("invalid_question_contract"):
                continue
            _promote_emergency("invalid_question_contract")
            continue

        # Patch widget fields before returning (prefetch/pool data may lack defaults)
        _patch_numeric_input_widgets(q_data)
        cleaned_next = _post_process_with_age_fallback(
            [q_data],
            subject,
            jwt_age if jwt_age else None,
            "assessment_next",
        )
        if cleaned_next:
            q_data = cleaned_next[0]
            next_content_hash = _compute_content_hash(q_data)
            break

        if validation_pass == 0 and _promote_fallback("post_process_empty"):
            continue
        _promote_emergency("post_process_empty")
        break

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
         "$set": {"current_difficulty": new_diff, "updated_at": datetime.now()},
         "$push": {"answers": answer_record, "used_question_ids": next_q.question_id,
                   "used_skill_ids": next_q.skill_ids[0] if next_q.skill_ids else "",
                   "used_content_hashes": next_content_hash}}
    )
    logger.info(f"[ADAPTIVE_NEXT] Served question {questions_asked}/{session.get('max_questions', 10)} for assessment {payload.assessment_id}")

    # Auto-chain: immediately start prefetching the NEXT question in background
    # so it's ready by the time the user answers this one.
    # Use < max_questions (not < max_questions - 1) so the final question also gets prefetched.
    if questions_asked < session.get("max_questions", 10):
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


def _learning_prefetch_worker(user_id: str, subject: str, exclude_question_ids: list, jwt_age: int):
    """Background worker that pre-generates the next learning-path question and caches it."""
    try:
        ensure_dash_system()
        from managers.mongodb_manager import mongo_db as _mongo

        active_subject = (subject or dash_system.subject or "").strip().title()
        if active_subject:
            _switch_subject_if_needed(active_subject, "US")
        cache_key = f"{user_id}:{active_subject.lower()}" if active_subject else user_id

        # Skip if we already have a cached question for this user+subject
        with _learning_prefetch_lock:
            if cache_key in _learning_prefetch_cache:
                logger.info(f"[LEARNING_PREFETCH] Already cached for {cache_key}, skipping")
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

        if active_subject and not _is_subject_scoped_question(q_data, active_subject):
            logger.info(f"[LEARNING_PREFETCH] Dropping cross-subject cache candidate {q.question_id} for {active_subject}")
            return

        with _learning_prefetch_lock:
            _learning_prefetch_cache[cache_key] = {
                "q_data": q_data,
                "question_id": q.question_id,
                "skill_id": q.skill_ids[0] if q.skill_ids else "",
                "subject": active_subject,
                "ts": time.time(),
            }
        logger.info(f"[LEARNING_PREFETCH] Cached question {q.question_id} for {cache_key}")

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
    selected_subject, selected_region = _get_user_subject_selection(user_id)
    active_subject = (selected_subject or dash_system.subject or "").strip().title()
    if active_subject:
        _switch_subject_if_needed(active_subject, selected_region or "US")

    exclude_ids = list(payload.current_question_ids)

    def _do_learning_prefetch():
        _learning_prefetch_worker(user_id, active_subject, exclude_ids, jwt_age)

    threading.Thread(target=_do_learning_prefetch, daemon=True).start()
    return {"status": "prefetching"}


def _trigger_learning_prefetch(user_id: str, subject: str, served_question_ids: list, jwt_age: int):
    """Fire-and-forget helper to trigger learning path prefetch after serving questions."""
    def _do():
        _learning_prefetch_worker(user_id, subject, served_question_ids, jwt_age)
    threading.Thread(target=_do, daemon=True).start()


def _compute_content_hash(q_data: dict) -> str:
    """Compute semantic content hash used by serving-pipeline dedupe.

    This intentionally mirrors the strict pretest fingerprint behavior:
    - strip Perseus widget markers from content
    - normalize whitespace/casing
    - include answerArea shape
    """
    content = str((q_data.get("question", {}) or {}).get("content", ""))
    content = re.sub(r"\[\[☃[^\]]+\]\]", " ", content)
    content = re.sub(r"\s+", " ", content).strip().lower()
    answer_str = json.dumps(q_data.get("answerArea", {}), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(f"{content}|{answer_str}".encode("utf-8")).hexdigest()


_SUBJECT_ALIAS = {
    "science": {"science", "biology", "chemistry", "physics", "earth", "astronomy"},
    "math": {"math", "algebra", "geometry", "arithmetic", "calculus", "statistics"},
    "english": {"english", "ela", "language", "grammar", "reading", "writing", "literature"},
    "history": {"history", "civilization", "historical"},
    "geography": {"geography", "map", "geology"},
}


def _normalize_subject_token(subject: Optional[str]) -> str:
    if not subject:
        return ""
    return subject.strip().lower().replace("_", " ").replace("-", " ")


def _match_alias(text: str, alias: str) -> bool:
    token = str(alias or "").strip().lower()
    if not token:
        return False
    escaped = re.escape(token)
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None


def _aliases_for_subject(normalized_subject: str) -> set:
    if normalized_subject in _SUBJECT_ALIAS:
        return set(_SUBJECT_ALIAS[normalized_subject])
    for aliases in _SUBJECT_ALIAS.values():
        if normalized_subject in aliases:
            return set(aliases)
    return {normalized_subject}


def _subject_families_for_token(normalized_subject: str) -> set:
    families = set()
    for family, aliases in _SUBJECT_ALIAS.items():
        if normalized_subject == family or normalized_subject in aliases:
            families.add(family)
    return families or {normalized_subject}


def _matched_subject_families(text_blob: str) -> set:
    hits = set()
    for family, aliases in _SUBJECT_ALIAS.items():
        if any(_match_alias(text_blob, alias) for alias in aliases):
            hits.add(family)
    return hits


def _is_subject_scoped_question(perseus: dict, subject: Optional[str]) -> bool:
    """Guard against cross-subject contamination in served questions."""
    normalized_subject = _normalize_subject_token(subject)
    if not normalized_subject:
        return True

    aliases = {a.lower() for a in _aliases_for_subject(normalized_subject)}
    expected_families = _subject_families_for_token(normalized_subject)

    dm = perseus.get("dash_metadata", {}) if isinstance(perseus, dict) else {}
    skill_ids = dm.get("skill_ids", []) if isinstance(dm, dict) else []
    skill_names = dm.get("skill_names", []) if isinstance(dm, dict) else []
    unit_name = dm.get("unit_name", "") if isinstance(dm, dict) else ""
    lesson_name = dm.get("lesson_name", "") if isinstance(dm, dict) else ""
    dm_subject = dm.get("subject", "") if isinstance(dm, dict) else ""
    parts = []
    if isinstance(skill_ids, list):
        parts.extend(str(s).lower() for s in skill_ids if s)
    if isinstance(skill_names, list):
        parts.extend(str(s).lower() for s in skill_names if s)
    if unit_name:
        parts.append(str(unit_name).lower())
    if lesson_name:
        parts.append(str(lesson_name).lower())
    if dm_subject:
        parts.append(str(dm_subject).lower())
    skill_blob = " ".join(parts)
    if skill_blob:
        # Reject only if metadata explicitly points to a different subject family.
        hit_families = _matched_subject_families(skill_blob)
        if hit_families:
            if hit_families & expected_families:
                return True
            return False
        # Sparse/neutral metadata should not be rejected.
        return True

    # Fallback to question content when skill metadata is sparse
    content = str(((perseus.get("question") or {}).get("content") or "")).lower()
    if not content.strip():
        return True

    # Keep hard mismatch guard for the most error-prone pair.
    forbidden = {
        "science": {"math"},
        "math": {"science"},
    }.get(normalized_subject, set())
    if any(_match_alias(content, f) for f in forbidden):
        return False

    if any(_match_alias(content, a) for a in aliases):
        return True
    return True


def _is_age_scoped_question(perseus: dict, age: Optional[int]) -> bool:
    """Reject only explicit age/grade mismatches from metadata."""
    if not isinstance(age, int):
        return True
    dm = perseus.get("dash_metadata", {}) if isinstance(perseus, dict) else {}
    skill_ids = dm.get("skill_ids", []) if isinstance(dm, dict) else []
    skill_names = dm.get("skill_names", []) if isinstance(dm, dict) else []
    unit_name = dm.get("unit_name", "") if isinstance(dm, dict) else ""
    lesson_name = dm.get("lesson_name", "") if isinstance(dm, dict) else ""
    parts = []
    if isinstance(skill_ids, list):
        parts.extend(str(s).lower() for s in skill_ids if s)
    if isinstance(skill_names, list):
        parts.extend(str(s).lower() for s in skill_names if s)
    if unit_name:
        parts.append(str(unit_name).lower())
    if lesson_name:
        parts.append(str(lesson_name).lower())
    skill_blob = " ".join(parts)
    if not skill_blob:
        return True

    normalized_blob = re.sub(r"[_\-]+", " ", skill_blob)
    hinted_grades = set()
    hinted_ranges: List[tuple[int, int]] = []
    hinted_bands = set()

    if re.search(r"\bkindergarten\b", normalized_blob) or re.search(r"\bgrade\s*k\b", normalized_blob):
        hinted_grades.add(0)
    for match in re.findall(r"\bgrade\s*(\d{1,2})\b", normalized_blob):
        g = int(match)
        if 0 <= g <= 12:
            hinted_grades.add(g)
    for match in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)\s*grade\b", normalized_blob):
        g = int(match)
        if 0 <= g <= 12:
            hinted_grades.add(g)
    for lo_s, hi_s in re.findall(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:to|-)\s*(\d{1,2})(?:st|nd|rd|th)?\s*grade\b",
        normalized_blob,
    ):
        lo = int(lo_s)
        hi = int(hi_s)
        if 0 <= lo <= 12 and 0 <= hi <= 12:
            hinted_ranges.append((min(lo, hi), max(lo, hi)))
    for lo_s, hi_s in re.findall(r"\bgrade\s*(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\b", normalized_blob):
        lo = int(lo_s)
        hi = int(hi_s)
        if 0 <= lo <= 12 and 0 <= hi <= 12:
            hinted_ranges.append((min(lo, hi), max(lo, hi)))

    if re.search(r"\belementary\b", normalized_blob):
        hinted_bands.add("elementary")
    if re.search(r"\bmiddle\s*school\b|\bjunior\s*high\b", normalized_blob):
        hinted_bands.add("middle")
    if re.search(r"\bhigh\s*school\b", normalized_blob):
        hinted_bands.add("high")
    if re.search(r"\bprecalculus\b|\bcalculus\b|\bap\s", normalized_blob):
        hinted_bands.add("high")

    # If no explicit age signal is present, do not reject.
    if not hinted_grades and not hinted_ranges and not hinted_bands:
        return True

    expected_grade = max(0, min(12, age - 5))
    for lo, hi in hinted_ranges:
        if lo - 1 <= expected_grade <= hi + 1:
            return True

    # Allow small drift for imperfect metadata labels.
    if hinted_grades and any(abs(g - expected_grade) <= 2 for g in hinted_grades):
        return True

    band_ranges = {
        "elementary": (0, 5),
        "middle": (6, 8),
        "high": (9, 12),
    }
    for band in hinted_bands:
        lo, hi = band_ranges[band]
        if lo - 1 <= expected_grade <= hi + 1:
            return True

    return False


def _has_answer_space(perseus: dict) -> bool:
    """Ensure frontend has an answer area + at least one scoreable widget."""
    if not isinstance(perseus, dict):
        return False
    answer_area = perseus.get("answerArea")
    if not isinstance(answer_area, dict):
        return False
    answer_type = answer_area.get("type")
    if not isinstance(answer_type, str) or not answer_type.strip():
        return False

    widgets = ((perseus.get("question") or {}).get("widgets") or {})
    if not isinstance(widgets, dict) or not widgets:
        return False

    for w in widgets.values():
        if not isinstance(w, dict):
            continue
        wtype = w.get("type")
        if isinstance(wtype, str) and wtype not in {"image", "definition"}:
            return True
    return False


def _post_process_pipeline_items(
    perseus_items: List[Dict],
    subject: Optional[str],
    age: Optional[int] = None,
) -> List[Dict]:
    """Final safety gate before returning questions to frontend.

    Enforces:
    - render contract patching
    - no broken-widget-only payloads
    - answer-space presence
    - subject scoping
    - duplicate question/content removal
    """
    seen_ids = set()
    seen_hashes = set()
    cleaned: List[Dict] = []

    for item in perseus_items:
        if not isinstance(item, dict):
            continue
        _patch_numeric_input_widgets(item)
        if _has_only_broken_widgets(item):
            continue
        if not _has_answer_space(item):
            continue
        if not _is_subject_scoped_question(item, subject):
            logger.warning("[CONTENT_PIPELINE] Rejected cross-subject question")
            continue
        if not _is_age_scoped_question(item, age):
            logger.warning("[CONTENT_PIPELINE] Rejected age-mismatched question")
            continue

        dm = item.get("dash_metadata", {}) if isinstance(item.get("dash_metadata"), dict) else {}
        qid = str(dm.get("dash_question_id") or "")
        if qid and qid in seen_ids:
            continue

        ch = _compute_content_hash(item)
        if ch in seen_hashes:
            continue

        if qid:
            seen_ids.add(qid)
        seen_hashes.add(ch)
        cleaned.append(_strip_objectids(item))

    return cleaned


def _post_process_with_age_fallback(
    perseus_items: List[Dict],
    subject: Optional[str],
    age: Optional[int],
    context: str,
    allow_age_relax: bool = True,
) -> List[Dict]:
    """Run strict post-process; relax only the age gate if it drops everything."""
    strict = _post_process_pipeline_items(perseus_items, subject, age)
    if strict or age is None:
        return strict
    if not allow_age_relax:
        logger.warning(
            f"[CONTENT_PIPELINE] {context}: strict age gate filtered all candidates; "
            "age-relax fallback disabled for this path"
        )
        return []
    relaxed = _post_process_pipeline_items(perseus_items, subject, None)
    if relaxed:
        logger.warning(
            f"[CONTENT_PIPELINE] {context}: strict age gate filtered all candidates; "
            f"serving {len(relaxed)} subject-scoped item(s)"
        )
    return relaxed


def _build_emergency_subject_question(
    subject: Optional[str],
    age: Optional[int] = None,
    current_grade: Optional[str] = None,
    question_number: int = 1,
    question_id_prefix: Optional[str] = None,
    difficulty: float = 0.5,
) -> Dict[str, Any]:
    """Construct a deterministic, render-safe, subject-scoped fallback question."""
    normalized_subject = (subject or "General").strip().title() or "General"

    age_value = None
    if isinstance(age, int):
        age_value = age
    else:
        try:
            age_value = int(age) if age is not None else None
        except (TypeError, ValueError):
            age_value = None

    if isinstance(current_grade, str) and current_grade.strip():
        grade_code = current_grade.strip()
    elif age_value is not None:
        if age_value <= 5:
            grade_code = "K"
        elif age_value >= 18:
            grade_code = "GRADE_12"
        else:
            grade_code = f"GRADE_{age_value - 5}"
    else:
        grade_code = "K"

    grade_label = "Kindergarten" if grade_code == "K" else grade_code.replace("GRADE_", "Grade ")
    subject_slug = re.sub(r"[^a-z0-9]+", "_", normalized_subject.lower()).strip("_") or "general"
    grade_slug = re.sub(r"[^a-z0-9]+", "_", grade_code.lower()).strip("_") or "k"

    if question_id_prefix:
        question_id = f"{question_id_prefix}_{question_number}_{int(time.time() * 1000) % 100000}"
    else:
        question_id = f"emg_{subject_slug}_{grade_slug}_{question_number}_{int(time.time() * 1000) % 100000}"
    skill_id = f"{subject_slug}_emergency_{grade_slug}"

    item = {
        "question": {
            "content": (
                f"In {normalized_subject}, which statement best matches a {grade_label} concept? "
                "[[\u2603 radio 1]]"
            ),
            "images": {},
            "widgets": {
                "radio 1": {
                    "type": "radio",
                    "graded": True,
                    "version": {"major": 1, "minor": 0},
                    "options": {
                        "choices": [
                            {"content": f"It aligns with core {normalized_subject.lower()} ideas taught in {grade_label}.", "correct": True},
                            {"content": "It is unrelated to the current subject focus.", "correct": False},
                            {"content": "It only applies to an advanced unrelated course.", "correct": False},
                            {"content": "It cannot be determined from this lesson context.", "correct": False},
                        ],
                        "multipleSelect": False,
                        "randomize": False,
                        "deselectEnabled": False,
                        "displayCount": None,
                        "hasNoneOfTheAbove": False,
                        "countChoices": False,
                    },
                }
            },
        },
        "answerArea": {
            "type": "multiple",
            "calculator": False,
            "chi2Table": False,
            "periodicTable": False,
            "tTable": False,
            "zTable": False,
        },
        "hints": [
            {"content": f"Focus on the main topic: {normalized_subject}."},
            {"content": f"Pick the choice that matches {grade_label} expectations."},
            {"content": "Choose the option that is directly relevant to this lesson context."},
        ],
        "itemDataVersion": {"major": 0, "minor": 1},
        "dash_metadata": {
            "dash_question_id": question_id,
            "source_question_id": question_id,
            "skill_ids": [skill_id],
            "difficulty": difficulty,
            "expected_time_seconds": 60.0,
            "slug": question_id,
            "skill_names": [f"{normalized_subject} Foundations ({grade_label})"],
            "unit_id": skill_id,
            "lesson_id": skill_id,
            "exercise_id": "emergency_local",
            "mongodb_id": question_id,
            "unit_name": f"{normalized_subject} Foundations {grade_label}",
            "lesson_name": "Core Practice",
            "exercise_name": "Emergency Practice",
            "ai_generated": True,
            "source": "emergency_local",
            "subject": normalized_subject,
        },
    }
    return _strip_objectids(item)


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
        if pool_col is not None:
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
                        from services.DashSystem.pre_serve_validator import validate_pre_serve
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
            from services.DashSystem.pre_serve_validator import validate_pre_serve
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


def _strip_wrapping_quotes(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if len(text) >= 2:
        first = text[0]
        last = text[-1]
        if (first == '"' and last == '"') or (first == "'" and last == "'"):
            return text[1:-1].strip()
    return text


def _sanitize_choice_list(raw_choices: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_choices, list):
        return []

    cleaned: List[Dict[str, Any]] = []
    for i, choice in enumerate(raw_choices):
        if isinstance(choice, str):
            cleaned.append(
                {
                    "id": f"choice-{i}",
                    "content": _strip_wrapping_quotes(choice),
                    "correct": False,
                }
            )
            continue

        if isinstance(choice, dict):
            normalized = dict(choice)
            cid = normalized.get("id")
            if not isinstance(cid, str) or not cid.strip():
                cid = f"choice-{i}"
            normalized["id"] = cid.strip()
            normalized["content"] = _strip_wrapping_quotes(normalized.get("content", ""))
            normalized["correct"] = bool(normalized.get("correct", False))
            cleaned.append(normalized)
            continue

        cleaned.append(
            {
                "id": f"choice-{i}",
                "content": _strip_wrapping_quotes(choice),
                "correct": False,
            }
        )

    return cleaned


def _strip_duplicate_radio_instruction(content: str) -> str:
    stripped = re.sub(
        r"^\s*choose\s+(?:\d+|one)\s+answers?:\s*$",
        "",
        content,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    stripped = re.sub(r"\n{3,}", "\n\n", stripped)
    return stripped.strip()


def _patch_numeric_input_widgets(perseus: dict) -> None:
    """Patch missing required fields on all widget types and validate answer presence."""
    widgets = perseus.get("question", {}).get("widgets", {})
    has_radio_widget = False
    for wkey, wval in widgets.items():
        if not isinstance(wval, dict):
            continue
        wtype = wval.get("type")
        raw_opts = wval.get("options")
        opts = raw_opts if isinstance(raw_opts, dict) else {}
        if not isinstance(raw_opts, dict):
            wval["options"] = opts
        if wtype == "radio":
            has_radio_widget = True
            if isinstance(raw_opts, list):
                opts["choices"] = _sanitize_choice_list(raw_opts)
            else:
                opts["choices"] = _sanitize_choice_list(opts.get("choices", []))
            opts.setdefault("multipleSelect", bool(wval.get("multipleSelect", False)))
            opts.setdefault("randomize", bool(wval.get("randomize", False)))
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
            opts["choices"] = _sanitize_choice_list(opts.get("choices", []))
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
        if has_radio_widget and isinstance(q.get("content"), str):
            q["content"] = _strip_duplicate_radio_instruction(q["content"])


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

    admin_user_id = require_admin(request)

    logger.info(f"[VIDEO_APPROVAL] Admin {admin_user_id} approving video {video_id} for question {question_id}")

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

    admin_user_id = require_admin(request)

    logger.info(f"[VIDEO_REJECTION] Admin {admin_user_id} rejecting video {video_id} for question {question_id}")

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
    """
    Pre-generate Q1 in background and cache it so start-adaptive is instant.
    Pool warmup on startup handles broader skill coverage (10+ skills per subject).
    """
    cache_key = f"{user_id}:{subject.lower()}"

    # Create an Event so start-adaptive can wait for this warm-start
    evt = threading.Event()
    with _warmstart_lock:
        # Skip if already cached and fresh
        if cache_key in _warmstart_cache:
            cached = _warmstart_cache[cache_key]
            if time.time() - cached.get("ts", 0) < WARMSTART_TTL:
                logger.info(f"[WARMSTART] Already cached for {cache_key}")
                evt.set()
                return
        _warmstart_events[cache_key] = evt

    def _bg():
        try:
            ensure_dash_system()
            from managers.mongodb_manager import mongo_db as _mongo

            if not dash_system:
                return

            # Pin DASH singleton to requested subject before any generation.
            _switch_subject_if_needed(subject, region)
            profile = dash_system.load_user_or_create(user_id)
            grade = profile.current_grade
            age = profile.age or 10
            grade_name = grade.replace("GRADE_", "Grade ").replace("K", "Kindergarten")

            q = None
            if dash_system.use_ai_questions and dash_system.ai_provider:
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

            # Fallback to DASH picker only if direct warm JIT failed.
            if not q:
                current_time = time.time()
                q = dash_system.get_next_question_flexible(
                    user_id,
                    current_time,
                    user_profile=profile,
                    fast_mode=True,
                    force_grade_range=True,
                )

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
    _persist_user_subject_selection(user_id, subject, region)

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
    require_admin(request)
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
async def get_pool_stats(skill_id: str, request: Request):
    """Get pool statistics for a skill."""
    require_admin(request)
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
