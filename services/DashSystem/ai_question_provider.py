"""
AI Question Provider — bridges DASH adaptive logic with Gemini question generation.

Replaces the Khan question bank lookup with AI-generated questions while
preserving DASH's full adaptive logic (memory, forgetting curves, prerequisites,
difficulty adjustment).

Three-tier retrieval:
  1. Queue pop   (fast, <50ms)  — pre-generated questions in MongoDB
  2. Reuse       (medium, <100ms) — previously generated questions by lowest used_count
  3. JIT generate (slow, 2-5s)  — call Gemini on-demand

Background threads keep the queue topped up while the student works.
"""

import hashlib
import json
import random
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from shared.logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_FORMATS = [
    "radio_single", "radio_multi", "orderer", "numeric_input", "dropdown",
    "expression", "matcher", "sorter", "definition",
    "categorizer", "number_line", "table",
]
# Default weights (current behavior — fallback when subject can't be detected)
DEFAULT_FORMAT_WEIGHTS = {
    "radio_single": 22, "radio_multi": 7, "orderer": 7,
    "numeric_input": 13, "dropdown": 7, "expression": 13,
    "matcher": 7, "sorter": 4, "definition": 7,
    "categorizer": 5, "number_line": 4, "table": 4,
}

# Formats suitable for fast_mode (assessment JIT): fast to generate, easy to validate
FAST_MODE_FORMATS = ["radio_single", "numeric_input", "dropdown"]
FAST_MODE_WEIGHTS = {
    "default": [50, 30, 20],    # radio, numeric, dropdown
    "math":    [20, 50, 30],    # numeric_input heavy for computation
    "science": [40, 35, 25],    # balanced
    "english": [55, 10, 35],    # radio + dropdown for vocab/comprehension
    "history": [50, 15, 35],    # radio + dropdown for recall
}

# Subject-specific format weights — each subject emphasises its natural question types
SUBJECT_FORMAT_WEIGHTS = {
    "math": {
        "radio_single": 8, "radio_multi": 4, "orderer": 4,
        "numeric_input": 22, "dropdown": 4, "expression": 25,
        "matcher": 4, "sorter": 4, "definition": 8,
        "categorizer": 4, "number_line": 10, "table": 3,
    },
    "science": {
        "radio_single": 17, "radio_multi": 8, "orderer": 8,
        "numeric_input": 12, "dropdown": 8, "expression": 8,
        "matcher": 8, "sorter": 4, "definition": 8,
        "categorizer": 10, "number_line": 3, "table": 6,
    },
    "english": {
        "radio_single": 13, "radio_multi": 4, "orderer": 4,
        "numeric_input": 4, "dropdown": 8, "expression": 4,
        "matcher": 18, "sorter": 8, "definition": 22,
        "categorizer": 10, "number_line": 1, "table": 4,
    },
    "history": {
        "radio_single": 17, "radio_multi": 8, "orderer": 12,
        "numeric_input": 4, "dropdown": 8, "expression": 4,
        "matcher": 8, "sorter": 12, "definition": 8,
        "categorizer": 10, "number_line": 1, "table": 8,
    },
}

# ── Age-based format restrictions ────────────────────────────────────────
# Formats that are inappropriate for young students
AGE_BLOCKED_FORMATS: Dict[int, Set[str]] = {
    7:  {"expression", "matcher", "sorter", "definition", "categorizer"},  # age ≤ 7
    9:  {"expression"},                                                     # age ≤ 9
}

def _filter_formats_by_age(formats: list, weights: list, age: int) -> tuple:
    """Zero out weights for formats that are age-inappropriate, then re-pick."""
    blocked: Set[str] = set()
    for max_age, blocked_fmts in AGE_BLOCKED_FORMATS.items():
        if age <= max_age:
            blocked |= blocked_fmts
    if not blocked:
        return formats, weights
    filtered_w = [w if f not in blocked else 0 for f, w in zip(formats, weights)]
    # If all weights are zero (shouldn't happen), fall back to radio_single
    if sum(filtered_w) == 0:
        return ["radio_single"], [1]
    # Remove zero-weighted entries so random.choices can't pick them
    filtered_formats = [f for f, w in zip(formats, filtered_w) if w > 0]
    filtered_w = [w for w in filtered_w if w > 0]
    return filtered_formats, filtered_w


