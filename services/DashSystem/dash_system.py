import math
import time
import json
import os
import sys
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from managers.user_manager import UserManager, UserProfile, SkillState
from services.DashSystem.khan_models import (
    KhanSkill, KhanSubSkill, GradeLevel as KhanGradeLevel,
    derive_grade_from_course, extract_subject
)

from shared.logging_config import get_logger

logger = get_logger(__name__)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s|%(message)s|file:%(filename)s:line No.%(lineno)d',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    FAST_MODE_SKILL_SCAN_LIMIT = max(1, int(os.getenv("DASH_FAST_SKILL_SCAN_LIMIT", "8")))
except (TypeError, ValueError):
    FAST_MODE_SKILL_SCAN_LIMIT = 8

# Helper function for backward compatibility
def log_print(message: str):
    """Wrapper for logger.info for easier migration"""
    logger.info(message)

class GradeLevel(Enum):
    K = 0
    GRADE_1 = 1
    GRADE_2 = 2
    GRADE_3 = 3
    GRADE_4 = 4
    GRADE_5 = 5
    GRADE_6 = 6
    GRADE_7 = 7
    GRADE_8 = 8
    GRADE_9 = 9
    GRADE_10 = 10
    GRADE_11 = 11
    GRADE_12 = 12

def parse_grade_level(grade_value, default=None):
    """Parse various grade formats into a GradeLevel enum.

    Handles: "GRADE_8", "K", "Grade 8", "grade 8", 3, "3", None
    Returns default (GradeLevel.K) if parsing fails.
    """
    if default is None:
        default = GradeLevel.K
    if grade_value is None:
        return default
    # Integer
    if isinstance(grade_value, int):
        try:
            return GradeLevel(grade_value)
        except ValueError:
            return default
    # String
    s = str(grade_value).strip()
    # Try direct enum key: "GRADE_8", "K"
    try:
        return GradeLevel[s]
    except KeyError:
        pass
    # Try "Grade 8" / "grade 8" format
    import re
    m = re.match(r'(?i)grade\s+(\d+)', s)
    if m:
        try:
            return GradeLevel(int(m.group(1)))
        except ValueError:
            return default
    # Try bare number string: "8"
    if s.isdigit():
        try:
            return GradeLevel(int(s))
        except ValueError:
            return default
    # "k" or "K"
    if s.upper() == 'K':
        return GradeLevel.K
    return default

class MasteryLevel(Enum):
    """Five-tier mastery system matching Khan Academy's proficiency model."""
    ATTEMPTED = 1      # 0.0 - 0.3: Student has tried but struggles
    FAMILIAR = 2       # 0.3 - 0.5: Recognizes concepts, inconsistent success
    PROFICIENT = 3     # 0.5 - 0.7: Getting most right, still needs practice
    MASTERED = 4       # 0.7 - 0.85: Solid understanding, occasional errors
    EXPERT = 5         # 0.85 - 1.0: Consistent accuracy, ready to advance

MASTERY_THRESHOLDS = [
    (0.0, 0.3, MasteryLevel.ATTEMPTED),
    (0.3, 0.5, MasteryLevel.FAMILIAR),
    (0.5, 0.7, MasteryLevel.PROFICIENT),
    (0.7, 0.85, MasteryLevel.MASTERED),
    (0.85, 1.01, MasteryLevel.EXPERT),  # 1.01 to handle floating point
]

def mastery_level_from_probability(probability: float) -> MasteryLevel:
    """Pure function: map probability 0-1 to MasteryLevel."""
    for lo, hi, level in MASTERY_THRESHOLDS:
        if lo <= probability < hi:
            return level
    return MasteryLevel.EXPERT  # Fallback for probability >= 1.0

# ---------------------------------------------------------------------------
# Concept-type forgetting rates (higher = faster decay)
# Based on cognitive science: procedural memory decays differently than
# declarative (vocabulary) or automaticity (math facts).
# ---------------------------------------------------------------------------
CONCEPT_FORGETTING_RATES = {
    "math_fact": 0.15,        # Arithmetic, times tables — fast recall, fast decay
    "vocabulary": 0.13,       # Definitions, terms — moderate decay
    "procedural": 0.10,       # Algorithms, procedures — standard (default)
    "conceptual": 0.07,       # Deep understanding, proofs — slow decay
    "problem_solving": 0.06,  # Multi-step reasoning — slowest decay
}

_CONCEPT_TYPE_KEYWORDS = {
    "math_fact": [
        "addition", "subtraction", "multiplication", "division", "arithmetic",
        "times table", "counting", "place value", "basic fact", "number fact",
    ],
    "vocabulary": [
        "vocabulary", "definition", "term", "word meaning", "spelling",
        "grammar", "phonics", "parts of speech", "literary term", "prefix",
        "suffix", "synonym", "antonym",
    ],
    "problem_solving": [
        "problem solving", "word problem", "proof", "derive", "design",
        "analyze", "synthesis", "critical thinking", "application",
        "multi-step", "real-world",
    ],
    "conceptual": [
        "concept", "theory", "principle", "law", "theorem", "understanding",
        "explain", "relationship", "why", "reasoning",
    ],
}

def detect_forgetting_rate(skill_name: str) -> float:
    """Detect appropriate forgetting rate based on skill name keywords.

    Returns a concept-type-specific decay rate. Falls back to 'procedural' (0.10).
    """
    lower = skill_name.lower()
    for concept_type, keywords in _CONCEPT_TYPE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return CONCEPT_FORGETTING_RATES[concept_type]
    return CONCEPT_FORGETTING_RATES["procedural"]

@dataclass
class Skill:
    skill_id: str
    name: str
    grade_level: GradeLevel
    prerequisites: List[str] = field(default_factory=list)
    forgetting_rate: float = 0.1
    difficulty: float = 0.0
    order: int = 0  # Order within grade level for learning journey

@dataclass
class StudentSkillState:
    memory_strength: float = 0.0
    last_practice_time: Optional[float] = None
    practice_count: int = 0
    correct_count: int = 0

@dataclass
class Question:
    question_id: str
    skill_ids: List[str]
    content: str
    difficulty: float = 0.0
    expected_time_seconds: float = 60.0  # Default expected time for answering
    perseus_data: Optional[Dict[str, Any]] = None  # Pre-loaded Perseus JSON (from content pool)