# Keywords used to detect subject category from skill_id / subject strings
_SUBJECT_KEYWORDS = {
    "math": [
        "math", "algebra", "geometry", "calculus", "arithmetic", "number",
        "fraction", "decimal", "equation", "trigonometry", "statistics",
        "probability",
    ],
    "science": [
        "science", "biology", "chemistry", "physics", "ecology", "astronomy",
        "earth", "cell", "atom", "molecule", "force", "energy",
        "computer", "programming", "coding", "algorithm", "software",
    ],
    "english": [
        "english", "grammar", "vocabulary", "reading", "writing", "literature",
        "poetry", "language", "spelling", "comprehension", "phonics", "literary",
        "art", "music", "drama", "creative",
    ],
    "history": [
        "history", "geography", "civics", "government", "civilization", "war",
        "revolution", "ancient", "medieval", "colonial", "economics",
        "social", "culture", "society",
    ],
}


def _detect_subject(skill_id: str, subject: str = "") -> str:
    """Detect subject category from skill_id or subject string.

    Returns one of "math", "science", "english", "history", or "default".
    """
    text = f"{skill_id} {subject}".lower()
    for subj, keywords in _SUBJECT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return subj
    return "default"


def _get_format_weights(skill_id: str, subject: str = "") -> list:
    """Get format weights list (parallel to SUPPORTED_FORMATS) for the skill's subject."""
    detected = _detect_subject(skill_id, subject)
    weights_dict = SUBJECT_FORMAT_WEIGHTS.get(detected, DEFAULT_FORMAT_WEIGHTS)
    return [weights_dict[fmt] for fmt in SUPPORTED_FORMATS]


class AIQuestionProvider:
    """Provides AI-generated questions to DASH on demand."""

    QUEUE_TARGET_DEPTH = 5
    QUEUE_REFILL_THRESHOLD = 4
    DIFFICULTY_TOLERANCE = 0.25

    def __init__(self, content_engine, mongo) -> None:
        self.content_engine = content_engine
        self.mongo = mongo
        self.collection = mongo.db["ai_generated_questions"]
        self.queue = mongo.db["ai_question_queue"]
        self._khan_example_cache: Dict[str, str] = {}
        self._validation_failures_col = mongo.db["validation_failures"]
        self._ensure_indexes()

    # ------------------------------------------------------------------
    # Index setup
    # ------------------------------------------------------------------

    def _ensure_indexes(self) -> None:
        """Create MongoDB indexes for efficient lookups."""
        try:
            self.collection.create_index(
                [("subject", 1), ("skill_id", 1), ("difficulty", 1), ("used_count", 1)],
                background=True,
            )
            self.collection.create_index("content_hash", unique=True, background=True)
            self.collection.create_index(
                [("skill_id", 1), ("format", 1)],
                background=True,
            )
            self.queue.create_index(
                [("subject", 1), ("skill_id", 1), ("status", 1), ("difficulty", 1)],
                background=True,
            )
        except Exception as e:
            logger.warning(f"[AI_PROVIDER] Index creation warning (non-fatal): {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_question_for_skill(
        self,
        skill_id: str,
        skill_name: str,
        target_difficulty: float,
        grade_level: str,
        age: int,
        exclude_question_ids: Set[str],
        user_id: str,
        lesson_name: Optional[str] = None,
        fast_mode: bool = False,
        subject: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single AI-generated Perseus question for the given skill + difficulty.

        When fast_mode=True (assessment JIT), skips verification retries for speed.

        Returns a dict with keys: question, answerArea, hints, dash_metadata.
        Returns None only if all tiers fail.
        """
        effective_lesson = lesson_name or skill_name

        # Tier 1: queue pop
        result = self._pop_from_queue(skill_id, target_difficulty, exclude_question_ids, subject=subject)
        if result:
            logger.info(f"[AI_PROVIDER] QUEUE HIT for skill={skill_name} diff={target_difficulty:.2f}")
            self._trigger_background_refill(
                skill_id, skill_name, effective_lesson, target_difficulty, grade_level, age, user_id,
                subject=subject,
            )
            formatted = self._format_output(result, skill_id, skill_name, effective_lesson)
            if formatted:
                return formatted
            # Validation failed — fall through to next tier

        # Tier 2: reuse from collection
        result = self._reuse_existing(skill_id, target_difficulty, exclude_question_ids, subject=subject)
        if result:
            logger.info(f"[AI_PROVIDER] REUSE HIT for skill={skill_name} diff={target_difficulty:.2f}")
            self._trigger_background_refill(
                skill_id, skill_name, effective_lesson, target_difficulty, grade_level, age, user_id,
                subject=subject,
            )
            formatted = self._format_output(result, skill_id, skill_name, effective_lesson)
            if formatted:
                return formatted
            # Validation failed — fall through to next tier

        # Tier 3: generate just-in-time
        result = self._generate_jit(
            skill_id, skill_name, effective_lesson, target_difficulty, grade_level, age, user_id,
            fast_mode=fast_mode,
            subject=subject,
        )
        if result:
            logger.info(f"[AI_PROVIDER] JIT GENERATED for skill={skill_name} diff={target_difficulty:.2f}")
            self._trigger_background_refill(
                skill_id, skill_name, effective_lesson, target_difficulty, grade_level, age, user_id,
                subject=subject,
            )
            formatted = self._format_output(result, skill_id, skill_name, effective_lesson)
            if formatted:
                return formatted

        logger.warning(f"[AI_PROVIDER] ALL TIERS FAILED for skill={skill_name}")
        return None

    def warm_cache_for_skills(
        self,
        skill_ids: List[str],
        skills_dict: Dict,
        age: int,
        user_id: str,
        subject: str = "",
    ) -> None:
        """Pre-warm queue for a set of skills (call after user login)."""

        def _bg_warm():
            for skill_id in skill_ids[:10]:  # Cap at 10 skills
                skill = skills_dict.get(skill_id)
                if not skill:
                    continue
                try:
                    self.refill_queue(
                        skill_id=skill_id,
                        skill_name=skill.name,
                        lesson_name=skill.name,
                        target_difficulty=skill.difficulty,
                        grade_level=skill.grade_level.name,
                        age=age,
                        user_id=user_id,
                        count=3,
                        subject=subject,
                    )
                except Exception as e:
                    logger.warning(f"[AI_PROVIDER] Warm cache failed for {skill_id}: {e}")

        threading.Thread(target=_bg_warm, daemon=True).start()

    # ------------------------------------------------------------------
    # Tier 1: Queue
    # ------------------------------------------------------------------

    def _pop_from_queue(
        self,
        skill_id: str,
        target_difficulty: float,
        exclude_ids: Set[str],
        subject: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Atomically pop a ready question from the queue."""
        min_diff = max(0.0, target_difficulty - self.DIFFICULTY_TOLERANCE)
        max_diff = min(1.0, target_difficulty + self.DIFFICULTY_TOLERANCE)

        query: Dict[str, Any] = {
            "skill_id": skill_id,
            "status": "ready",
            "difficulty": {"$gte": min_diff, "$lte": max_diff},
        }
        if subject:
            query["subject"] = subject
        if exclude_ids:
            query["question_id"] = {"$nin": list(exclude_ids)}

        queue_item = self.queue.find_one_and_update(
            query,
            {"$set": {"status": "served", "served_at": datetime.utcnow()}},
            sort=[("created_at", 1)],
        )
        # NOTE: Untagged fallback removed — serving old math questions for
        # non-math subjects caused wrong-subject content (Bug #21).
        if not queue_item:
            return None

        doc = self.collection.find_one({"question_id": queue_item["question_id"]})
        if not doc:
            return None

        # Increment used_count
        self.collection.update_one(
            {"_id": doc["_id"]}, {"$inc": {"used_count": 1}, "$set": {"last_served_at": datetime.utcnow()}}
        )
        return doc

    # ------------------------------------------------------------------
    # Tier 2: Reuse
    # ------------------------------------------------------------------

    def _reuse_existing(
        self,
        skill_id: str,
        target_difficulty: float,
        exclude_ids: Set[str],
        subject: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Find a previously generated question sorted by lowest used_count."""
        min_diff = max(0.0, target_difficulty - self.DIFFICULTY_TOLERANCE)
        max_diff = min(1.0, target_difficulty + self.DIFFICULTY_TOLERANCE)

        query: Dict[str, Any] = {
            "skill_id": skill_id,
            "difficulty": {"$gte": min_diff, "$lte": max_diff},
        }
        if subject:
            query["subject"] = subject
        if exclude_ids:
            query["question_id"] = {"$nin": list(exclude_ids)}

        doc = self.collection.find_one(query, sort=[("used_count", 1), ("created_at", -1)])
        # NOTE: Untagged fallback removed — same reason as _pop_from_queue (Bug #21).
        if doc:
            self.collection.update_one(
                {"_id": doc["_id"]}, {"$inc": {"used_count": 1}, "$set": {"last_served_at": datetime.utcnow()}}
            )
        return doc

    # ------------------------------------------------------------------
    # Tier 3: Just-In-Time Generation
    # ------------------------------------------------------------------

    def _generate_jit(
        self,
        skill_id: str,
        skill_name: str,
        lesson_name: str,
        target_difficulty: float,
        grade_level: str,
        age: int,
        user_id: str,
        fast_mode: bool = False,
        subject: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Generate a question on-demand via Gemini."""
        if fast_mode:
            # Fast mode (assessment): pick from 3 fast-to-validate formats
            detected = _detect_subject(skill_id, subject or skill_name)
            fast_weights = list(FAST_MODE_WEIGHTS.get(detected, FAST_MODE_WEIGHTS["default"]))
            fmts, fast_weights = _filter_formats_by_age(FAST_MODE_FORMATS, fast_weights, age)
            fmt = random.choices(fmts, weights=fast_weights, k=1)[0]
        else:
            weights = _get_format_weights(skill_id, subject or skill_name)
            fmts, weights = _filter_formats_by_age(SUPPORTED_FORMATS, weights, age)
            fmt = random.choices(fmts, weights=weights, k=1)[0]
        memory = self.content_engine._memory_context(user_id)
        khan_example = self._get_khan_example(skill_id, fmt)

        perseus_json = self.content_engine.generate_for_skill(
            skill_name=skill_name,
            lesson_name=lesson_name,
            difficulty=target_difficulty,
            age=age,
            fmt=fmt,
            memory=memory,
            khan_example=khan_example,
            fast_mode=fast_mode,
            subject=subject,
        )

        if not perseus_json:
            # Don't use generic fallback — it produces meta-learning garbage
            # ("Which statement is most accurate about X?") that doesn't test
            # subject knowledge. Return None so the caller retries with the
            # next skill or a fresh JIT attempt.
            logger.warning(f"[JIT] Gemini generation failed for skill={skill_id}, fmt={fmt} — returning None (caller will retry)")
            return None

        return self._store_question(
            skill_id=skill_id,
            skill_name=skill_name,
            lesson_name=lesson_name,
            difficulty=target_difficulty,
            grade_level=grade_level,
            age=age,
            fmt=fmt,
            perseus_json=perseus_json,
            source="gemini",
            user_id=user_id,
            subject=subject,
        )

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def _store_question(
        self,
        skill_id: str,
        skill_name: str,
        lesson_name: str,
        difficulty: float,
        grade_level: str,
        age: int,
        fmt: str,
        perseus_json: Dict[str, Any],
        source: str,
        user_id: str,
        subject: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Store a generated question in ai_generated_questions. Returns the doc."""
        content_hash = self._compute_content_hash(perseus_json)
        question_id = f"ai_q_{uuid.uuid4().hex[:12]}"

        doc = {
            "question_id": question_id,
            "skill_id": skill_id,
            "skill_name": skill_name,
            "lesson_id": skill_id,
            "lesson_name": lesson_name,
            "difficulty": difficulty,
            "format": fmt,
            "age_band": self.content_engine._age_band(age),
            "grade_level": grade_level,
            "subject": subject,
            "perseus_json": perseus_json,
            "source": source,
            "content_hash": content_hash,
            "used_count": 1,
            "quality": {
                "topic_grounding_ok": True,
                "verification": perseus_json.pop("_verification", None),
            },
            "created_at": datetime.utcnow(),
            "last_served_at": datetime.utcnow(),
        }

        try:
            self.collection.insert_one(doc)
            return doc
        except Exception as e:
            # DuplicateKeyError on content_hash — question already exists, find and return it
            if "duplicate" in str(e).lower() or "E11000" in str(e):
                existing = self.collection.find_one({"content_hash": content_hash})
                if existing:
                    self.collection.update_one(
                        {"_id": existing["_id"]},
                        {"$inc": {"used_count": 1}, "$set": {"last_served_at": datetime.utcnow()}},
                    )
                    return existing
            logger.error(f"[AI_PROVIDER] Failed to store question: {e}")
            return None

    # ------------------------------------------------------------------
    # Background Queue Refill
    # ------------------------------------------------------------------

    def _trigger_background_refill(
        self,
        skill_id: str,
        skill_name: str,
        lesson_name: str,
        target_difficulty: float,
        grade_level: str,
        age: int,
        user_id: str,
        subject: str = "",
    ) -> None:
        """Start background thread to refill queue if below threshold."""
        refill_filter: dict = {"skill_id": skill_id, "status": "ready"}
        if subject:
            refill_filter["subject"] = subject
        ready = self.queue.count_documents(refill_filter)
        if ready >= self.QUEUE_REFILL_THRESHOLD:
            return

        def _bg_refill():
            try:
                self.refill_queue(
                    skill_id, skill_name, lesson_name, target_difficulty,
                    grade_level, age, user_id,
                    count=self.QUEUE_TARGET_DEPTH - ready,
                    subject=subject,
                )
            except Exception as e:
                logger.warning(f"[AI_PROVIDER] Background refill failed for {skill_id}: {e}")

        threading.Thread(target=_bg_refill, daemon=True).start()

    @staticmethod
    def _spread_difficulties(center: float, count: int) -> list:
        """Generate evenly spread difficulties around the center value."""
        spread = 0.3  # +/-0.15 from center
        step = spread / max(count - 1, 1)
        # Shift the window to avoid clamping at boundaries
        low = center - spread / 2
        high = center + spread / 2
        if low < 0.05:
            low = 0.05
            high = low + spread
        if high > 1.0:
            high = 1.0
            low = high - spread
        low = max(0.05, low)
        return [round(low + i * step, 2) for i in range(count)]

    def refill_queue(
        self,
        skill_id: str,
        skill_name: str,
        lesson_name: str,
        target_difficulty: float,
        grade_level: str,
        age: int,
        user_id: str,
        count: int = 5,
        subject: str = "",
    ) -> int:
        """Parallel queue refill. Called from background thread."""
        memory = self.content_engine._memory_context(user_id)
        existing_ids = set(
            doc["question_id"]
            for doc in self.queue.find(
                {"skill_id": skill_id, "status": {"$in": ["ready", "served"]}},
                {"question_id": 1, "_id": 0},
            )
        )

        difficulties = self._spread_difficulties(target_difficulty, count)

        # Pre-select formats and Khan examples for each slot (age-filtered)
        weights = _get_format_weights(skill_id, subject or skill_name)
        fmts, weights = _filter_formats_by_age(SUPPORTED_FORMATS, weights, age)
        slots = []
        for idx in range(count):
            fmt = random.choices(fmts, weights=weights, k=1)[0]
            khan_example = self._get_khan_example(skill_id, fmt)
            slots.append((difficulties[idx], fmt, khan_example))

        def _generate_one(diff, fmt, khan_example):
            """Generate a single question (runs in parallel thread)."""
            try:
                perseus_json = self.content_engine.generate_for_skill(
                    skill_name=skill_name,
                    lesson_name=lesson_name,
                    difficulty=diff,
                    age=age,
                    fmt=fmt,
                    memory=memory,
                    khan_example=khan_example,
                    subject=subject,
                )
                if not perseus_json:
                    fallback_topic = f"{subject}: {skill_name}" if subject else skill_name
                    fallback = self.content_engine._fallback_question(fallback_topic, age, fmt, diff)
                    perseus_json = fallback["item"]
                    # Repair fallback question (add missing placeholders, field defaults)
                    perseus_json = self.content_engine._repair_item(perseus_json, fmt=fmt)
                    # Validate fallback — don't insert broken questions into queue
                    if not self.content_engine._validate_item(perseus_json, fmt=fmt):
                        logger.warning(f"[AI_PROVIDER] Fallback question failed validation for {skill_name}/{fmt}")
                        return (diff, fmt, None)
                return (diff, fmt, perseus_json)
            except Exception as e:
                logger.warning(f"[AI_PROVIDER] Parallel gen failed for {skill_name}: {e}")
                return (diff, fmt, None)

        # Generate all questions in parallel (5 concurrent Gemini calls)
        results = []
        pool = ThreadPoolExecutor(max_workers=min(count, 5))
        try:
            futures = [pool.submit(_generate_one, d, f, k) for d, f, k in slots]
            for future in as_completed(futures):
                results.append(future.result())
        finally:
            for future in futures:
                future.cancel()
            pool.shutdown(wait=False, cancel_futures=True)

        inserted = 0
        for diff, fmt, perseus_json in results:
            if not perseus_json:
                continue

            doc = self._store_question(
                skill_id=skill_id,
                skill_name=skill_name,
                lesson_name=lesson_name,
                difficulty=diff,
                grade_level=grade_level,
                age=age,
                fmt=fmt,
                perseus_json=perseus_json,
                source="gemini",
                user_id=user_id,
                subject=subject,
            )

            if not doc:
                continue

            if doc["question_id"] in existing_ids:
                continue

            try:
                self.queue.insert_one({
                    "skill_id": skill_id,
                    "question_id": doc["question_id"],
                    "difficulty": diff,
                    "subject": subject,
                    "status": "ready",
                    "created_at": datetime.utcnow(),
                })
                existing_ids.add(doc["question_id"])
                inserted += 1
            except Exception as e:
                logger.warning(f"[AI_PROVIDER] Failed to insert question {doc.get('question_id', 'unknown')} for skill={skill_name}: {e}")
                continue

        logger.info(f"[AI_PROVIDER] Refilled {inserted}/{count} questions for skill={skill_name}")
        return inserted

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    def _format_output(
        self,
        question_doc: Dict[str, Any],
        skill_id: str,
        skill_name: str,
        lesson_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Wrap Perseus JSON with dash_metadata matching frontend expectations.
        Returns None if pre-serve validation fails.
        """
        from pre_serve_validator import validate_pre_serve

        payload = dict(question_doc["perseus_json"])

        # Pre-serve validation gate
        vr = validate_pre_serve(
            payload,
            skill_id=skill_id,
            subject=question_doc.get("subject"),
            db_collection=self._validation_failures_col,
        )
        if not vr.passed:
            logger.warning(
                f"[AI_PROVIDER] Pre-serve REJECT {question_doc.get('question_id')}: {vr.failures}"
            )
            return None

        payload["dash_metadata"] = self._build_dash_metadata(question_doc, skill_id, skill_name, lesson_name)
        return payload

    def _build_dash_metadata(
        self,
        question_doc: Dict[str, Any],
        skill_id: str,
        skill_name: str,
        lesson_name: str,
    ) -> Dict[str, Any]:
        return {
            "dash_question_id": question_doc["question_id"],
            "skill_ids": [skill_id],
            "difficulty": question_doc["difficulty"],
            "expected_time_seconds": 60.0,
            "slug": question_doc["question_id"],
            "skill_names": [skill_name],
            "unit_id": skill_id,
            "lesson_id": question_doc.get("lesson_id", skill_id),
            "exercise_id": "ai_generated",
            "mongodb_id": str(question_doc.get("_id", question_doc["question_id"])),
            "unit_name": skill_name,
            "lesson_name": lesson_name,
            "exercise_name": "AI Generated Practice",
            "ai_generated": True,
            "source": question_doc.get("source", "gemini"),
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_content_hash(perseus_json: Dict[str, Any]) -> str:
        content = json.dumps(
            perseus_json.get("question", {}).get("content", ""),
            sort_keys=True,
            ensure_ascii=True,
        )
        # Include answerArea so different-answer variants aren't treated as same question
        answer_area = json.dumps(
            perseus_json.get("answerArea", {}),
            sort_keys=True,
            ensure_ascii=True,
        )
        widgets = json.dumps(
            perseus_json.get("question", {}).get("widgets", {}),
            sort_keys=True,
            ensure_ascii=True,
        )
        combined = content + widgets + answer_area
        return hashlib.sha256(combined.encode()).hexdigest()

    # Keywords per subject for matching Khan question unit_ids in fallback
    _KHAN_SUBJECT_KEYWORDS = {
        "math": ["math", "algebra", "geometry", "arithmetic", "calcul", "fraction",
                 "decimal", "equation", "trigonometr", "statistic", "number", "counting"],
        "science": ["science", "biology", "chemistry", "physics", "ecolog", "astrono",
                     "earth", "cell", "atom", "molecul", "force", "energy"],
        "english": ["english", "grammar", "vocabular", "reading", "writing", "literatur",
                     "poetry", "language", "spelling", "comprehens", "phonics"],
        "history": ["history", "geography", "civic", "government", "civilization", "war",
                     "revolution", "ancient", "medieval", "colonial", "economic"],
    }

    def _get_khan_example(self, skill_id: str, fmt: str) -> str:
        """
        Fetch a real Khan Academy question as a few-shot example for Gemini.
        Returns a trimmed JSON string suitable for prompt inclusion, or "" if none found.
        Results are cached in memory to avoid repeated MongoDB queries.
        """
        cache_key = f"{skill_id}:{fmt}"
        if cache_key in self._khan_example_cache:
            return self._khan_example_cache[cache_key]

        # Map our format names to the widget type used in Khan Perseus JSON
        fmt_to_widget = {
            "radio_single": "radio",
            "radio_multi": "radio",
            "orderer": "orderer",
            "numeric_input": "numeric-input",
            "dropdown": "dropdown",
            "expression": "expression",
            "matcher": "matcher",
            "sorter": "sorter",
            "definition": "definition",
            "categorizer": "categorizer",
            "number_line": "number-line",
            "table": "table",
        }
        target_widget = fmt_to_widget.get(fmt, "radio")

        try:
            # Try same skill first, then subject-relevant fallback, then any question
            # Detect subject from skill_id to build a subject-filtered fallback
            detected = _detect_subject(skill_id, "")
            subject_regex = None
            if detected != "default":
                kws = self._KHAN_SUBJECT_KEYWORDS.get(detected, [])
                if kws:
                    subject_regex = {"unit_id": {"$regex": "|".join(kws), "$options": "i"}}

            candidates = [{"unit_id": skill_id}]
            if subject_regex:
                candidates.append(subject_regex)
            candidates.append({})  # last resort: any question
            for query in candidates:
                for doc in self.mongo.questions.find(query).limit(20):
                    pj = doc.get("perseus_json", {})
                    widgets = pj.get("question", {}).get("widgets", {})
                    # Check if any widget matches the target type
                    has_target = any(
                        w.get("type") == target_widget for w in widgets.values()
                    )
                    if not has_target:
                        continue

                    # Build a trimmed example: question content + widgets + up to 3 hints
                    example = {
                        "question": {
                            "content": pj.get("question", {}).get("content", ""),
                            "widgets": widgets,
                        },
                        "hints": pj.get("hints", [])[:3],
                    }
                    result = json.dumps(example, ensure_ascii=True)
                    # Keep under 1200 chars to avoid bloating the prompt
                    if len(result) > 1200:
                        example["hints"] = pj.get("hints", [])[:1]
                        result = json.dumps(example, ensure_ascii=True)
                    if len(result) > 1200:
                        result = result[:1200]

                    self._khan_example_cache[cache_key] = result
                    return result

        except Exception as e:
            logger.warning(f"[AI_PROVIDER] Khan example lookup failed (non-fatal): {e}")

        self._khan_example_cache[cache_key] = ""
        return ""