class DASHSystem:
    def __init__(self, skills_file: Optional[str] = None, curriculum_file: Optional[str] = None, use_mongodb: bool = True,
                 use_khan_hierarchy: bool = True, region: str = "US", subject: str = "Math",
                 use_ai_questions: Optional[bool] = None, content_engine=None):

        # Default file paths relative to the project root
        self.skills_file_path = skills_file if skills_file else "QuestionsBank/skills.json"
        self.curriculum_file_path = curriculum_file if curriculum_file else "QuestionsBank/curriculum.json"
        self.use_mongodb = use_mongodb
        self.use_khan_hierarchy = use_khan_hierarchy
        self.region = region
        self.subject = subject

        # AI question generation flag (env var or constructor arg)
        if use_ai_questions is not None:
            self.use_ai_questions = use_ai_questions
        else:
            self.use_ai_questions = os.getenv("USE_AI_QUESTIONS", "false").lower() in ("true", "1", "yes")

        self.skills: Dict[str, Skill] = {}
        self.khan_skills: Dict[str, KhanSkill] = {}  # New: Khan Academy units as skills
        self.khan_sub_skills: Dict[str, KhanSubSkill] = {}  # New: Khan Academy lessons as sub-skills
        self.student_states: Dict[str, Dict[str, StudentSkillState]] = {}
        # Lightweight index structures for efficient question loading
        self.question_index: Dict[str, str] = {}  # Maps question_id → skill_id
        self.skill_question_index: Dict[str, List[str]] = {}  # Maps skill_id → [question_ids]
        self.question_cache: Dict[str, Question] = {}  # LRU cache for created Question objects
        self._cache_max_size = 10000  # LRU cache limit
        # Cache statistics for monitoring
        self._cache_hits = 0
        self._cache_misses = 0
        # Keep questions dict for backward compatibility (will be populated on-demand)
        self.questions: Dict[str, Question] = {}  # Deprecated: use _get_or_create_question() instead
        self.curriculum: Dict = {}
        self.user_manager = UserManager(users_folder="Users")

        # AI Question Provider (initialized after MongoDB)
        self.ai_provider = None

        # ContentGenerationService for pool-based question serving
        self.content_service = None
        self._pool_check_counter = 0  # For proactive pool refill (check every 5th pop)

        # Initialize MongoDB manager if using MongoDB
        self.mongo = None
        if use_mongodb:
            try:
                from managers.mongodb_manager import mongo_db
                self.mongo = mongo_db
                log_print("[MONGODB] MongoDB manager initialized")
            except Exception as e:
                log_print(f"[ERROR] Could not initialize MongoDB: {e}")
                raise RuntimeError(f"MongoDB initialization failed: {e}. Please configure MONGODB_URI in .env file.")

        # Load skills and questions from MongoDB
        if self.use_mongodb and self.mongo:
            if self.use_khan_hierarchy:
                log_print(f"[KHAN] Loading Khan Academy hierarchy for {region} - {subject}")
                self._load_from_khan_hierarchy()
            else:
                log_print("[LEGACY] Loading from generated_skills collection")
                self._load_from_mongodb()
        else:
            raise RuntimeError("MongoDB is required. Please configure MONGODB_URI in .env file.")

        # Initialize AI Question Provider after skills are loaded
        if self.use_ai_questions and self.mongo:
            try:
                from services.DashSystem.ai_question_provider import AIQuestionProvider
                if content_engine is None:
                    from services.DashSystem.content_v1 import ContentV1Engine
                    content_engine = ContentV1Engine()
                self.ai_provider = AIQuestionProvider(content_engine, self.mongo)
                log_print(f"[AI_QUESTIONS] AI question provider initialized (skills: {len(self.skills)})")
            except Exception as e:
                log_print(f"[AI_QUESTIONS] Failed to initialize AI provider: {e}. Falling back to Khan question bank.")
                self.use_ai_questions = False

        # Ensure adaptive difficulty history collection has proper indexes
        if self.use_mongodb and self.mongo:
            self._ensure_difficulty_history_index()
    
    def reload_curriculum(self):
        """Reload skills from MongoDB after new curriculum is generated.

        Builds new data structures in temporary dicts, then swaps references
        atomically so concurrent readers never see an empty/partial state.
        Call this after CurriculumGenerator finishes so DASH picks up
        the newly created courses/units/lessons without a server restart.
        """
        # Save current references so we can build new ones without
        # disturbing concurrent readers.
        prev_skills = self.skills
        prev_khan = self.khan_skills
        prev_sub = self.khan_sub_skills
        prev_qi = self.question_index
        prev_sqi = self.skill_question_index

        # Build into fresh temporaries (NOT self.*) so _load_from_khan_hierarchy
        # populates them while readers still see old data.
        self.skills = {}
        self.khan_skills = {}
        self.khan_sub_skills = {}
        self.question_index = {}
        self.skill_question_index = {}

        try:
            self._load_from_khan_hierarchy()
        except Exception as e:
            # Rollback on failure — restore old data atomically
            self.skills = prev_skills
            self.khan_skills = prev_khan
            self.khan_sub_skills = prev_sub
            self.question_index = prev_qi
            self.skill_question_index = prev_sqi
            log_print(f"[RELOAD] Curriculum reload FAILED, rolled back: {e}")
            return

        # Success — new dicts are fully populated on self.* at this point.
        # Python attribute assignment is atomic (pointer swap), so readers
        # will see either old or new, never partial.
        self.question_cache.clear()
        log_print(f"[RELOAD] Curriculum reloaded: {len(self.skills)} skills")

    def set_content_service(self, service):
        """Set the ContentGenerationService for pool-based question serving."""
        self.content_service = service
        log_print(f"[CONTENT_SERVICE] ContentGenerationService {'attached' if service else 'detached'}")

    def _fire_and_forget_sync(self, fn, *args, **kwargs):
        """Run a synchronous function in a background daemon thread.

        Used for non-blocking pool warm-up (ensure_pool, on_skill_unlock).
        """
        import threading
        def _run():
            try:
                fn(*args, **kwargs)
            except Exception as e:
                log_print(f"[CONTENT_SERVICE] Background task failed: {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _load_from_khan_hierarchy(self):
        """
        Load skills from Khan Academy hierarchy (questions_db).
        Maps Units → Skills and Lessons → Sub-skills.
        OPTIMIZED: Uses batch queries with $in to avoid query storm.
        """
        try:
            log_print(f"[KHAN] Loading courses for region={self.region}, subject={self.subject}")

            # First, check for AI-generated curriculum (works on fresh DB)
            relevant_courses = list(self.mongo.courses.find({
                "region": self.region,
                "source": "ai_generated",
                "subject": self.subject,
            }).sort("order_in_region", 1))

            if relevant_courses:
                log_print(f"[KHAN] Found {len(relevant_courses)} AI-generated {self.subject} courses in {self.region}")
            else:
                # Fall back to Khan data (title heuristic)
                all_courses = list(self.mongo.courses.find({"region": self.region}).sort("order_in_region", 1))
                log_print(f"[KHAN] No AI-generated courses; checking {len(all_courses)} Khan courses in {self.region}")
                for course in all_courses:
                    course_subject = extract_subject(course['title'])
                    if course_subject == self.subject:
                        relevant_courses.append(course)
                log_print(f"[KHAN] Found {len(relevant_courses)} {self.subject} courses in {self.region}")

            if not relevant_courses:
                log_print(f"[WARNING] No {self.subject} courses found for region {self.region} (OK on fresh DB)")
                return

            # OPTIMIZATION: Batch load all units for all relevant courses at once
            course_ids = [course['course_id'] for course in relevant_courses]
            all_units = list(self.mongo.units.find({"course_id": {"$in": course_ids}}).sort("order_in_course", 1))
            log_print(f"[KHAN] Loaded {len(all_units)} units in batch")

            # Group units by course_id for prerequisite calculation
            units_by_course = {}
            for unit in all_units:
                course_id = unit['course_id']
                if course_id not in units_by_course:
                    units_by_course[course_id] = []
                units_by_course[course_id].append(unit)

            # OPTIMIZATION: Batch load all lessons for all units at once
            unit_ids = [unit['unit_id'] for unit in all_units]
            all_lessons = list(self.mongo.lessons.find({"unit_id": {"$in": unit_ids}}).sort("order_in_unit", 1))
            log_print(f"[KHAN] Loaded {len(all_lessons)} lessons in batch")

            # Group lessons by unit_id
            lessons_by_unit = {}
            for lesson in all_lessons:
                unit_id = lesson['unit_id']
                if unit_id not in lessons_by_unit:
                    lessons_by_unit[unit_id] = []
                lessons_by_unit[unit_id].append(lesson)

            # OPTIMIZATION: Batch load all exercises for all lessons at once
            lesson_ids = [lesson['lesson_id'] for lesson in all_lessons]
            all_exercises = list(self.mongo.exercises.find({"lesson_id": {"$in": lesson_ids}}))
            log_print(f"[KHAN] Loaded {len(all_exercises)} exercises in batch")

            # Group exercises by lesson_id
            exercises_by_lesson = {}
            for exercise in all_exercises:
                lesson_id = exercise['lesson_id']
                if lesson_id not in exercises_by_lesson:
                    exercises_by_lesson[lesson_id] = []
                exercises_by_lesson[lesson_id].append(exercise)

            # Now process all units and create skills
            total_units = 0
            total_lessons = 0
            total_exercises = 0

            for course in relevant_courses:
                course_id = course['course_id']
                course_title = course['title']
                base_grade_level = derive_grade_from_course(
                    course_title,
                    course['slug'],
                    course.get('order_in_region', 0),
                    min_grade=course.get('min_grade'),
                )

                # Get units for this course from pre-loaded data
                units = units_by_course.get(course_id, [])
                units_sorted = sorted(units, key=lambda u: u.get('order_in_course', 0))

                # For banded AI courses (e.g. grades 6-8), distribute units
                # evenly across the band so each grade gets skills
                min_g = course.get('min_grade')
                max_g = course.get('max_grade')
                grade_span = 1
                if min_g is not None and max_g is not None and max_g > min_g:
                    grade_span = max_g - min_g + 1

                for idx, unit in enumerate(units_sorted):
                    unit_id = unit['unit_id']

                    # Compute per-unit grade: spread across band
                    if grade_span > 1 and len(units_sorted) > 0:
                        offset = (idx * grade_span) // len(units_sorted)
                        g_val = min(min_g + offset, 12)
                        grade_level = list(GradeLevel)[g_val]
                    else:
                        grade_level = base_grade_level

                    # Get prerequisites (all previous units in the same course)
                    prerequisites = [
                        u['unit_id'] for u in units_sorted
                        if u.get('order_in_course', 0) < unit.get('order_in_course', 0)
                    ]

                    # Get lessons for this unit from pre-loaded data
                    lessons = lessons_by_unit.get(unit_id, [])
                    sub_skill_ids = [lesson['lesson_id'] for lesson in lessons]

                    # Create KhanSkill (Unit → Skill mapping)
                    skill_forgetting_rate = detect_forgetting_rate(unit['title'])

                    # Map grade level to difficulty (K=0.15, Grade 1=0.25, ..., Grade 12=0.95)
                    grade_value = grade_level.value
                    if grade_value == 0:  # Kindergarten
                        skill_difficulty = 0.15
                    else:
                        # Linear mapping: Grade 1=0.25, Grade 12=0.95
                        skill_difficulty = 0.25 + (grade_value - 1) * 0.058
                        skill_difficulty = min(0.95, skill_difficulty)  # Cap at 0.95

                    khan_skill = KhanSkill(
                        skill_id=unit_id,
                        name=unit['title'],
                        course_id=course_id,
                        region=self.region,
                        subject=self.subject,
                        grade_level=grade_level,
                        order_in_course=unit.get('order_in_course', 0),
                        prerequisites=prerequisites,
                        sub_skills=sub_skill_ids,
                        difficulty=skill_difficulty,
                        forgetting_rate=skill_forgetting_rate
                    )
                    self.khan_skills[unit_id] = khan_skill

                    # Also add to regular skills dict for backward compatibility
                    skill = Skill(
                        skill_id=unit_id,
                        name=unit['title'],
                        grade_level=grade_level,
                        prerequisites=prerequisites,
                        forgetting_rate=skill_forgetting_rate,
                        difficulty=skill_difficulty,
                        order=unit.get('order_in_course', 0)
                    )
                    self.skills[unit_id] = skill

                    # Create KhanSubSkills (Lesson → Sub-skill mapping)
                    for lesson in lessons:
                        lesson_id = lesson['lesson_id']

                        # Get exercises for this lesson from pre-loaded data
                        exercises = exercises_by_lesson.get(lesson_id, [])
                        exercise_ids = [ex['exercise_id'] for ex in exercises]

                        khan_sub_skill = KhanSubSkill(
                            sub_skill_id=lesson_id,
                            name=lesson['title'],
                            skill_id=unit_id,
                            course_id=course_id,
                            order_in_skill=lesson.get('order_in_unit', 0),
                            exercise_ids=exercise_ids,
                            difficulty=0.5
                        )
                        self.khan_sub_skills[lesson_id] = khan_sub_skill

                        total_lessons += 1
                        total_exercises += len(exercise_ids)

                    total_units += 1

            log_print(f"[KHAN] Loaded {total_units} units (skills) with {total_lessons} lessons (sub-skills)")
            log_print(f"[KHAN] Total exercises available: {total_exercises}")

            # Always build Khan question index as fallback (even when AI questions enabled)
            self._build_khan_question_index()

        except Exception as e:
            log_print(f"[ERROR] Error loading Khan hierarchy: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Failed to load Khan Academy hierarchy: {e}")
    
    def _build_khan_question_index(self):
        """
        Build question index from Khan Academy questions in questions_db.
        Maps questions to their parent units (skills) via exercise → lesson → unit chain.
        """
        try:
            log_print("[KHAN] Building question index from questions_db...")
            
            # Get all exercise IDs we're interested in (from our loaded sub-skills)
            all_exercise_ids = []
            for sub_skill in self.khan_sub_skills.values():
                all_exercise_ids.extend(sub_skill.exercise_ids)
            
            log_print(f"[KHAN] Looking for questions from {len(all_exercise_ids)} exercises")
            
            # Query questions from questions_db
            questions_cursor = self.mongo.questions.find(
                {"exercise_id": {"$in": all_exercise_ids}},
                {"question_id": 1, "exercise_id": 1, "lesson_id": 1, "unit_id": 1}
            ).batch_size(1000)
            
            # Build mapping: exercise_id → unit_id for fast lookup
            exercise_to_unit = {}
            for sub_skill in self.khan_sub_skills.values():
                for exercise_id in sub_skill.exercise_ids:
                    exercise_to_unit[exercise_id] = sub_skill.skill_id
            
            # Initialize index structures
            self.question_index.clear()
            self.skill_question_index.clear()
            
            question_count = 0
            for q_doc in questions_cursor:
                question_id = q_doc.get('question_id', '')
                exercise_id = q_doc.get('exercise_id', '')
                
                if not question_id or not exercise_id:
                    continue
                
                # Map question to its unit (skill)
                unit_id = q_doc.get('unit_id') or exercise_to_unit.get(exercise_id)
                
                if unit_id and unit_id in self.khan_skills:
                    # Build indexes
                    self.question_index[question_id] = unit_id
                    if unit_id not in self.skill_question_index:
                        self.skill_question_index[unit_id] = []
                    self.skill_question_index[unit_id].append(question_id)
                    question_count += 1
            
            log_print(f"[KHAN] Indexed {question_count} questions across {len(self.skill_question_index)} skills")
            
        except Exception as e:
            log_print(f"[ERROR] Error building Khan question index: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _load_from_mongodb(self):
        """Load skills and questions from MongoDB"""
        try:
            # Load skills from MongoDB (using generated_skills collection)
            skills_docs = list(self.mongo.generated_skills.find())
            for skill_doc in skills_docs:
                try:
                    skill = Skill(
                        skill_id=skill_doc['skill_id'],
                        name=skill_doc['name'],
                        grade_level=GradeLevel[skill_doc['grade_level']],
                        prerequisites=skill_doc['prerequisites'],
                        forgetting_rate=skill_doc['forgetting_rate'],
                        difficulty=skill_doc['difficulty'],
                        order=skill_doc.get('order', 0)
                    )
                    self.skills[skill.skill_id] = skill
                except KeyError as e:
                    log_print(f"[WARNING] Skipping skill {skill_doc.get('skill_id', 'unknown')}: missing field {e}")
            
            log_print(f"[MONGODB] Loaded {len(self.skills)} skills from MongoDB")
            
            # Get valid exerciseDirNames (skill_ids) from loaded skills for MongoDB-level filtering
            valid_skill_ids = list(self.skills.keys())
            log_print(f"[MONGODB] Filtering questions by {len(valid_skill_ids)} valid skills at database level...")
            
            # Load lightweight question index from scraped_questions collection
            # Filter at MongoDB level using $in operator to only get questions with valid skills
            # This reduces documents processed from ~38,158 to ~1,623 (23x reduction)
            log_print("[MONGODB] Loading question index from scraped_questions collection (lightweight projection with skill filter)...")
            questions_cursor = self.mongo.scraped_questions.find(
                {"exerciseDirName": {"$in": valid_skill_ids}},  # Filter at DB level using $in operator
                {"questionId": 1, "exerciseDirName": 1}  # Projection: only needed fields
            ).batch_size(1000)
            
            # Initialize index structures
            self.question_index.clear()
            self.skill_question_index.clear()
            
            question_count = 0
            processed_count = 0
            
            for q_doc in questions_cursor:
                question_count += 1
                if question_count % 1000 == 0:
                    log_print(f"[MONGODB] Processed {question_count} questions so far...")
                
                try:
                    # Extract questionId (includes fabricated prefix: e.g., "41.1.2.1.9_x338f5e1fbc6cafdf")
                    # Format: {course_idx}.{unit_idx}.{lesson_idx}.{exercise_idx}.{question_idx}_{item_id}
                    question_id = q_doc.get('questionId', '')
                    if not question_id:
                        continue
                    
                    # Extract exerciseDirName (maps to skill_id)
                    exercise_dir_name = q_doc.get('exerciseDirName', '')
                    if not exercise_dir_name:
                        log_print(f"[WARNING] Skipping question {question_id}: missing exerciseDirName")
                        continue
                    
                    # Note: Skill validation already done at MongoDB level via $in filter
                    # But double-check for safety (should always pass now)
                    if exercise_dir_name not in self.skills:
                        log_print(f"[WARNING] Question {question_id} has skill {exercise_dir_name} not in skills (unexpected after DB filter)")
                        continue
                    
                    # Build lightweight indexes
                    self.question_index[question_id] = exercise_dir_name
                    if exercise_dir_name not in self.skill_question_index:
                        self.skill_question_index[exercise_dir_name] = []
                    self.skill_question_index[exercise_dir_name].append(question_id)
                    processed_count += 1
                    
                except KeyError as e:
                    log_print(f"[WARNING] Skipping question {q_doc.get('questionId', 'unknown')}: missing field {e}")
                except Exception as e:
                    log_print(f"[WARNING] Skipping question {q_doc.get('questionId', 'unknown')}: error {e}")
            
            log_print(f"[MONGODB] Loaded {len(self.question_index)} questions into index (processed {processed_count} out of {question_count} total documents)")
            log_print(f"[MONGODB] Index covers {len(self.skill_question_index)} skills")
            
        except Exception as e:
            log_print(f"[ERROR] Error loading from MongoDB: {e}")
            raise RuntimeError(f"Failed to load data from MongoDB: {e}. Local fallback disabled.")
    
    def _get_or_create_question(self, question_id: str) -> Optional[Question]:
        """
        Get Question object from cache or create on-demand from index.
        This method implements lazy loading of Question objects for memory efficiency.
        
        Args:
            question_id: The question identifier
            
        Returns:
            Question object if found, None otherwise
        """
        # Check cache first (fast path)
        if question_id in self.question_cache:
            self._cache_hits += 1
            return self.question_cache[question_id]
        
        # Cache miss - will create new Question object
        self._cache_misses += 1
        
        # Check if question exists in index
        if question_id not in self.question_index:
            return None
        
        # Get skill_id from index
        skill_id = self.question_index[question_id]
        if skill_id not in self.skills:
            return None
        
        # Get difficulty from skill
        skill = self.skills[skill_id]
        difficulty = skill.difficulty
        
        # Create Question object on-demand
        question = Question(
            question_id=question_id,
            skill_ids=[skill_id],
            content="",  # Always empty, Perseus data loaded separately
            difficulty=difficulty,
            expected_time_seconds=60.0  # Default value
        )
        
        # Cache with LRU eviction (FIFO when cache is full)
        if len(self.question_cache) >= self._cache_max_size:
            # Remove oldest entry (FIFO eviction)
            oldest_key = next(iter(self.question_cache))
            del self.question_cache[oldest_key]
        
        self.question_cache[question_id] = question
        
        # Also update backward-compatible questions dict for existing code
        self.questions[question_id] = question
        
        # Log cache statistics periodically (every 100 misses)
        if self._cache_misses % 100 == 0:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
            log_print(f"[CACHE_STATS] Hits: {self._cache_hits}, Misses: {self._cache_misses}, Hit Rate: {hit_rate:.1f}%, Cache Size: {len(self.question_cache)}")
        
        return question
    
    def _load_from_files(self, skills_file: str, curriculum_file: str):
        """Load skills and curriculum from JSON files"""
        try:
            # Load skills
            with open(skills_file, 'r') as f:
                skills_data = json.load(f)
            
            # Track order within each grade level for learning journey
            grade_order_map = {}
            for skill_id, skill_data in skills_data.items():
                grade_level = GradeLevel[skill_data['grade_level']]
                # Use order from JSON if present, otherwise infer from position
                order = skill_data.get('order', 0)
                if order == 0:
                    # Infer order from position in file (for backward compatibility)
                    if grade_level not in grade_order_map:
                        grade_order_map[grade_level] = 0
                    grade_order_map[grade_level] += 1
                    order = grade_order_map[grade_level]
                
                skill = Skill(
                    skill_id=skill_data['skill_id'],
                    name=skill_data['name'],
                    grade_level=grade_level,
                    prerequisites=skill_data['prerequisites'],
                    forgetting_rate=skill_data['forgetting_rate'],
                    difficulty=skill_data['difficulty'],
                    order=order
                )
                self.skills[skill_id] = skill
            
            # Load curriculum and questions
            with open(curriculum_file, 'r') as f:
                self.curriculum = json.load(f)
            
            self.questions.clear()
            for grade_key, grade_data in self.curriculum['grades'].items():
                for skill_data in grade_data['skills']:
                    for question_data in skill_data['questions']:
                        question = Question(
                            question_id=question_data['question_id'],
                            skill_ids=[skill_data['skill_id']],
                            content=question_data['content'],
                            difficulty=question_data['difficulty'],
                            expected_time_seconds=question_data.get('expected_time_seconds', 60.0)
                        )
                        self.questions[question.question_id] = question
            
            log_print(f"[OK] Loaded {len(self.skills)} skills from JSON files")
            
        except FileNotFoundError as e:
            log_print(f"[ERROR] Error: Could not find file {e.filename}")
            log_print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
        except json.JSONDecodeError as e:
            log_print(f"[ERROR] Error: Invalid JSON format - {e}")
            log_print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
        except Exception as e:
            log_print(f"[ERROR] Unexpected error loading curriculum: {e}")
            log_print("[INFO] Falling back to hardcoded curriculum...")
            self._initialize_k12_math_curriculum_fallback()
    
    def _initialize_k12_math_curriculum_fallback(self):
        """Fallback: Initialize K-12 Math curriculum with hardcoded skills (original implementation)"""
        
        # Kindergarten skills (order: 1, 2, 3)
        self.skills["counting_1_10"] = Skill("counting_1_10", "Counting 1-10", GradeLevel.K, [], 0.05, 0.0, 1)
        self.skills["number_recognition"] = Skill("number_recognition", "Number Recognition", GradeLevel.K, [], 0.05, 0.0, 2)
        self.skills["basic_shapes"] = Skill("basic_shapes", "Basic Shapes", GradeLevel.K, [], 0.08, 0.0, 3)
        
        # Grade 1 skills (order: 1, 2, 3)
        self.skills["addition_basic"] = Skill("addition_basic", "Basic Addition", GradeLevel.GRADE_1, ["counting_1_10"], 0.07, 0.0, 1)
        self.skills["subtraction_basic"] = Skill("subtraction_basic", "Basic Subtraction", GradeLevel.GRADE_1, ["counting_1_10"], 0.07, 0.0, 2)
        self.skills["counting_100"] = Skill("counting_100", "Counting to 100", GradeLevel.GRADE_1, ["counting_1_10"], 0.06, 0.0, 3)
        
        # Grade 2 skills (order: 1, 2, 3)
        self.skills["addition_2digit"] = Skill("addition_2digit", "2-Digit Addition", GradeLevel.GRADE_2, ["addition_basic"], 0.08, 0.0, 1)
        self.skills["subtraction_2digit"] = Skill("subtraction_2digit", "2-Digit Subtraction", GradeLevel.GRADE_2, ["subtraction_basic"], 0.08, 0.0, 2)
        self.skills["multiplication_intro"] = Skill("multiplication_intro", "Introduction to Multiplication", GradeLevel.GRADE_2, ["addition_basic"], 0.09, 0.0, 3)
        
        # Grade 3 skills (order: 1, 2, 3)
        self.skills["multiplication_tables"] = Skill("multiplication_tables", "Multiplication Tables", GradeLevel.GRADE_3, ["multiplication_intro"], 0.08, 0.0, 1)
        self.skills["division_basic"] = Skill("division_basic", "Basic Division", GradeLevel.GRADE_3, ["multiplication_tables"], 0.09, 0.0, 2)
        self.skills["fractions_intro"] = Skill("fractions_intro", "Introduction to Fractions", GradeLevel.GRADE_3, ["division_basic"], 0.10, 0.0, 3)
        
        # Grade 4 skills (order: 1, 2)
        self.skills["fractions_operations"] = Skill("fractions_operations", "Fraction Operations", GradeLevel.GRADE_4, ["fractions_intro"], 0.11, 0.0, 1)
        self.skills["decimals_intro"] = Skill("decimals_intro", "Introduction to Decimals", GradeLevel.GRADE_4, ["fractions_intro"], 0.10, 0.0, 2)
        
        # Grade 5 skills (order: 1, 2)
        self.skills["decimals_operations"] = Skill("decimals_operations", "Decimal Operations", GradeLevel.GRADE_5, ["decimals_intro"], 0.10, 0.0, 1)
        self.skills["percentages"] = Skill("percentages", "Percentages", GradeLevel.GRADE_5, ["decimals_operations"], 0.11, 0.0, 2)
        
        # Grade 6 skills (order: 1, 2)
        self.skills["integers"] = Skill("integers", "Integers", GradeLevel.GRADE_6, ["subtraction_2digit"], 0.09, 0.0, 1)
        self.skills["ratios_proportions"] = Skill("ratios_proportions", "Ratios and Proportions", GradeLevel.GRADE_6, ["fractions_operations"], 0.12, 0.0, 2)
        
        # Grade 7 skills (order: 1, 2)
        self.skills["algebraic_expressions"] = Skill("algebraic_expressions", "Algebraic Expressions", GradeLevel.GRADE_7, ["integers"], 0.13, 0.0, 1)
        self.skills["linear_equations_1var"] = Skill("linear_equations_1var", "Linear Equations (1 Variable)", GradeLevel.GRADE_7, ["algebraic_expressions"], 0.14, 0.0, 2)
        
        # Grade 8 skills (order: 1, 2)
        self.skills["linear_equations_2var"] = Skill("linear_equations_2var", "Linear Equations (2 Variables)", GradeLevel.GRADE_8, ["linear_equations_1var"], 0.15, 0.0, 1)
        self.skills["quadratic_intro"] = Skill("quadratic_intro", "Introduction to Quadratics", GradeLevel.GRADE_8, ["linear_equations_1var"], 0.16, 0.0, 2)
        
        # Grade 9 skills (Algebra 1) (order: 1, 2)
        self.skills["quadratic_equations"] = Skill("quadratic_equations", "Quadratic Equations", GradeLevel.GRADE_9, ["quadratic_intro"], 0.15, 0.0, 1)
        self.skills["polynomial_operations"] = Skill("polynomial_operations", "Polynomial Operations", GradeLevel.GRADE_9, ["algebraic_expressions"], 0.14, 0.0, 2)
        
        # Grade 10 skills (Geometry) (order: 1, 2)
        self.skills["geometric_proofs"] = Skill("geometric_proofs", "Geometric Proofs", GradeLevel.GRADE_10, ["basic_shapes"], 0.17, 0.0, 1)
        self.skills["trigonometry_basic"] = Skill("trigonometry_basic", "Basic Trigonometry", GradeLevel.GRADE_10, ["geometric_proofs"], 0.16, 0.0, 2)
        
        # Grade 11 skills (Algebra 2) (order: 1, 2)
        self.skills["exponentials_logs"] = Skill("exponentials_logs", "Exponentials and Logarithms", GradeLevel.GRADE_11, ["polynomial_operations"], 0.18, 0.0, 1)
        self.skills["trigonometry_advanced"] = Skill("trigonometry_advanced", "Advanced Trigonometry", GradeLevel.GRADE_11, ["trigonometry_basic"], 0.17, 0.0, 2)
        
        # Grade 12 skills (Pre-Calculus/Calculus) (order: 1, 2)
        self.skills["limits"] = Skill("limits", "Limits", GradeLevel.GRADE_12, ["exponentials_logs"], 0.19, 0.0, 1)
        self.skills["derivatives"] = Skill("derivatives", "Derivatives", GradeLevel.GRADE_12, ["limits"], 0.20, 0.0, 2)
    
    def get_student_state(self, student_id: str, skill_id: str) -> StudentSkillState:
        """Get or create student state for a specific skill"""
        if student_id not in self.student_states:
            self.student_states[student_id] = {}
        
        if skill_id not in self.student_states[student_id]:
            self.student_states[student_id][skill_id] = StudentSkillState()
        
        return self.student_states[student_id][skill_id]
    
    def calculate_memory_strength(self, student_id: str, skill_id: str, current_time: float) -> float:
        """Calculate current memory strength with tiered decay.
        Expert skills (>= 0.85) decay at 5% of normal rate (20x slower).
        Mastered skills (>= 0.7) decay at 10% of normal rate (10x slower).
        All other skills decay at full rate.
        """
        state = self.get_student_state(student_id, skill_id)
        skill = self.skills.get(skill_id)
        if not skill:
            return state.memory_strength

        if state.last_practice_time is None:
            return state.memory_strength

        stored_strength = state.memory_strength

        # For negative strengths (struggling students), decay toward zero means
        # improvement without practice. Fix: only decay positive strengths multiplicatively;
        # for negative strengths, decay toward zero is correct (forgetting the struggle).
        # But we should NOT let negative decay make a student appear better — clamp.
        time_elapsed = current_time - state.last_practice_time

        # First pass: apply full decay to get decayed strength
        decay_factor_full = math.exp(-skill.forgetting_rate * time_elapsed)
        tentative = stored_strength * decay_factor_full

        # Now use the decayed probability to pick the tier (not pre-decay)
        logit = tentative - skill.difficulty
        probability = 1 / (1 + math.exp(-logit))

        # Tiered decay: mastered/expert skills decay much more slowly
        if probability >= 0.85:
            effective_rate = skill.forgetting_rate * 0.05   # Expert: 20x slower
        elif probability >= 0.7:
            effective_rate = skill.forgetting_rate * 0.1    # Mastered: 10x slower
        else:
            effective_rate = skill.forgetting_rate           # Full rate

        decay_factor = math.exp(-effective_rate * time_elapsed)
        decayed = stored_strength * decay_factor

        # For negative strengths, ensure decay doesn't make student appear BETTER
        if stored_strength < 0:
            decayed = min(decayed, stored_strength)

        return decayed
    
    def get_all_prerequisites(self, skill_id: str, _visited: set = None) -> List[str]:
        """Get all prerequisite skills recursively (with cycle protection)"""
        if _visited is None:
            _visited = set()
        if skill_id in _visited:
            return []
        _visited.add(skill_id)

        prerequisites: List[str] = []
        skill = self.skills.get(skill_id)
        if not skill:
            return prerequisites

        for prereq_id in skill.prerequisites:
            if prereq_id not in _visited:
                prerequisites.append(prereq_id)
                prerequisites.extend(self.get_all_prerequisites(prereq_id, _visited))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_prerequisites = []
        for prereq in prerequisites:
            if prereq not in seen:
                seen.add(prereq)
                unique_prerequisites.append(prereq)
        
        return unique_prerequisites
    
    def calculate_time_penalty(self, response_time_seconds: float) -> float:
        """Calculate time penalty multiplier for response time"""
        if response_time_seconds > 180:  # 3 minutes
            return 0.5
        return 1.0
    
    def predict_correctness(self, student_id: str, skill_id: str, current_time: float) -> float:
        """Predict probability of correct answer using sigmoid function"""
        memory_strength = self.calculate_memory_strength(student_id, skill_id, current_time)
        skill = self.skills.get(skill_id)
        if not skill:
            return 0.5  # Unknown skill — assume neutral probability

        # Sigmoid function: P(correct) = 1 / (1 + exp(-(memory_strength - difficulty)))
        logit = memory_strength - skill.difficulty
        return 1 / (1 + math.exp(-logit))
    
    def get_mastery_level(self, student_id: str, skill_id: str, current_time: float) -> Dict:
        """Calculate mastery level for a student on a specific skill."""
        probability = self.predict_correctness(student_id, skill_id, current_time)
        level = mastery_level_from_probability(probability)
        # Find next level threshold
        next_threshold = None
        for lo, hi, lvl in MASTERY_THRESHOLDS:
            if lvl.value == level.value + 1:
                next_threshold = lo
                break
        return {
            "level_name": level.name,
            "level_number": level.value,
            "probability": round(probability, 3),
            "is_prerequisite_met": level.value >= MasteryLevel.MASTERED.value,
            "next_level_threshold": next_threshold,
        }

    def update_student_state(self, student_id: str, skill_id: str, is_correct: bool, current_time: float, response_time_seconds: float = 0.0):
        """Update student state after practice"""
        state = self.get_student_state(student_id, skill_id)
        skill = self.skills.get(skill_id)
        skill_name = skill.name if skill else skill_id
        
        # Store previous values for logging
        prev_strength = state.memory_strength
        prev_practice_count = state.practice_count
        prev_correct_count = state.correct_count
        
        # Update practice counts
        state.practice_count += 1
        if is_correct:
            state.correct_count += 1
        
        # Update memory strength based on performance
        # IMPORTANT: Use stored memory_strength (not decayed) as base for updates
        # Decay is only applied when calculating current strength for display/selection
        stored_strength = state.memory_strength
        time_since_last = current_time - state.last_practice_time if state.last_practice_time else 0
        
        # Update memory strength based on performance
        if is_correct:
            # Base strength increment with diminishing returns
            strength_increment = 1.0 / (1 + 0.03 * state.correct_count)
            
            # Apply time penalty using separate function
            time_penalty = self.calculate_time_penalty(response_time_seconds)
            strength_increment *= time_penalty
            
            # Update stored strength (absolute value, not decayed)
            new_strength = min(5.0, stored_strength + strength_increment)
            state.memory_strength = new_strength
            
            # Compact memory update log
            strength_change = new_strength - prev_strength
            log_print(f"  |- {skill_name}: {prev_strength:.3f} -> {new_strength:.3f} ({strength_change:+.3f})")
        else:
            # Slight decrease for incorrect answers
            # Use stored strength (not decayed) as base; clamp at 0 not negative
            # to avoid inverted forgetting curves where decay makes student "better"
            new_strength = max(0.0, stored_strength - 0.2)
            state.memory_strength = new_strength
            
            # Compact memory update log
            strength_change = new_strength - prev_strength
            log_print(f"  |- {skill_name}: {prev_strength:.3f} -> {new_strength:.3f} ({strength_change:+.3f})")
        
        # Update last practice time
        state.last_practice_time = current_time
    
    def update_with_prerequisites(self, student_id: str, skill_ids: List[str], is_correct: bool, current_time: float, response_time_seconds: float = 0.0) -> List[str]:
        """Update student state including prerequisites on wrong answers"""
        all_affected_skills = []
        already_updated = set()  # Track what we've already touched

        for skill_id in skill_ids:
            # Always update the direct skill
            self.update_student_state(student_id, skill_id, is_correct, current_time, response_time_seconds)
            all_affected_skills.append(skill_id)
            already_updated.add(skill_id)

        # Penalize prerequisites only if incorrect, and only once per prereq
        if not is_correct:
            for skill_id in skill_ids:
                prerequisites = self.get_all_prerequisites(skill_id)
                for prereq_id in prerequisites:
                    if prereq_id in already_updated:
                        continue  # Already updated — don't double-penalize
                    already_updated.add(prereq_id)
                    # Apply penalty to prerequisite (but don't count as practice attempt)
                    # Use stored strength (not decayed) to avoid double-decay
                    state = self.get_student_state(student_id, prereq_id)
                    stored_strength = state.memory_strength

                    # Apply smaller penalty to prerequisites; clamp at 0 not negative
                    state.memory_strength = max(0.0, stored_strength - 0.1)
                    state.last_practice_time = current_time

                    all_affected_skills.append(prereq_id)

        # Remove duplicates while preserving order
        seen = set()
        unique_affected_skills = []
        for skill_id in all_affected_skills:
            if skill_id not in seen:
                seen.add(skill_id)
                unique_affected_skills.append(skill_id)

        return unique_affected_skills

    def check_prerequisites(
        self, student_id: str, skill_id: str, current_time: float, threshold: float = 0.6
    ) -> Dict:
        """
        Hard prerequisite check. Threshold 0.6 balances between over-blocking (0.7)
        and under-blocking (0.5) while ensuring reasonable readiness.
        Returns {met, missing, redirect_to}.
        """
        skill = self.skills.get(skill_id)
        if not skill:
            return {"met": True, "missing": [], "redirect_to": None}

        missing = []
        for prereq_id in skill.prerequisites:
            prereq_skill = self.skills.get(prereq_id)
            if not prereq_skill:
                continue
            prereq_prob = self.predict_correctness(student_id, prereq_id, current_time)
            if prereq_prob < threshold:
                level = mastery_level_from_probability(prereq_prob)
                missing.append({
                    "skill_id": prereq_id,
                    "skill_name": prereq_skill.name,
                    "current_probability": round(prereq_prob, 3),
                    "required_probability": threshold,
                    "mastery_level": level.name,
                })

        missing.sort(key=lambda x: x["current_probability"])
        redirect_to = missing[0]["skill_id"] if missing else None
        return {"met": len(missing) == 0, "missing": missing, "redirect_to": redirect_to}

    def _initialize_unattempted_prerequisites(self, user_profile: UserProfile):
        """
        Initialize unattempted previous-grade skills to meet 0.7 threshold.
        For existing users: sets memory_strength=1.0 for all unattempted skills from grades below student's current grade.
        This ensures students can access grade-appropriate content without being blocked by empty skill history.
        """
        try:
            current_grade = parse_grade_level(user_profile.current_grade)
        except KeyError:
            return  # Invalid grade, skip initialization
        
        current_grade_value = current_grade.value
        threshold = 0.7
        updated_count = 0
        
        # Find all skills from grades AT OR BELOW current grade (previous + current skills)
        for skill_id, skill in self.skills.items():
            # Only process skills from current grade or lower
            if skill.grade_level.value > current_grade_value:
                continue
            
            # Ensure skill exists in skill_states (add if missing)
            if skill_id not in user_profile.skill_states:
                user_profile.skill_states[skill_id] = SkillState(
                    memory_strength=0.0,
                    last_practice_time=None,
                    practice_count=0,
                    correct_count=0
                )
            
            skill_state = user_profile.skill_states[skill_id]
            
            # Only update unattempted skills (practice_count == 0)
            if skill_state.practice_count > 0:
                continue
            
            # Calculate current probability: P(correct) = 1 / (1 + exp(-(memory_strength - difficulty)))
            logit = skill_state.memory_strength - skill.difficulty
            probability = 1 / (1 + math.exp(-logit))
            
            # If below threshold, set memory_strength to 1.0 (gives probability >= 0.7)
            if probability < threshold:
                skill_state.memory_strength = 1.0
                updated_count += 1
        
        if updated_count > 0:
            log_print(f"[PREV_SKILLS_INIT] Initialized {updated_count} unattempted previous-grade skills for grade {user_profile.current_grade}")
            # Save updated profile
            self.user_manager.save_user(user_profile)
    
    def load_user_or_create(self, user_id: str, age: int = 5) -> UserProfile:
        """Load existing user or create new one with cold-start initialization"""
        all_skill_ids = list(self.skills.keys())
        user_profile = self.user_manager.get_or_create_user(
            user_id, 
            all_skill_ids,
            all_skills=self.skills,  # Pass skills for cold-start
            age=age
        )
        
        # Initialize unattempted prerequisites (safe to run for all users - only updates if needed)
        self._initialize_unattempted_prerequisites(user_profile)
        
        # Sync user profile with current student_states for backward compatibility
        self.student_states[user_id] = {}
        for skill_id, skill_state in user_profile.skill_states.items():
            self.student_states[user_id][skill_id] = StudentSkillState(
                memory_strength=skill_state.memory_strength,
                last_practice_time=skill_state.last_practice_time,
                practice_count=skill_state.practice_count,
                correct_count=skill_state.correct_count
            )
        
        return user_profile
    
    def is_cold_start(self, user_profile: UserProfile) -> bool:
        """Check if user is in cold-start phase (first 20 questions)"""
        return len(user_profile.question_history) < 20
    
    def save_user_state(self, user_id: str, user_profile: UserProfile):
        """Save current student states back to user profile.

        Copies ALL in-memory student states to user_profile.skill_states,
        creating new entries for skills that were practiced but not yet in
        the profile (e.g. skills added during assessment).
        """
        if user_id in self.student_states:
            for skill_id, student_state in self.student_states[user_id].items():
                # Always save — create entry if missing (Bug #22 fix)
                user_profile.skill_states[skill_id] = SkillState(
                    memory_strength=student_state.memory_strength,
                    last_practice_time=student_state.last_practice_time,
                    practice_count=student_state.practice_count,
                    correct_count=student_state.correct_count
                )

        self.user_manager.save_user(user_profile)
    
    def record_question_attempt(self, user_profile: UserProfile, question_id: str, 
                              skill_ids: List[str], is_correct: bool, 
                              response_time_seconds: float):
        """Record a question attempt and update both memory and persistent storage"""
        current_time = time.time()
        time_penalty_applied = self.calculate_time_penalty(response_time_seconds) < 1.0
        
        # Get question details for logging (on-demand creation)
        question = self._get_or_create_question(question_id)
        question_difficulty = question.difficulty if question else "unknown"
        expected_time = question.expected_time_seconds if question else 0.0
        time_ratio = response_time_seconds / expected_time if expected_time > 0 else 0.0
        
        skill_names = [self.skills.get(sid).name if self.skills.get(sid) else sid for sid in skill_ids]
        
        result_str = 'CORRECT' if is_correct else 'INCORRECT'
        log_print(f"[ANSWER_SUBMITTED] Q:{question_id} | {result_str} | Time:{response_time_seconds:.1f}s | Skills:{','.join(skill_ids)}")
        
        # Update memory states
        affected_skills = self.update_with_prerequisites(
            user_profile.user_id, skill_ids, is_correct, current_time, response_time_seconds
        )
        
        # Save to persistent storage
        self.save_user_state(user_profile.user_id, user_profile)
        
        # Add to question history
        self.user_manager.add_question_attempt(
            user_profile, question_id, skill_ids, is_correct, 
            response_time_seconds, time_penalty_applied
        )

        # Record attempt for per-skill adaptive difficulty tracking
        for sid in skill_ids:
            self.record_attempt_for_difficulty(user_profile.user_id, sid, is_correct)

        # Notify ContentGenerationService on mastery progression
        if self.content_service:
            current_time_now = time.time()
            for sid in skill_ids:
                skill = self.skills.get(sid)
                if not skill:
                    continue
                probability = self.predict_correctness(
                    user_profile.user_id, sid, current_time_now
                )
                new_level = mastery_level_from_probability(probability)
                # Fire-and-forget pool warm-up when student progresses
                if new_level.value >= MasteryLevel.FAMILIAR.value:
                    self._fire_and_forget_sync(
                        self.content_service.on_skill_unlock,
                        student_id=user_profile.user_id,
                        skill_id=sid,
                        skill_name=skill.name,
                        grade=skill.grade_level.name,
                        subject=self.subject,
                    )

        return affected_skills

    # ------------------------------------------------------------------ #
    #  Cross-mode question exclusion                                      #
    # ------------------------------------------------------------------ #
    def _get_recent_assessment_question_ids(self, user_id: str) -> set:
        """Return question IDs used in recent assessment sessions for this user.
        Prevents the learning path from serving the same questions the student
        just saw during assessment."""
        try:
            sessions = self.mongo.db["assessment_sessions"].find(
                {"user_id": user_id},
                {"used_question_ids": 1},
            ).sort("created_at", -1).limit(5)  # Last 5 sessions
            ids: set = set()
            for s in sessions:
                ids.update(s.get("used_question_ids", []))
            return ids
        except Exception:
            return set()

    # ------------------------------------------------------------------ #
    #  AI-subject grading panel  (uses self.skills, not questions_db)     #
    # ------------------------------------------------------------------ #
    def _get_ai_grading_panel(self, user_id: str) -> Dict[str, Any]:
        """Build grading panel from DASH skill graph for AI-generated subjects.

        Reads persisted skill_states from MongoDB (source of truth) instead of
        in-memory self.student_states, which can be stale after load_user_or_create
        resets them.
        """
        current_time = time.time()
        subject_name = self.subject or "General"

        grading_data: Dict[str, Any] = {
            "subjects": {},
            "overall_grade": "N/A",
            "overall_mastery": 0,
        }

        # ── Load user profile from MongoDB (source of truth for practice data) ──
        user_profile = self.user_manager.load_user(user_id)
        profile_states = user_profile.skill_states if user_profile else {}

        # ── Grade range filter (same ±2 logic as Khan path) ──
        student_grade_value = 0  # Default to K
        if user_profile and user_profile.current_grade:
            try:
                student_grade_value = parse_grade_level(user_profile.current_grade).value
            except (KeyError, Exception):
                student_grade_value = 0
        log_print(f"[GRADING_PANEL_AI] user={user_id}, profile_found={user_profile is not None}, "
                  f"current_grade={getattr(user_profile, 'current_grade', None)}, "
                  f"grade_value={student_grade_value}, profile_skills={len(profile_states)}")

        grade_range = 2
        grade_min = max(0, student_grade_value - grade_range)
        grade_max = min(12, student_grade_value + grade_range)
        log_print(f"[GRADING_PANEL_AI] Showing grades {grade_min}-{grade_max} (student grade {student_grade_value})")

        total_mastery = 0.0
        practiced_count = 0
        filtered_count = 0

        for skill_id, skill in self.skills.items():
            grade_name = skill.grade_level.name if skill.grade_level else "Unknown"
            # Normalise grade label for display
            grade_label = "K" if grade_name == "K" else grade_name.replace("GRADE_", "")

            # ── Filter to ±2 grade range (Bug #33) ──
            try:
                skill_grade_val = skill.grade_level.value if skill.grade_level else -1
            except Exception:
                skill_grade_val = -1
            if skill_grade_val < grade_min or skill_grade_val > grade_max:
                filtered_count += 1
                continue

            # Ensure subject → grade structure
            subj_dict = grading_data["subjects"].setdefault(
                subject_name, {"grade_levels": {}}
            )
            grade_dict = subj_dict["grade_levels"].setdefault(
                grade_label, {"units": []}
            )

            # Pull student state from MongoDB profile (Bug #22 fix)
            # This is the source of truth — in-memory states can be stale
            profile_state = profile_states.get(skill_id)
            attempts = profile_state.practice_count if profile_state else 0
            correct = profile_state.correct_count if profile_state else 0
            mastery_pct = (correct / attempts * 100) if attempts > 0 else 0

            if attempts > 0:
                total_mastery += mastery_pct
                practiced_count += 1

            mastery_lvl = mastery_level_from_probability(mastery_pct / 100.0)

            grade_dict["units"].append({
                "id": skill_id,
                "name": skill.name,
                "mastery": round(mastery_pct, 1),
                "mastery_level_name": mastery_lvl.name,
                "mastery_level_number": mastery_lvl.value,
                "questions_answered": attempts,
                "questions_correct": correct,
                "sub_skills": [],
            })

        # Overall grade
        if practiced_count > 0:
            avg = total_mastery / practiced_count
            grading_data["overall_mastery"] = round(avg, 1)
            grading_data["overall_grade"] = (
                "A" if avg >= 90 else "B" if avg >= 80 else
                "C" if avg >= 70 else "D" if avg >= 60 else "F"
            )

        log_print(f"[GRADING_PANEL_AI] {subject_name}: {len(self.skills)} total skills, "
                  f"{filtered_count} filtered out, {len(self.skills) - filtered_count} shown, "
                  f"{practiced_count} practiced, overall_grade={grading_data['overall_grade']}")
        return grading_data

    def get_grading_panel_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get grading panel data. For AI-generated subjects, build from
        self.skills (the DASH skill graph). For Khan (Math), fall back
        to the questions_db hierarchy.
        """
        try:
            # ---------- AI-subject fast-path ----------
            if self.use_ai_questions and self.skills:
                return self._get_ai_grading_panel(user_id)

            # ---------- Khan hierarchy (original) ----------
            # 0. Load user profile to get grade range for filtering
            user_profile = self.user_manager.load_user(user_id)
            student_grade_value = 0  # Default to K
            if user_profile and user_profile.current_grade:
                try:
                    student_grade_value = parse_grade_level(user_profile.current_grade).value
                except KeyError:
                    student_grade_value = 0
            grade_range = 2  # Show skills within ±2 grades of student
            grade_min = max(0, student_grade_value - grade_range)
            grade_max = min(12, student_grade_value + grade_range)
            log_print(f"[GRADING_PANEL] Student grade: {student_grade_value}, showing grades {grade_min}-{grade_max}")

            # 1. Get current Khan Academy hierarchy from questions_db
            units = list(self.mongo.units.find({}))

            # 2. Get all question attempts for this student
            attempts = list(self.mongo.question_attempts.find({"user_id": user_id}))

            # OPTIMIZATION: Batch load all questions, lessons, and courses to avoid N+1 queries
            question_ids = [attempt.get("question_id") for attempt in attempts if attempt.get("question_id")]
            questions_list = list(self.mongo.questions.find({"question_id": {"$in": question_ids}}))
            questions_by_id = {q["question_id"]: q for q in questions_list}

            lesson_ids = [q.get("lesson_id") for q in questions_list if q.get("lesson_id")]
            lessons_list = list(self.mongo.lessons.find({"lesson_id": {"$in": lesson_ids}}))
            lessons_by_id = {l["lesson_id"]: l for l in lessons_list}

            course_ids = list(set([unit.get("course_id") for unit in units if unit.get("course_id")]))
            courses_list = list(self.mongo.courses.find({"course_id": {"$in": course_ids}}))
            courses_by_id = {c["course_id"]: c for c in courses_list}

            # 3. Build performance map: unit_id -> {correct, total, lessons}
            unit_performance = {}

            for attempt in attempts:
                question_id = attempt.get("question_id")

                # Find question -> lesson -> unit path using batch-loaded data
                question = questions_by_id.get(question_id)
                if not question:
                    continue

                lesson_id = question.get("lesson_id")
                if not lesson_id:
                    continue

                lesson = lessons_by_id.get(lesson_id)
                if not lesson:
                    continue

                unit_id = lesson.get("unit_id")
                if not unit_id:
                    continue

                # Initialize unit performance
                if unit_id not in unit_performance:
                    unit_performance[unit_id] = {
                        "correct": 0,
                        "total": 0,
                        "lessons": {}
                    }

                # Update unit totals
                unit_performance[unit_id]["total"] += 1
                if attempt.get("is_correct"):
                    unit_performance[unit_id]["correct"] += 1

                # Track lesson-level performance (sub-skills)
                if lesson_id not in unit_performance[unit_id]["lessons"]:
                    unit_performance[unit_id]["lessons"][lesson_id] = {
                        "lesson_name": lesson.get("title"),
                        "correct": 0,
                        "total": 0
                    }

                unit_performance[unit_id]["lessons"][lesson_id]["total"] += 1
                if attempt.get("is_correct"):
                    unit_performance[unit_id]["lessons"][lesson_id]["correct"] += 1

            # 4. Build grading panel structure organized by subject and grade
            grading_data = {
                "subjects": {},
                "overall_grade": None,
                "overall_mastery": 0
            }

            total_mastery = 0
            total_units_with_attempts = 0

            # Sort units by grade level before processing
            # First, we need to get course info for each unit to determine grade
            units_with_grade = []
            for unit in units:
                unit_id = unit.get("unit_id")
                course_id = unit.get("course_id")

                # Get course to determine grade level
                course = courses_by_id.get(course_id)
                if not course:
                    continue

                # Extract grade level from course
                grade_level_enum = derive_grade_from_course(
                    course.get("title", ""),
                    course.get("slug", ""),
                    course.get("order_in_region", 0)
                )

                # Store unit with its grade level value for sorting
                grade_value = grade_level_enum.value if grade_level_enum else 999
                units_with_grade.append((unit, course, grade_level_enum, grade_value))

            # Sort by grade level (ascending order: K=0, Grade1=1, ..., Grade12=12)
            units_with_grade.sort(key=lambda x: x[3])

            # Filter units by student's grade range (±2 grades)
            # Always include units that have attempts (so practiced skills always show)
            units_with_attempts_ids = set(unit_performance.keys())
            units_with_grade = [
                (unit, course, grade_level_enum, gv)
                for unit, course, grade_level_enum, gv in units_with_grade
                if (grade_min <= gv <= grade_max) or unit.get("unit_id") in units_with_attempts_ids
            ]
            log_print(f"[GRADING_PANEL] Filtered to {len(units_with_grade)} units (grade range {grade_min}-{grade_max} + units with attempts)")

            for unit, course, grade_level_enum, grade_value in units_with_grade:
                unit_id = unit.get("unit_id")
                course_id = unit.get("course_id")

                # Extract subject and grade level from course (already computed above)
                subject = extract_subject(course.get("title", ""))
                # Format grade level for display (K, 1, 2, ... 12)
                if grade_level_enum:
                    grade_level = "K" if grade_level_enum == KhanGradeLevel.K else str(grade_level_enum.value)
                else:
                    grade_level = "Unknown"
                
                # Initialize subject in grading data
                if subject not in grading_data["subjects"]:
                    grading_data["subjects"][subject] = {
                        "grade_levels": {}
                    }
                
                # Initialize grade level
                if grade_level not in grading_data["subjects"][subject]["grade_levels"]:
                    grading_data["subjects"][subject]["grade_levels"][grade_level] = {
                        "units": []
                    }
                
                # Calculate unit mastery
                perf = unit_performance.get(unit_id, {"correct": 0, "total": 0, "lessons": {}})
                mastery = (perf["correct"] / perf["total"] * 100) if perf["total"] > 0 else 0
                
                if perf["total"] > 0:
                    total_mastery += mastery
                    total_units_with_attempts += 1
                
                # Build sub-skills (lessons) data
                sub_skills = []
                for lesson_id, lesson_perf in perf["lessons"].items():
                    lesson_mastery = (lesson_perf["correct"] / lesson_perf["total"] * 100) if lesson_perf["total"] > 0 else 0
                    sub_skills.append({
                        "id": lesson_id,
                        "name": lesson_perf["lesson_name"],
                        "mastery": round(lesson_mastery, 1),
                        "questions_answered": lesson_perf["total"],
                        "questions_correct": lesson_perf["correct"]
                    })
                
                # Determine mastery level from percentage
                mastery_lvl = mastery_level_from_probability(mastery / 100.0)

                # Add unit to grading data
                grading_data["subjects"][subject]["grade_levels"][grade_level]["units"].append({
                    "id": unit_id,
                    "name": unit.get("title"),
                    "mastery": round(mastery, 1),
                    "mastery_level_name": mastery_lvl.name,
                    "mastery_level_number": mastery_lvl.value,
                    "questions_answered": perf["total"],
                    "questions_correct": perf["correct"],
                    "sub_skills": sub_skills
                })
            
            # 5. Calculate overall grade
            if total_units_with_attempts > 0:
                avg_mastery = total_mastery / total_units_with_attempts
                grading_data["overall_mastery"] = round(avg_mastery, 1)
                
                if avg_mastery >= 90:
                    grading_data["overall_grade"] = "A"
                elif avg_mastery >= 80:
                    grading_data["overall_grade"] = "B"
                elif avg_mastery >= 70:
                    grading_data["overall_grade"] = "C"
                elif avg_mastery >= 60:
                    grading_data["overall_grade"] = "D"
                else:
                    grading_data["overall_grade"] = "F"
            else:
                grading_data["overall_grade"] = "N/A"
            
            log_print(f"[GRADING_PANEL] Generated data for {total_units_with_attempts} units with attempts")
            return grading_data
            
        except Exception as e:
            log_print(f"[ERROR] Error getting grading panel data: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_skills_due_for_review(
        self,
        student_id: str,
        current_time: float,
        decay_threshold: float = 0.6,
    ) -> List[str]:
        """
        Find previously mastered skills that have decayed below the review threshold.
        Returns skill IDs sorted by most decayed first.
        """
        review_skills = []
        for skill_id, skill in self.skills.items():
            state = self.get_student_state(student_id, skill_id)
            # Only consider skills that were practiced and reached mastery
            if state.last_practice_time is None or state.practice_count < 3:
                continue
            # Check stored strength (pre-decay) was high enough to have been mastered
            stored_logit = state.memory_strength - skill.difficulty
            stored_prob = 1 / (1 + math.exp(-stored_logit))
            if stored_prob < 0.7:
                continue  # Was never mastered
            # Check current (decayed) probability is below review threshold
            current_prob = self.predict_correctness(student_id, skill_id, current_time)
            if current_prob < decay_threshold:
                review_skills.append((skill_id, current_prob))

        # Sort by most decayed first
        review_skills.sort(key=lambda x: x[1])
        return [sid for sid, _ in review_skills]

    PREREQ_REVIEW_THRESHOLD = 0.6  # Below this, review the prerequisite

    def get_prerequisite_review_skills(
        self,
        student_id: str,
        current_skill_ids: List[str],
        current_time: float,
    ) -> List[str]:
        """Find prerequisites of currently-active skills that need review.

        Returns skill IDs of prerequisites whose probability has decayed
        below PREREQ_REVIEW_THRESHOLD, sorted by most decayed first.
        This prevents students from forgetting foundational skills while
        working on advanced ones.
        """
        review_candidates = []
        seen: set = set()

        for skill_id in current_skill_ids:
            skill = self.skills.get(skill_id)
            if not skill:
                continue
            for prereq_id in skill.prerequisites:
                if prereq_id in seen:
                    continue
                seen.add(prereq_id)
                prereq_skill = self.skills.get(prereq_id)
                if not prereq_skill:
                    continue
                state = self.get_student_state(student_id, prereq_id)
                if state.practice_count < 3:
                    continue  # Not enough history to warrant review
                prob = self.predict_correctness(student_id, prereq_id, current_time)
                if prob < self.PREREQ_REVIEW_THRESHOLD:
                    review_candidates.append((prereq_id, prob))

        review_candidates.sort(key=lambda x: x[1])
        if review_candidates:
            log_print(
                f"[PREREQ_REVIEW] Found {len(review_candidates)} prerequisite(s) needing review: "
                + ", ".join(f"{sid}({p:.2f})" for sid, p in review_candidates[:5])
            )
        return [sid for sid, _ in review_candidates]

    def get_recommended_skills(
        self,
        student_id: str,
        current_time: float,
        threshold: float = 0.7,
        cold_start_grade_filter: Optional[str] = None,
        grade_range: int = 1
    ) -> List[str]:
        """
        Get skills that need practice based on memory strength decay.
        Returns skills sorted by learning journey: grade level -> order -> probability.
        
        Args:
            student_id: Unique student identifier
            current_time: Current timestamp
            threshold: Probability threshold for recommendations
            cold_start_grade_filter: If provided, only recommend skills within ±grade_range
            grade_range: How many grades above/below to include (default: 1)
        """
        recommendations = []
        skipped_prerequisites = []
        skipped_above_threshold = []
        skipped_grade_filter = []
        
        # Parse grade filter if provided
        target_grade = None
        if cold_start_grade_filter:
            try:
                target_grade = GradeLevel[cold_start_grade_filter]
            except KeyError:
                logger.warning(f"[FILTER] Invalid grade filter: {cold_start_grade_filter}")

        # Collect prerequisite IDs for in-range skills so they aren't grade-filtered out
        prereq_ids_for_in_range = set()
        if target_grade is not None:
            for sid, sk in self.skills.items():
                if abs(sk.grade_level.value - target_grade.value) <= grade_range:
                    prereq_ids_for_in_range.update(sk.prerequisites)

        for skill_id, skill in self.skills.items():
            # Apply grade filter if in cold-start mode
            if target_grade is not None:
                grade_diff = abs(skill.grade_level.value - target_grade.value)
                if grade_diff > grade_range and skill_id not in prereq_ids_for_in_range:
                    skipped_grade_filter.append((skill_id, skill.name, skill.grade_level.name))
                    continue
            
            probability = self.predict_correctness(student_id, skill_id, current_time)
            
            # Check if prerequisites are met
            prerequisites_met = True
            missing_prereqs = []
            for prereq_id in skill.prerequisites:
                # Don't block on prerequisites the student has never attempted
                prereq_state = self.get_student_state(student_id, prereq_id)
                if prereq_state.practice_count == 0:
                    continue
                prereq_prob = self.predict_correctness(student_id, prereq_id, current_time)
                if prereq_prob < threshold:
                    prerequisites_met = False
                    missing_prereqs.append((prereq_id, prereq_prob))
            
            # Recommend if probability is below threshold and prerequisites are met
            if probability < threshold and prerequisites_met:
                recommendations.append((skill_id, skill, probability))
            elif not prerequisites_met:
                skipped_prerequisites.append((skill_id, skill.name, missing_prereqs))
            elif probability >= threshold:
                skipped_above_threshold.append((skill_id, skill.name, probability))
        
        # Log grade filtering if applied
        if skipped_grade_filter and cold_start_grade_filter:
            log_print(f"[FILTER] Skipped {len(skipped_grade_filter)} skills outside grade range {cold_start_grade_filter}+-{grade_range}")
        
        # Log skill recommendation details for investigation
        if skipped_above_threshold:
            log_print(f"[SKILL_RECOMMEND] Skipped {len(skipped_above_threshold)} skills above threshold (>= {threshold}):")
            for skill_id, skill_name, prob in skipped_above_threshold[:5]:  # Show top 5
                log_print(f"  - {skill_name[:30]:<30} (prob: {prob:.3f})")
        
        if skipped_prerequisites:
            log_print(f"[SKILL_RECOMMEND] Skipped {len(skipped_prerequisites)} skills with unmet prerequisites")
        
        # Sort by learning journey: grade → order → mastery priority → probability
        # Prioritize FAMILIAR/PROFICIENT (0.3-0.7) over ATTEMPTED (<0.3) since they're closer to mastery
        recommendations.sort(key=lambda x: (
            x[1].grade_level.value,  # Grade level (K=0, Grade 1=1, etc.)
            x[1].order,                # Order within grade
            0 if 0.3 <= x[2] < 0.7 else 1,  # FAMILIAR/PROFICIENT before ATTEMPTED
            x[2]                       # Probability (lower = needs more practice)
        ))
        
        # Log recommended skills for investigation
        if recommendations:
            log_print(f"[SKILL_RECOMMEND] Found {len(recommendations)} skills needing practice (prob < {threshold}):")
            for skill_id, skill, prob in recommendations[:5]:  # Show top 5
                log_print(f"  - {skill.name[:30]:<30} (prob: {prob:.3f}, grade: {skill.grade_level.name}, order: {skill.order})")
        else:
            log_print(f"[SKILL_RECOMMEND] No skills found needing practice (all above threshold {threshold} or prerequisites unmet)")
        
        result = [skill_id for skill_id, _, _ in recommendations]

        # If grade filter produced 0 recommendations, retry without it
        if not result and cold_start_grade_filter:
            logger.info(f"[RECOMMEND] Grade filter ±{grade_range} found 0 skills, retrying with all grades")
            return self.get_recommended_skills(
                student_id, current_time, threshold=threshold,
                cold_start_grade_filter=None, grade_range=grade_range,
            )

        # Interleave review skills (previously mastered, now decayed) every 3rd position
        # Also include prerequisite reviews for currently-active skills
        review_ids = self.get_skills_due_for_review(student_id, current_time)
        active_skill_ids = [sid for sid, _, _ in recommendations[:5]]
        prereq_review_ids = self.get_prerequisite_review_skills(
            student_id, active_skill_ids, current_time
        )
        # Merge: prereq reviews take priority over general reviews
        prereq_set = set(prereq_review_ids)
        combined_review_ids = prereq_review_ids + [
            sid for sid in review_ids if sid not in prereq_set
        ]
        review_ids = combined_review_ids
        if review_ids:
            # Remove any review skills already in the result to avoid duplicates
            review_ids = [sid for sid in review_ids if sid not in set(result)]
            if review_ids:
                log_print(f"[REVIEW] Interleaving {len(review_ids)} review skill(s) into recommendations")
                merged = []
                ri = 0
                for i, sid in enumerate(result):
                    # Insert a review skill every 3rd position
                    if (i + 1) % 3 == 0 and ri < len(review_ids):
                        merged.append(review_ids[ri])
                        ri += 1
                    merged.append(sid)
                # Append any remaining review skills
                merged.extend(review_ids[ri:])
                result = merged

        return result
    
    def _ensure_difficulty_history_index(self):
        """Create compound index on student_difficulty_history for fast lookups.
        
        Schema: one document per (student_id, skill_id) with a capped
        ``attempts`` array holding the last 10 results.
        """
        try:
            coll = self.mongo.db['student_difficulty_history']
            coll.create_index(
                [("student_id", 1), ("skill_id", 1)],
                name="student_skill_idx",
                unique=True,
                background=True,
            )
            log_print("[ADAPTIVE_DIFFICULTY] Ensured index on student_difficulty_history")
        except Exception as e:
            log_print(f"[ADAPTIVE_DIFFICULTY] Index creation warning (non-fatal): {e}")

    def get_adaptive_difficulty(self, student_id: str, skill_id: str) -> float:
        """
        Calculate adaptive difficulty based on recent per-skill performance.

        Uses last 5 attempts on this skill to adjust the base difficulty from
        the mastery level system.  The adjustment is an offset applied on top
        of the existing base difficulty (skill.difficulty), keeping the mastery
        logic untouched.

        Adjustment rules (based on correct rate over last 5 attempts):
            rate >= 0.8  -> base + 0.12  (student excelling, push harder)
            rate >= 0.6  -> base + 0.05  (slight increase)
            rate >= 0.4  -> base + 0.00  (optimal challenge zone)
            rate >= 0.2  -> base - 0.10  (struggling, ease off)
            rate <  0.2  -> base - 0.20  (really struggling, significant ease)

        Returns:
            float clamped to [0.2, 1.0]
        """
        # 1. Base difficulty from skill definition
        skill = self.skills.get(skill_id)
        base_difficulty = skill.difficulty if skill else 0.5

        # 2. Fetch the attempts array for this student + skill from MongoDB
        if not self.mongo:
            return max(0.2, min(1.0, base_difficulty))

        try:
            coll = self.mongo.db['student_difficulty_history']
            doc = coll.find_one(
                {"student_id": student_id, "skill_id": skill_id},
                {"attempts": 1, "_id": 0},
            )
        except Exception as e:
            log_print(f"[ADAPTIVE_DIFFICULTY] DB read failed for {student_id}/{skill_id}: {e}")
            return max(0.2, min(1.0, base_difficulty))

        # 3. Extract last 5 attempts from the capped array
        if not doc or not doc.get("attempts"):
            return max(0.2, min(1.0, base_difficulty))

        recent = doc["attempts"][-5:]  # Last 5 (array is already capped at 10)

        # If fewer than 2 attempts, not enough data — return base
        if len(recent) < 2:
            return max(0.2, min(1.0, base_difficulty))

        # 4. Calculate recent correct rate
        correct_count = sum(1 for a in recent if a.get("correct", False))
        rate = correct_count / len(recent)

        # 5. Determine adjustment offset
        if rate >= 0.8:
            adjustment = 0.12
        elif rate >= 0.6:
            adjustment = 0.05
        elif rate >= 0.4:
            adjustment = 0.0
        elif rate >= 0.2:
            adjustment = -0.10
        else:
            adjustment = -0.20

        adjusted = base_difficulty + adjustment

        log_print(
            f"[ADAPTIVE_DIFFICULTY] student={student_id} skill={skill_id} "
            f"rate={rate:.2f} ({correct_count}/{len(recent)}) "
            f"base={base_difficulty:.2f} adj={adjustment:+.2f} final={max(0.2, min(1.0, adjusted)):.2f}"
        )

        # 6. Clamp to [0.2, 1.0] — allows synthesis tier (0.92-1.0) for experts
        return max(0.2, min(1.0, adjusted))

    def record_attempt_for_difficulty(self, student_id: str, skill_id: str, correct: bool):
        """
        Record an attempt result for per-skill adaptive difficulty tracking.

        Stores in MongoDB collection ``ai_tutor.student_difficulty_history``.
        Each document: {student_id, skill_id, correct, timestamp}.
        Uses $push with $slice: -10 to keep only the last 10 per student+skill,
        preventing unbounded growth.
        """
        if not self.mongo:
            return

        try:
            coll = self.mongo.db['student_difficulty_history']

            # Upsert a document per (student_id, skill_id) with a capped array
            # of recent attempts. This avoids creating thousands of tiny docs.
            coll.update_one(
                {"student_id": student_id, "skill_id": skill_id},
                {
                    "$push": {
                        "attempts": {
                            "$each": [{"correct": correct, "ts": datetime.utcnow()}],
                            "$slice": -10,
                        }
                    },
                    "$set": {"updated_at": datetime.utcnow()},
                    "$setOnInsert": {"created_at": datetime.utcnow()},
                },
                upsert=True,
            )
        except Exception as e:
            log_print(f"[ADAPTIVE_DIFFICULTY] Failed to record attempt for {student_id}/{skill_id}: {e}")

    def analyze_recent_performance(self, user_profile: UserProfile, lookback_count: int = 5) -> Dict[str, float]:
        """
        Analyze recent performance to determine difficulty adjustment.
        Returns a dict with:
        - 'performance_score': -1.0 (struggling) to 1.0 (excelling)
        - 'difficulty_adjustment': negative = easier, positive = harder
        - 'correctness_rate': 0.0 to 1.0
        - 'avg_time_ratio': average response time / expected time
        """
        if not user_profile.question_history or len(user_profile.question_history) == 0:
            # No history: start with medium difficulty
            log_print(f"[ADAPTIVE_DIFFICULTY] Student {user_profile.user_id}: No question history, using default difficulty (no adjustment)")
            return {
                'performance_score': 0.0,
                'difficulty_adjustment': 0.0,
                'correctness_rate': 0.5,
                'avg_time_ratio': 1.0
            }
        
        # Get recent attempts (last N questions)
        recent_attempts = user_profile.question_history[-lookback_count:]
        total_history = len(user_profile.question_history)
        
        # Calculate correctness rate
        correct_count = sum(1 for attempt in recent_attempts if attempt.is_correct)
        correctness_rate = correct_count / len(recent_attempts)
        
        # Calculate average response time ratio
        # Get expected time from questions (on-demand creation)
        time_ratios = []
        time_details = []
        for attempt in recent_attempts:
            question = self._get_or_create_question(attempt.question_id)
            if question and attempt.response_time_seconds > 0:
                expected_time = question.expected_time_seconds
                if expected_time > 0:
                    time_ratio = attempt.response_time_seconds / expected_time
                    time_ratios.append(time_ratio)
                    time_details.append((attempt.question_id, attempt.response_time_seconds, expected_time, time_ratio))
        
        avg_time_ratio = sum(time_ratios) / len(time_ratios) if time_ratios else 1.0
        
        # Calculate performance score
        # - Correctness contributes 60% weight
        # - Time efficiency contributes 40% weight
        correctness_score = (correctness_rate - 0.5) * 2.0  # -1.0 to 1.0
        time_score = (1.0 - min(avg_time_ratio, 2.0) / 2.0) * 2.0 - 1.0  # -1.0 to 1.0 (faster = better)
        
        performance_score = correctness_score * 0.6 + time_score * 0.4
        
        # Determine difficulty adjustment
        # If struggling (low correctness, slow): make easier (negative adjustment)
        # If excelling (high correctness, fast): make harder (positive adjustment)
        if performance_score < -0.3:
            # Struggling: easier questions (reduce difficulty by 0.2-0.4)
            difficulty_adjustment = -0.3
            performance_level = "STRUGGLING"
        elif performance_score < -0.1:
            # Slightly struggling: slightly easier (reduce by 0.1-0.2)
            difficulty_adjustment = -0.15
            performance_level = "SLIGHTLY_STRUGGLING"
        elif performance_score > 0.3:
            # Excelling: harder questions (increase difficulty by 0.2-0.4)
            difficulty_adjustment = 0.3
            performance_level = "EXCELLING"
        elif performance_score > 0.1:
            # Slightly excelling: slightly harder (increase by 0.1-0.2)
            difficulty_adjustment = 0.15
            performance_level = "SLIGHTLY_EXCELLING"
        else:
            # Balanced performance: maintain current difficulty
            difficulty_adjustment = 0.0
            performance_level = "BALANCED"
        
        # Removed verbose logging - only essential info logged elsewhere
        
        return {
            'performance_score': performance_score,
            'difficulty_adjustment': difficulty_adjustment,
            'correctness_rate': correctness_rate,
            'avg_time_ratio': avg_time_ratio
        }

    def get_next_question_flexible(self, student_id: str, current_time: float, exclude_question_ids: Optional[List[str]] = None, force_grade_range: bool = False, user_profile: Optional['UserProfile'] = None, exclude_skill_ids: Optional[List[str]] = None, fast_mode: bool = False) -> Optional[Question]:
        """
        Flexible question selection that expands search when primary skills exhausted.
        Maintains full DASH intelligence (adaptive difficulty, learning journey).

        Args:
            student_id: Student identifier
            current_time: Current timestamp
            exclude_question_ids: Question IDs to exclude
            force_grade_range: If True, search all grade-appropriate skills (not just recommended)
            user_profile: Optional pre-loaded user profile to avoid redundant MongoDB calls
            exclude_skill_ids: Skill IDs to exclude from selection (for diversifying questions)

        Returns:
            Question with full DASH intelligence, or None if truly no questions available
        """
        # Load user profile once and reuse throughout
        if user_profile is None:
            user_profile = self.user_manager.load_user(student_id)
        if not user_profile:
            return None

        # First try normal DASH selection (recommended skills only)
        if not force_grade_range:
            # Prevent recursion loop: get_next_question() may fallback to flexible mode
            # when no skills are recommended. Mark this as retry so it can return None.
            question = self.get_next_question(
                student_id,
                current_time,
                is_retry=True,
                exclude_question_ids=exclude_question_ids,
                user_profile=user_profile,
                fast_mode=fast_mode,
            )
            if question:
                return question
        
        # Get grade range (same as cold-start filtering)
        student_grade = parse_grade_level(user_profile.current_grade)
        grade_min = max(0, student_grade.value - 1)
        grade_max = student_grade.value + 1

        # Get all skills in grade range, but exclude mastered skills (above threshold)
        # Cache predictions to avoid computing twice per skill (filter + sort)
        current_time_for_check = time.time()
        threshold = 0.7  # Same threshold as get_recommended_skills
        _prob_cache: Dict[str, float] = {}
        grade_appropriate_skills = []
        for skill in self.skills.values():
            if grade_min <= skill.grade_level.value <= grade_max:
                probability = self.predict_correctness(student_id, skill.skill_id, current_time_for_check)
                _prob_cache[skill.skill_id] = probability
                if probability < threshold:  # Only include skills that need practice
                    grade_appropriate_skills.append(skill)
                elif not fast_mode:
                    log_print(f"[FLEXIBLE_SELECT] Skipping mastered skill: {skill.name} (prob: {probability:.3f} >= {threshold})")

        if not grade_appropriate_skills:
            log_print(f"[FLEXIBLE_SELECT] No grade-appropriate skills need practice (all mastered)")
            return None

        # Sort by learning journey (grade -> order -> current probability)
        # Reuse cached predictions instead of calling predict_correctness again
        skill_probabilities = []
        for skill in grade_appropriate_skills:
            prob = _prob_cache.get(skill.skill_id, self.predict_correctness(student_id, skill.skill_id, current_time))
            skill_probabilities.append((skill.skill_id, skill, prob))
        
        # Sort by grade level, order, then probability (lower prob = needs more practice)
        skill_probabilities.sort(key=lambda x: (x[1].grade_level.value, x[1].order, x[2]))
        if fast_mode and len(skill_probabilities) > FAST_MODE_SKILL_SCAN_LIMIT:
            skill_probabilities = skill_probabilities[:FAST_MODE_SKILL_SCAN_LIMIT]
        
        # Get answered questions to exclude (learning path + assessments)
        answered_question_ids = {attempt.question_id for attempt in user_profile.question_history}
        if exclude_question_ids:
            answered_question_ids.update(exclude_question_ids)
        # Also exclude questions used in recent assessment sessions
        answered_question_ids.update(self._get_recent_assessment_question_ids(student_id))

        # Analyze performance for global fallback adjustment
        performance_analysis = self.analyze_recent_performance(user_profile)
        global_difficulty_adjustment = performance_analysis['difficulty_adjustment']

        # Try each skill in learning journey order with adaptive difficulty
        for skill_id, skill, probability in skill_probabilities:
            # Skip excluded skills (for diversifying assessment questions)
            if exclude_skill_ids and skill_id in exclude_skill_ids:
                continue

            # Hard prerequisite check — skip skills whose prerequisites aren't met
            prereq_status = self.check_prerequisites(student_id, skill_id, current_time)
            if not prereq_status["met"]:
                if not fast_mode:
                    log_print(f"[FLEXIBLE_SELECT] Skipping {skill.name}: "
                              f"{len(prereq_status['missing'])} prerequisite(s) not met")
                continue

            # Use per-skill adaptive difficulty + global cross-skill momentum
            adaptive_base = self.get_adaptive_difficulty(student_id, skill_id)
            target_difficulty = max(0.1, min(1.0, adaptive_base + global_difficulty_adjustment))

            # --- Pool-based question serving (fast-path) ---
            if self.content_service:
                try:
                    if fast_mode:
                        pool_question = self.content_service.pop_assessment_question(
                            skill_id, target_difficulty, exclude_ids=answered_question_ids,
                            subject=self.subject or "")
                    else:
                        pool_question = self.content_service.pop_question(
                            skill_id, target_difficulty, exclude_ids=answered_question_ids,
                            subject=self.subject or "")
                    if pool_question:
                        q_id = pool_question.get("question_id", pool_question.get("dash_metadata", {}).get("dash_question_id", f"pool_{skill_id}"))
                        log_print(f"[QUESTION_SELECTED] Q:{q_id} | Skill:{skill.name} | "
                                  f"Difficulty:{target_difficulty:.2f} (FLEXIBLE_POOL, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                        # Attach dash_metadata to pool question for direct serving
                        if "dash_metadata" not in pool_question:
                            pool_question["dash_metadata"] = {
                                "dash_question_id": q_id,
                                "skill_ids": [skill_id],
                                "difficulty": pool_question.get("difficulty", target_difficulty),
                                "skill_names": [skill.name],
                                "unit_name": skill.name,
                                "lesson_name": "Practice",
                                "ai_generated": True,
                            }
                        # Proactive pool refill: check every 5th pop
                        self._pool_check_counter += 1
                        if self._pool_check_counter % 5 == 0 and not fast_mode:
                            try:
                                stats = self.content_service.get_pool_stats(skill_id)
                                low_threshold = max(3, int(int(os.getenv("POOL_MIN_PER_BUCKET", "10")) * 0.3))
                                if any(stats.get(b, 0) < low_threshold for b in ["easy", "medium", "hard", "synthesis"]):
                                    self._fire_and_forget_sync(
                                        self.content_service.ensure_pool,
                                        skill_id,
                                        skill_name=skill.name,
                                        grade=skill.grade_level.name,
                                        subject=self.subject,
                                    )
                            except Exception:
                                pass  # Non-critical
                        return Question(
                            question_id=q_id,
                            skill_ids=[skill_id],
                            content="",
                            difficulty=pool_question.get("difficulty", target_difficulty),
                            expected_time_seconds=60.0,
                            perseus_data=pool_question,
                        )
                    elif not fast_mode:
                        # Pool empty for this skill -- trigger background fill
                        # Skip in fast_mode to avoid Gemini rate limit contention
                        self._fire_and_forget_sync(
                            self.content_service.ensure_pool,
                            skill_id,
                            skill_name=skill.name,
                            grade=skill.grade_level.name,
                            subject=self.subject,
                        )
                    # Pool empty: try immediate JIT for this same skill before moving on
                    if not pool_question and self.use_ai_questions and self.ai_provider:
                        jit_result = self.ai_provider.get_question_for_skill(
                            skill_id=skill_id,
                            skill_name=skill.name,
                            target_difficulty=target_difficulty,
                            grade_level=skill.grade_level.name,
                            age=user_profile.age if user_profile else 7,
                            exclude_question_ids=answered_question_ids,
                            user_id=student_id,
                            fast_mode=fast_mode,
                            subject=self.subject or "",
                        )
                        if jit_result:
                            q_id = jit_result["dash_metadata"]["dash_question_id"]
                            log_print(f"[QUESTION_SELECTED] Q:{q_id} | Skill:{skill.name} | "
                                      f"Difficulty:{target_difficulty:.2f} (FLEXIBLE_POOL_JIT, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                            return Question(
                                question_id=q_id,
                                skill_ids=[skill_id],
                                content="",
                                difficulty=jit_result["dash_metadata"]["difficulty"],
                                expected_time_seconds=60.0,
                            )
                except Exception as e:
                    log_print(f"[CONTENT_SERVICE] Flexible pool pop failed for {skill_id}: {e}")
                # Fall through to existing AI/Khan logic on pool miss or error

            # --- AI-generated question path ---
            if self.use_ai_questions and self.ai_provider:
                ai_result = self.ai_provider.get_question_for_skill(
                    skill_id=skill_id,
                    skill_name=skill.name,
                    target_difficulty=target_difficulty,
                    grade_level=skill.grade_level.name,
                    age=user_profile.age if user_profile else 7,
                    exclude_question_ids=answered_question_ids,
                    user_id=student_id,
                    fast_mode=fast_mode,
                    subject=self.subject or "",
                )
                if ai_result:
                    q_id = ai_result["dash_metadata"]["dash_question_id"]
                    log_print(f"[QUESTION_SELECTED] Q:{q_id} | Skill:{skill.name} | "
                              f"Difficulty:{target_difficulty:.2f} (FLEXIBLE_AI, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                    return Question(
                        question_id=q_id,
                        skill_ids=[skill_id],
                        content="",
                        difficulty=ai_result["dash_metadata"]["difficulty"],
                        expected_time_seconds=60.0,
                    )
                continue  # Try next skill if AI provider returned nothing

            # --- Khan question bank path (original) ---
            min_difficulty = max(0.0, target_difficulty - 0.2)
            max_difficulty = target_difficulty + 0.2

            # Get question IDs for this skill from index (fast lookup)
            skill_question_ids = self.skill_question_index.get(skill_id, [])
            if not skill_question_ids:
                continue

            # Filter out answered questions
            candidate_ids = [qid for qid in skill_question_ids if qid not in answered_question_ids]
            if not candidate_ids:
                continue

            # Create Question objects on-demand from index
            all_candidates = []
            for qid in candidate_ids:
                question = self._get_or_create_question(qid)
                if question:
                    all_candidates.append(question)

            if not all_candidates:
                continue

            # Filter by difficulty range (adaptive selection)
            filtered_candidates = [
                q for q in all_candidates
                if min_difficulty <= q.difficulty <= max_difficulty
            ]

            # Select best match
            if filtered_candidates:
                filtered_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
                selected = filtered_candidates[0]
                log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                          f"Difficulty:{selected.difficulty:.2f} (FLEXIBLE, target:{target_difficulty:.2f}, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                return selected

            # Use closest match if no exact difficulty match
            all_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
            selected = all_candidates[0]
            log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                      f"Difficulty:{selected.difficulty:.2f} (FLEXIBLE_FALLBACK, target:{target_difficulty:.2f})")
            return selected

        # Truly no questions available in grade range
        return None
    
    def get_next_question(self, student_id: str, current_time: float, is_retry: bool = False, exclude_question_ids: Optional[List[str]] = None, user_profile: Optional['UserProfile'] = None, fast_mode: bool = False) -> Optional[Question]:
        """
        Get the next best question for the student, avoiding repeats.
        Intelligently selects question difficulty based on recent performance.
        If no questions are available, try to generate one.

        Args:
            user_profile: Optional pre-loaded user profile to avoid redundant MongoDB calls
        """
        # Use provided user_profile or load from DB (avoids redundant MongoDB calls)
        if user_profile is None:
            user_profile = self.user_manager.load_user(student_id)
        if not user_profile:
            return None
        
        # Apply grade filtering during cold-start phase (first 20 questions)
        # This ensures age-appropriate questions for new students
        cold_start_filter = None
        if self.is_cold_start(user_profile):
            cold_start_filter = user_profile.current_grade
        
        # Get recommended skills with optional grade filtering
        recommended_skills = self.get_recommended_skills(
            student_id, 
            current_time,
            cold_start_grade_filter=cold_start_filter,
            grade_range=1  # Allow ±1 grade level
        )
        if fast_mode and len(recommended_skills) > FAST_MODE_SKILL_SCAN_LIMIT:
            recommended_skills = recommended_skills[:FAST_MODE_SKILL_SCAN_LIMIT]
        
        if not recommended_skills:
            log_print(f"[GET_NEXT_QUESTION] No recommended skills — trying flexible selection")
            if is_retry:
                return None
            return self.get_next_question_flexible(
                student_id, current_time, exclude_question_ids,
                force_grade_range=True,
                user_profile=user_profile, fast_mode=fast_mode,
            )
        
        log_print(f"[GET_NEXT_QUESTION] Found {len(recommended_skills)} recommended skills for student {student_id}")
        
        answered_question_ids = {attempt.question_id for attempt in user_profile.question_history}

        # Also exclude questions that are already selected in the current batch
        if exclude_question_ids:
            answered_question_ids.update(exclude_question_ids)
        # Also exclude questions used in recent assessment sessions
        answered_question_ids.update(self._get_recent_assessment_question_ids(student_id))

        # Analyze recent performance for global fallback adjustment
        performance_analysis = self.analyze_recent_performance(user_profile)
        global_difficulty_adjustment = performance_analysis['difficulty_adjustment']
        
        # Try to find an unanswered question from the recommended skills with adaptive difficulty
        for skill_idx, skill_id in enumerate(recommended_skills, 1):
            skill = self.skills.get(skill_id)
            if not skill:
                continue

            # Hard prerequisite check — skip skills whose prerequisites aren't met
            prereq_status = self.check_prerequisites(student_id, skill_id, current_time)
            if not prereq_status["met"]:
                log_print(f"[GET_NEXT_QUESTION] Skipping {skill.name}: "
                          f"{len(prereq_status['missing'])} prerequisite(s) not met")
                continue

            # Use per-skill adaptive difficulty (falls back to base if < 2 attempts)
            # Then layer the global performance adjustment on top for combined signal
            adaptive_base = self.get_adaptive_difficulty(student_id, skill_id)
            # Global adjustment provides cross-skill momentum (hot streak / cold streak)
            target_difficulty = max(0.1, min(1.0, adaptive_base + global_difficulty_adjustment))

            # --- Pool-based question serving (fast-path) ---
            if self.content_service:
                try:
                    if fast_mode:
                        pool_question = self.content_service.pop_assessment_question(
                            skill_id, target_difficulty, exclude_ids=answered_question_ids,
                            subject=self.subject or "")
                    else:
                        pool_question = self.content_service.pop_question(
                            skill_id, target_difficulty, exclude_ids=answered_question_ids,
                            subject=self.subject or "")
                    if pool_question:
                        q_id = pool_question.get("question_id", pool_question.get("dash_metadata", {}).get("dash_question_id", f"pool_{skill_id}"))
                        log_print(f"[QUESTION_SELECTED] Q:{q_id} | Skill:{skill.name} | "
                                  f"Difficulty:{target_difficulty:.2f} (POOL, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                        if "dash_metadata" not in pool_question:
                            pool_question["dash_metadata"] = {
                                "dash_question_id": q_id,
                                "skill_ids": [skill_id],
                                "difficulty": pool_question.get("difficulty", target_difficulty),
                                "skill_names": [skill.name],
                                "unit_name": skill.name,
                                "lesson_name": "Practice",
                                "ai_generated": True,
                            }
                        # Proactive pool refill: check every 5th pop
                        self._pool_check_counter += 1
                        if self._pool_check_counter % 5 == 0 and not fast_mode:
                            try:
                                stats = self.content_service.get_pool_stats(skill_id)
                                low_threshold = max(3, int(int(os.getenv("POOL_MIN_PER_BUCKET", "10")) * 0.3))
                                if any(stats.get(b, 0) < low_threshold for b in ["easy", "medium", "hard", "synthesis"]):
                                    self._fire_and_forget_sync(
                                        self.content_service.ensure_pool,
                                        skill_id,
                                        skill_name=skill.name,
                                        grade=skill.grade_level.name,
                                        subject=self.subject,
                                    )
                            except Exception:
                                pass  # Non-critical
                        return Question(
                            question_id=q_id,
                            skill_ids=[skill_id],
                            content="",
                            difficulty=pool_question.get("difficulty", target_difficulty),
                            expected_time_seconds=60.0,
                            perseus_data=pool_question,
                        )
                    elif not fast_mode:
                        # Pool empty for this skill -- trigger background fill
                        # Skip in fast_mode to avoid Gemini rate limit contention
                        self._fire_and_forget_sync(
                            self.content_service.ensure_pool,
                            skill_id,
                            skill_name=skill.name,
                            grade=skill.grade_level.name,
                            subject=self.subject,
                        )
                    # Pool empty: try immediate JIT for this same skill before moving on
                    if not pool_question and self.use_ai_questions and self.ai_provider:
                        jit_result = self.ai_provider.get_question_for_skill(
                            skill_id=skill_id,
                            skill_name=skill.name,
                            target_difficulty=target_difficulty,
                            grade_level=skill.grade_level.name,
                            age=user_profile.age if user_profile else 7,
                            exclude_question_ids=answered_question_ids,
                            user_id=student_id,
                            fast_mode=fast_mode,
                            subject=self.subject or "",
                        )
                        if jit_result:
                            q_id = jit_result["dash_metadata"]["dash_question_id"]
                            log_print(f"[QUESTION_SELECTED] Q:{q_id} | Skill:{skill.name} | "
                                      f"Difficulty:{target_difficulty:.2f} (POOL_JIT, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                            return Question(
                                question_id=q_id,
                                skill_ids=[skill_id],
                                content="",
                                difficulty=jit_result["dash_metadata"]["difficulty"],
                                expected_time_seconds=60.0,
                            )
                except Exception as e:
                    log_print(f"[CONTENT_SERVICE] Pool pop failed for {skill_id}: {e}")
                # Fall through to existing AI/Khan logic on pool miss or error

            # --- AI-generated question path ---
            if self.use_ai_questions and self.ai_provider:
                ai_result = self.ai_provider.get_question_for_skill(
                    skill_id=skill_id,
                    skill_name=skill.name,
                    target_difficulty=target_difficulty,
                    grade_level=skill.grade_level.name,
                    age=user_profile.age if user_profile else 7,
                    exclude_question_ids=answered_question_ids,
                    user_id=student_id,
                    fast_mode=fast_mode,
                    subject=self.subject or "",
                )
                if ai_result:
                    q_id = ai_result["dash_metadata"]["dash_question_id"]
                    log_print(f"[QUESTION_SELECTED] Q:{q_id} | Skill:{skill.name} | "
                              f"Difficulty:{target_difficulty:.2f} (AI_GENERATED, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                    return Question(
                        question_id=q_id,
                        skill_ids=[skill_id],
                        content="",
                        difficulty=ai_result["dash_metadata"]["difficulty"],
                        expected_time_seconds=60.0,
                    )
                continue  # Try next skill if AI provider returned nothing

            # --- Khan question bank path (original) ---
            # Allow some flexibility: ±0.2 around target difficulty
            min_difficulty = max(0.0, target_difficulty - 0.2)
            max_difficulty = target_difficulty + 0.2

            # Get question IDs for this skill from index (fast lookup)
            skill_question_ids = self.skill_question_index.get(skill_id, [])
            if not skill_question_ids:
                continue  # Skip silently if no questions for this skill

            # Filter out answered questions
            candidate_ids = [qid for qid in skill_question_ids if qid not in answered_question_ids]
            if not candidate_ids:
                continue  # Skip silently if all questions already answered

            # Create Question objects on-demand from index
            all_candidates = []
            for qid in candidate_ids:
                question = self._get_or_create_question(qid)
                if question:
                    all_candidates.append(question)

            if not all_candidates:
                continue  # Skip silently

            # Filter by difficulty range (adaptive selection)
            filtered_candidates = [
                q for q in all_candidates
                if min_difficulty <= q.difficulty <= max_difficulty
            ]

            # If we have questions in the target difficulty range, use them
            if filtered_candidates:
                # Sort by how close they are to target difficulty, then return the best match
                filtered_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
                selected = filtered_candidates[0]
                log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                      f"Difficulty:{selected.difficulty:.2f} (target:{target_difficulty:.2f}, adaptive_base:{adaptive_base:.2f}, global_adj:{global_difficulty_adjustment:+.2f})")
                return selected

            # If no questions in target range, use closest match from all candidates
            # This ensures we always return a question if available
            all_candidates.sort(key=lambda q: abs(q.difficulty - target_difficulty))
            selected = all_candidates[0]
            log_print(f"[QUESTION_SELECTED] Q:{selected.question_id} | Skill:{skill.name} | "
                      f"Difficulty:{selected.difficulty:.2f} (FALLBACK, target:{target_difficulty:.2f})")
            return selected

        # No unanswered questions found
        return None
    
    def get_dynamic_student_performance(self, user_id: str) -> Dict[str, Any]:
        """
        Get student performance mapped to CURRENT skill structure.
        Maps historical question attempts to current Khan Academy hierarchy.
        This is future-proof - works even when questions_db is updated.
        """
        from datetime import datetime
        
        # 1. Get all historical question attempts for this student
        attempts = list(self.mongo.question_attempts.find({
            "user_id": user_id
        }).sort("timestamp", -1))
        
        if not attempts:
            # No attempts yet - return empty performance with current skills
            return {
                "overall_grade": "N/A",
                "overall_mastery": 0.0,
                "skills": [],
                "total_questions": 0,
                "updated_at": datetime.now().isoformat()
            }
        
        # 2. Map attempts to current skills
        skill_performance: Dict[str, Dict[str, Any]] = {}

        for attempt in attempts:
            question_id = attempt.get("question_id")
            
            # Find which current skill this question belongs to
            question_doc = self.mongo.questions.find_one({"question_id": question_id})
            
            if not question_doc:
                continue  # Question no longer exists in current DB
                
            # Get the lesson, then unit (skill)
            lesson_id = question_doc.get("lesson_id")
            if not lesson_id:
                continue
                
            lesson = self.mongo.lessons.find_one({"lesson_id": lesson_id})
            if not lesson:
                continue
                
            unit_id = lesson.get("unit_id")
            if not unit_id:
                continue
                
            # Find the skill in current DASH tree
            skill_node = self.skills.get(unit_id)
            
            if not skill_node:
                continue  # Skill no longer in current hierarchy
                
            # Initialize skill performance tracking
            if skill_node.skill_id not in skill_performance:
                skill_performance[skill_node.skill_id] = {
                    "skill_name": skill_node.name,
                    "subject": getattr(skill_node, 'subject', 'Unknown'),
                    "grade_level": skill_node.grade_level.name if hasattr(skill_node.grade_level, 'name') else str(skill_node.grade_level),
                    "correct": 0,
                    "total": 0,
                    "recent_attempts": []
                }
            
            # Update performance
            perf = skill_performance[skill_node.skill_id]
            perf["total"] += 1
            if attempt.get("is_correct"):
                perf["correct"] += 1
            
            perf["recent_attempts"].append({
                "timestamp": attempt.get("timestamp"),
                "correct": attempt.get("is_correct"),
                "question_id": question_id
            })
        
        # 3. Calculate mastery levels
        skills_with_mastery = []
        for skill_id, perf in skill_performance.items():
            mastery = (perf["correct"] / perf["total"] * 100) if perf["total"] > 0 else 0
            
            skills_with_mastery.append({
                "skill_id": skill_id,
                "skill_name": perf["skill_name"],
                "subject": perf["subject"],
                "grade_level": perf["grade_level"],
                "mastery": round(mastery, 1),
                "questions_answered": perf["total"],
                "questions_correct": perf["correct"],
                "last_attempt": perf["recent_attempts"][0]["timestamp"] if perf["recent_attempts"] else None
            })
        
        # 4. Sort by subject and grade level
        skills_with_mastery.sort(key=lambda x: (x["subject"], x["grade_level"], x["skill_name"]))
        
        # 5. Calculate overall grade
        if skills_with_mastery:
            total_mastery = sum(s["mastery"] for s in skills_with_mastery)
            avg_mastery = total_mastery / len(skills_with_mastery)
            
            # Map to letter grade
            if avg_mastery >= 90:
                letter_grade = "A"
            elif avg_mastery >= 80:
                letter_grade = "B"
            elif avg_mastery >= 70:
                letter_grade = "C"
            elif avg_mastery >= 60:
                letter_grade = "D"
            else:
                letter_grade = "F"
        else:
            letter_grade = "N/A"
            avg_mastery = 0.0
        
        return {
            "overall_grade": letter_grade,
            "overall_mastery": round(avg_mastery, 1),
            "skills": skills_with_mastery,
            "total_questions": sum(s["questions_answered"] for s in skills_with_mastery),
            "updated_at": datetime.now().isoformat()
        }
