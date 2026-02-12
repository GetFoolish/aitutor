"""
Deterministic, on-demand content generation service.
Seeded Gemini generation -> Verification gate -> Dedup -> Pool storage -> Audit logging.

Uses sync pymongo (matching the rest of the codebase) and the existing ContentV1Engine
for Gemini calls, parsing, repair, and validation.

Pool design:
  - POOL_MIN_PER_BUCKET questions per difficulty bucket (easy/med/hard/synthesis)
  - Near-duplicate rejection via trigram similarity > 0.85
  - Fallback: serve best existing question from pool, never show error
  - Deterministic seed: hash(skill_id + difficulty_bucket + counter)
  - Assessment-verified pool: verified questions preferred for assessments
"""

import hashlib
import json
import logging
import os
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from shared.logging_config import get_logger

logger = get_logger(__name__)

PROMPT_VERSION = "v4.0"  # Increment when prompts change
try:
    POOL_MIN_PER_BUCKET = int(os.getenv("POOL_MIN_PER_BUCKET", "10"))
except (ValueError, TypeError):
    POOL_MIN_PER_BUCKET = 10  # per bucket
DIFFICULTY_BUCKETS = {
    "easy": (0.1, 0.35),
    "medium": (0.35, 0.65),
    "hard": (0.65, 0.92),
    "synthesis": (0.92, 1.0),
}
SIMILARITY_THRESHOLD = 0.85  # Trigram similarity rejection threshold
MAX_VERIFY_ATTEMPTS = 2  # Retry with stricter prompt up to 2x, then reject


class ContentGenerationService:
    """Deterministic content generation with verification, dedup, and audit.

    All methods are synchronous (matching the pymongo driver used throughout the project).
    Long-running Gemini calls are wrapped in ThreadPoolExecutor just like ContentV1Engine.
    """

    def __init__(self, db_ai_tutor, db_questions, content_engine=None, verifier=None):
        """
        Args:
            db_ai_tutor:    pymongo Database for ai_tutor (e.g. mongo_db.db)
            db_questions:   pymongo Database for questions_db (e.g. mongo_db.questions_db)
            content_engine: ContentV1Engine instance (owns the Gemini client)
            verifier:       DeterministicVerifier instance
        """
        self.pool_col = db_ai_tutor["content_pool"]
        self.audit_col = db_ai_tutor["generation_audit_log"]
        self.questions_col = db_questions["ai_generated_questions"]
        self.units_col = db_questions["units"]  # For skill name lookups
        self.content_engine = content_engine
        self.verifier = verifier
        self._skill_name_cache: Dict[str, str] = {}
        self.khan_questions_col = db_questions["questions"]
        self._khan_example_cache: Dict[str, str] = {}
        self._format_history: Dict[str, List[str]] = {}  # skill_id -> last N formats served
        self._ensure_indexes()

    # ------------------------------------------------------------------
    # Index setup
    # ------------------------------------------------------------------

    def _ensure_indexes(self):
        """Create MongoDB indexes for pool and audit collections."""
        try:
            self.pool_col.create_index(
                [("subject", 1), ("skill_id", 1), ("difficulty_bucket", 1)], background=True
            )
            self.pool_col.create_index("content_hash", unique=True, background=True)
            self.pool_col.create_index(
                [("skill_id", 1), ("quality_score", -1)], background=True
            )
            self.audit_col.create_index("skill_id", background=True)
            self.audit_col.create_index("timestamp", background=True)
        except Exception as e:
            logger.warning(f"[CONTENT_GEN] Index creation warning (non-fatal): {e}")

    # ------------------------------------------------------------------
    # Skill name resolution
    # ------------------------------------------------------------------

    def _resolve_skill_name(self, skill_id: str, skill_name: str = "") -> str:
        """Resolve a human-readable skill name from skill_id if not provided.

        Falls back to querying the units collection in questions_db.
        Results are cached in-memory.
        """
        if skill_name:
            return skill_name
        if skill_id in self._skill_name_cache:
            return self._skill_name_cache[skill_id]
        try:
            unit = self.units_col.find_one(
                {"unit_id": skill_id}, {"title": 1, "_id": 0}
            )
            if unit and unit.get("title"):
                self._skill_name_cache[skill_id] = unit["title"]
                return unit["title"]
        except Exception as e:
            logger.warning(f"[CONTENT_GEN] Skill name lookup failed for {skill_id}: {e}")
        return skill_id  # Last resort: return the ID itself

    # ------------------------------------------------------------------
    # Few-shot Khan example lookup
    # ------------------------------------------------------------------

    _FMT_TO_WIDGET = {
        "radio_single": "radio",
        "radio_multi": "radio",
        "orderer": "orderer",
        "numeric_input": "numeric-input",
        "dropdown": "dropdown",
        "expression": "expression",
        "matcher": "matcher",
        "sorter": "sorter",
        "definition": "definition",
    }

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
        """Fetch a real Khan Academy question as a few-shot example for Gemini.

        Returns a trimmed JSON string suitable for prompt inclusion, or "" if none found.
        Results are cached in memory to avoid repeated MongoDB queries.
        Ported from ai_question_provider.py to enable pool generation with few-shot context.
        """
        cache_key = f"{skill_id}:{fmt}"
        if cache_key in self._khan_example_cache:
            return self._khan_example_cache[cache_key]

        target_widget = self._FMT_TO_WIDGET.get(fmt, "radio")

        try:
            # Detect subject from skill_id for subject-filtered fallback
            from services.DashSystem.ai_question_provider import _detect_subject
            detected = _detect_subject(skill_id, "")
            subject_regex = None
            if detected != "default":
                kws = self._KHAN_SUBJECT_KEYWORDS.get(detected, [])
                if kws:
                    subject_regex = {"unit_id": {"$regex": "|".join(kws), "$options": "i"}}

            # Try same skill first, then subject-relevant fallback, then any question
            queries = [{"unit_id": skill_id}]
            if subject_regex:
                queries.append(subject_regex)
            queries.append({})  # last resort: any question
            for query in queries:
                for doc in self.khan_questions_col.find(query).limit(20):
                    pj = doc.get("perseus_json", {})
                    widgets = pj.get("question", {}).get("widgets", {})
                    has_target = any(
                        w.get("type") == target_widget for w in widgets.values()
                    )
                    if not has_target:
                        continue

                    example = {
                        "question": {
                            "content": pj.get("question", {}).get("content", ""),
                            "widgets": widgets,
                        },
                        "hints": pj.get("hints", [])[:3],
                    }
                    result = json.dumps(example, ensure_ascii=True)
                    if len(result) > 1200:
                        example["hints"] = pj.get("hints", [])[:1]
                        result = json.dumps(example, ensure_ascii=True)
                    if len(result) > 1200:
                        result = result[:1200]

                    self._khan_example_cache[cache_key] = result
                    return result

        except Exception as e:
            logger.warning(f"[CONTENT_GEN] Khan example lookup failed (non-fatal): {e}")

        self._khan_example_cache[cache_key] = ""
        return ""

    # ------------------------------------------------------------------
    # Seed generation
    # ------------------------------------------------------------------

    @staticmethod
    def make_seed(skill_id: str, difficulty_bucket: str, counter: int) -> int:
        """Deterministic seed from skill + difficulty + counter."""
        raw = f"{skill_id}:{difficulty_bucket}:{counter}"
        return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)

    # ------------------------------------------------------------------
    # Near-duplicate detection (trigram similarity)
    # ------------------------------------------------------------------

    @staticmethod
    def _trigrams(text: str) -> set:
        """Extract character trigrams from text."""
        text = text.lower().strip()
        if len(text) < 3:
            return {text} if text else set()  # Empty string → empty set (not {""})
        return {text[i : i + 3] for i in range(len(text) - 2)}

    @staticmethod
    def trigram_similarity(a: str, b: str) -> float:
        """Compute Jaccard trigram similarity between two strings.  Returns 0.0-1.0."""
        tg_a = ContentGenerationService._trigrams(a)
        tg_b = ContentGenerationService._trigrams(b)
        if not tg_a or not tg_b:
            return 0.0
        intersection = tg_a & tg_b
        union = tg_a | tg_b
        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def _extract_question_text(item: dict) -> str:
        """Extract the main question text from a Perseus item for similarity comparison."""
        content = ""
        if "question" in item and "content" in item["question"]:
            content = str(item["question"]["content"] or "")
        # Also include choice text for radio questions
        widgets = item.get("question", {}).get("widgets", {})
        for w in widgets.values():
            if w.get("type") == "radio":
                for choice in w.get("options", {}).get("choices", []):
                    choice_text = choice.get("content") or ""
                    content += " " + str(choice_text)
        return content

    def is_near_duplicate(self, skill_id: str, item: dict) -> bool:
        """Check if question is too similar to existing pool questions for this skill."""
        new_text = self._extract_question_text(item)
        if not new_text or len(new_text.strip()) < 10:
            # Empty/near-empty question text — treat as duplicate to prevent storage
            return True

        existing = self.pool_col.find(
            {"skill_id": skill_id}, {"question_text": 1, "_id": 0}
        ).sort("created_at", -1).limit(100)  # Cap to prevent full-collection scan
        for doc in existing:
            existing_text = doc.get("question_text", "")
            if self.trigram_similarity(new_text, existing_text) > SIMILARITY_THRESHOLD:
                logger.info(f"[CONTENT_GEN] Near-duplicate detected for skill {skill_id}")
                return True
        return False

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate_question(
        self,
        skill_id: str,
        difficulty: float,
        seed: Optional[int] = None,
        skill_name: str = "",
        lesson_name: str = "",
        grade: str = "",
        subject: str = "",
        user_id: str = "",
    ) -> Tuple[Optional[dict], dict]:
        """
        Generate a single question deterministically using the existing Gemini pipeline.

        Returns: (parsed_question_or_None, audit_data)
        """
        # Resolve human-readable name if not provided
        skill_name = self._resolve_skill_name(skill_id, skill_name)

        bucket = self._difficulty_to_bucket(difficulty)
        if seed is None:
            counter = self._get_pool_count(skill_id, bucket)
            seed = self.make_seed(skill_id, bucket, counter)

        audit: Dict[str, Any] = {
            "skill_id": skill_id,
            "difficulty": difficulty,
            "seed": seed,
            "prompt_version": PROMPT_VERSION,
            "model": None,
            "temperature": None,
            "format": None,
            "raw_response_preview": None,
            "parsed_question": None,
            "verification": None,
            "stored": False,
            "rejected_reason": None,
            "timestamp": datetime.utcnow(),
        }

        if not self.content_engine:
            audit["rejected_reason"] = "no_content_engine"
            return None, audit

        if not self.content_engine.client:
            audit["rejected_reason"] = "no_gemini_client"
            return None, audit

        try:
            from services.DashSystem.ai_question_prompts import build_skill_question_prompt
            from services.DashSystem.ai_question_provider import (
                SUPPORTED_FORMATS,
                _detect_subject,
                _get_format_weights,
            )

            # --- Deterministic format selection via seeded RNG ---
            rng = random.Random(seed)

            detected_subject = _detect_subject(skill_id, subject)
            weights = _get_format_weights(skill_id, subject)
            fmt = rng.choices(SUPPORTED_FORMATS, weights=weights, k=1)[0]
            audit["format"] = fmt

            age = self._grade_to_age(grade)
            effective_lesson = lesson_name or skill_name or skill_id
            effective_skill = skill_name or skill_id

            # Memory context (user interests etc.) for personalization
            memory: Dict[str, Any] = {}
            if user_id:
                try:
                    memory = self.content_engine._memory_context(user_id)
                except Exception:
                    pass  # Non-critical

            # Khan example for few-shot prompting (requires provider instance -- optional)
            khan_example = self._get_khan_example(skill_id, fmt)

            # Build the prompt
            prompt_text = build_skill_question_prompt(
                skill_name=effective_skill,
                lesson_name=effective_lesson,
                difficulty=difficulty,
                age=age,
                fmt=fmt,
                memory=memory,
                khan_example=khan_example,
                subject=subject,
            )

            audit["model"] = self.content_engine.model

            # --- Call Gemini using the same pattern as content_v1.py ---
            # Temperature: 0.6 baseline (single attempt here; retries handled by verify loop)
            temperature = 0.6

            def _call_gemini():
                return self.content_engine.client.models.generate_content(
                    model=self.content_engine.model,
                    contents=prompt_text,
                    config={"temperature": temperature},
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                response = future.result(timeout=15)

            raw = response.text or ""
            audit["temperature"] = temperature
            audit["raw_response_preview"] = raw[:3000] if raw else None

            if not raw.strip():
                audit["rejected_reason"] = "empty_gemini_response"
                return None, audit

            # Parse -> Repair -> Validate (using ContentV1Engine methods)
            parsed = self.content_engine._extract_json(raw)
            parsed = self.content_engine._repair_item(parsed, fmt=fmt)

            if not self.content_engine._validate_item(parsed, fmt=fmt):
                audit["rejected_reason"] = "validation_failed"
                return None, audit

            # Subject-content cross-validation: reject off-topic widgets/content
            if not self.content_engine._validate_subject_content(parsed, subject=subject, fmt=fmt):
                audit["rejected_reason"] = f"subject_mismatch:{subject}"
                return None, audit

            audit["parsed_question"] = parsed
            return parsed, audit

        except FutureTimeoutError:
            logger.warning(f"[CONTENT_GEN] Gemini timeout for {skill_id}")
            audit["rejected_reason"] = "gemini_timeout"
            return None, audit
        except json.JSONDecodeError as e:
            logger.warning(f"[CONTENT_GEN] JSON parse error for {skill_id}: {e}")
            audit["rejected_reason"] = f"json_parse_error: {str(e)}"
            return None, audit
        except Exception as e:
            logger.error(f"[CONTENT_GEN] Generation failed for {skill_id}: {e}")
            audit["rejected_reason"] = f"exception: {str(e)}"
            return None, audit

    # ------------------------------------------------------------------
    # Verification gate
    # ------------------------------------------------------------------

    def verify_question(
        self,
        question: dict,
        skill_id: str,
        skill_name: str = "",
        lesson_name: str = "",
        fmt: str = "",
        subject: str = "",
        grade: str = "",
        difficulty: float = 0.5,
    ) -> Tuple[bool, dict]:
        """
        Verify a question using DeterministicVerifier.
        Auto-retry with stricter prompt up to MAX_VERIFY_ATTEMPTS times.

        Returns: (passed: bool, verification_result_dict)
        """
        if not self.verifier:
            return True, {"skipped": True, "reason": "no_verifier"}

        # Resolve human-readable name if not provided
        skill_name = self._resolve_skill_name(skill_id, skill_name)

        age = self._grade_to_age(grade)
        effective_skill = skill_name or skill_id
        effective_lesson = lesson_name or skill_name or skill_id

        # Detect format if not provided
        if not fmt:
            widgets = question.get("question", {}).get("widgets", {})
            first_widget = next(iter(widgets.values()), {}) if widgets else {}
            wtype = first_widget.get("type", "radio")
            _type_to_fmt = {
                "radio": "radio_single",
                "numeric-input": "numeric_input",
                "dropdown": "dropdown",
                "expression": "expression",
                "orderer": "orderer",
                "matcher": "matcher",
                "sorter": "sorter",
                "definition": "definition",
            }
            fmt = _type_to_fmt.get(wtype, "radio_single")
            # Check multipleSelect for radio_multi
            if wtype == "radio" and first_widget.get("options", {}).get("multipleSelect"):
                fmt = "radio_multi"

        last_result = None

        for attempt in range(MAX_VERIFY_ATTEMPTS + 1):
            # DeterministicVerifier.verify() signature:
            # verify(item, skill_name, lesson_name, fmt, age, difficulty)
            result = self.verifier.verify(
                question, effective_skill, effective_lesson, fmt, age, difficulty
            )
            last_result = {
                "passed": result.passed,
                "subject": result.subject,
                "checks_run": result.checks_run,
                "failures": result.failures,
                "confidence": result.confidence,
                "elapsed_ms": result.elapsed_ms,
                "verify_attempts": attempt + 1,
            }

            if result.passed:
                return True, last_result

            if attempt < MAX_VERIFY_ATTEMPTS:
                # Retry: regenerate with corrections injected
                question = self._regenerate_with_corrections(
                    question,
                    skill_id=skill_id,
                    skill_name=effective_skill,
                    lesson_name=effective_lesson,
                    subject=subject,
                    grade=grade,
                    fmt=fmt,
                    failures=result.failures,
                    difficulty=difficulty,
                )
                if question is None:
                    last_result["final"] = "regen_failed"
                    return False, last_result

        last_result["final"] = "rejected"
        return False, last_result

    def _regenerate_with_corrections(
        self,
        original: dict,
        skill_id: str,
        skill_name: str,
        lesson_name: str,
        subject: str,
        grade: str,
        fmt: str,
        failures: list,
        difficulty: float = 0.5,
    ) -> Optional[dict]:
        """Regenerate with verification failures injected as CRITICAL CORRECTIONS.

        Follows the same pattern used in content_v1.py generate_for_skill().
        """
        if not self.content_engine or not self.content_engine.client:
            return None

        try:
            from services.DashSystem.ai_question_prompts import build_skill_question_prompt

            age = self._grade_to_age(grade)
            effective_lesson = lesson_name or skill_name or skill_id
            effective_skill = skill_name or skill_id

            prompt = build_skill_question_prompt(
                skill_name=effective_skill,
                lesson_name=effective_lesson,
                difficulty=difficulty,
                age=age,
                fmt=fmt,
                memory={},
                khan_example=self._get_khan_example(skill_id, fmt),
                subject=subject,
            )

            # Inject failure corrections (same pattern as content_v1.py)
            verification_feedback = "\n".join(f"- {f}" for f in failures)
            prompt += (
                "\n\nCRITICAL CORRECTIONS (your previous attempt had errors):\n"
                + verification_feedback
                + "\nFix these specific issues in your new question."
            )

            # Slightly higher temperature for correction rounds (same as content_v1.py)
            temperature = 0.7

            def _call_gemini():
                return self.content_engine.client.models.generate_content(
                    model=self.content_engine.model,
                    contents=prompt,
                    config={"temperature": temperature},
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                response = future.result(timeout=15)

            raw = response.text or ""
            if not raw.strip():
                return None

            parsed = self.content_engine._extract_json(raw)
            parsed = self.content_engine._repair_item(parsed, fmt=fmt)

            if not self.content_engine._validate_item(parsed, fmt=fmt):
                return None

            # Subject-content cross-validation on retry path too
            if not self.content_engine._validate_subject_content(parsed, subject=subject, fmt=fmt):
                return None

            return parsed

        except Exception as e:
            logger.warning(f"[CONTENT_GEN] Regen with corrections failed for {skill_id}: {e}")
            return None

    # ------------------------------------------------------------------
    # Storage + Dedup
    # ------------------------------------------------------------------

    def store_question(
        self, question: dict, audit: dict, skill_id: str, difficulty: float,
        subject: str = "",
    ) -> bool:
        """
        Store question in the pool after exact and near-duplicate checks.
        Returns True if stored, False if rejected as duplicate.
        """
        # Content hash for exact dedup (same approach as AIQuestionProvider)
        content_str = json.dumps(
            question.get("question", {}).get("content", ""),
            sort_keys=True, ensure_ascii=True,
        )
        widgets_str = json.dumps(
            question.get("question", {}).get("widgets", {}),
            sort_keys=True, ensure_ascii=True,
        )
        content_hash = hashlib.sha256(
            (content_str + widgets_str).encode()
        ).hexdigest()

        # Check exact duplicate
        if self.pool_col.find_one({"content_hash": content_hash}):
            audit["rejected_reason"] = "exact_duplicate"
            audit["stored"] = False
            self._save_audit(audit)
            return False

        # Check near-duplicate
        if self.is_near_duplicate(skill_id, question):
            audit["rejected_reason"] = "near_duplicate"
            audit["stored"] = False
            self._save_audit(audit)
            return False

        # Store in pool
        bucket = self._difficulty_to_bucket(difficulty)
        question_text = self._extract_question_text(question)

        question_id = f"pool_{content_hash[:16]}"
        # Embed question_id in the question_data so it's available at serve time
        if isinstance(question, dict):
            question.setdefault("question_id", question_id)

        # Pool questions pass through the verification gate — mark them as assessment-safe
        verification_passed = (audit.get("verification") or {}).get("passed", False)
        doc = {
            "skill_id": skill_id,
            "question_id": question_id,
            "difficulty": difficulty,
            "difficulty_bucket": bucket,
            "subject": subject,
            "content_hash": content_hash,
            "question_text": question_text,
            "question_data": question,
            "prompt_version": audit.get("prompt_version", PROMPT_VERSION),
            "seed": audit.get("seed"),
            "format": audit.get("format"),
            "quality_score": 0.5,
            "attempt_count": 0,
            "verification": audit.get("verification"),
            "assessment_verified": verification_passed,
            "created_at": datetime.utcnow(),
        }

        try:
            self.pool_col.insert_one(doc)
            audit["stored"] = True
            self._save_audit(audit)
            logger.info(
                f"[CONTENT_GEN] Stored question in pool: skill={skill_id} "
                f"bucket={bucket} hash={content_hash[:12]}"
            )
            return True
        except Exception as e:
            # Handle duplicate key errors from concurrent inserts (unique index on content_hash)
            err_str = str(e)
            if "duplicate key" in err_str.lower() or "E11000" in err_str:
                audit["stored"] = False
                audit["rejected_reason"] = "duplicate_key_constraint"
                self._save_audit(audit)
                logger.info(f"[CONTENT_GEN] Concurrent duplicate for {skill_id}: {content_hash[:12]}")
                return False
            logger.warning(f"[CONTENT_GEN] Store failed for {skill_id}: {e}")
            audit["stored"] = False
            audit["rejected_reason"] = f"store_error: {err_str}"
            self._save_audit(audit)
            return False

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    def ensure_pool(
        self,
        skill_id: str,
        skill_name: str = "",
        lesson_name: str = "",
        grade: str = "",
        subject: str = "",
        user_id: str = "",
    ) -> Dict[str, int]:
        """
        Ensure skill has at least POOL_MIN_PER_BUCKET questions per difficulty bucket.
        Generates missing questions deterministically.

        Returns a dict of {bucket: count_generated} for diagnostics.
        """
        # Resolve human-readable skill name if not provided
        skill_name = self._resolve_skill_name(skill_id, skill_name)
        generated_counts: Dict[str, int] = {}

        for bucket, (low, high) in DIFFICULTY_BUCKETS.items():
            pool_filter: dict = {"skill_id": skill_id, "difficulty_bucket": bucket}
            if subject:
                pool_filter["subject"] = subject
            count = self.pool_col.count_documents(pool_filter)
            needed = POOL_MIN_PER_BUCKET - count
            generated_counts[bucket] = 0

            if needed <= 0:
                continue

            logger.info(
                f"[CONTENT_GEN] Pool {skill_id}/{bucket}: have {count}, need {needed} more"
            )

            for i in range(needed):
                # Deterministic difficulty spread within bucket
                difficulty = low + (high - low) * (i + 0.5) / needed
                seed = self.make_seed(skill_id, bucket, count + i)

                # Generate
                question, audit = self.generate_question(
                    skill_id=skill_id,
                    difficulty=difficulty,
                    seed=seed,
                    skill_name=skill_name,
                    lesson_name=lesson_name,
                    grade=grade,
                    subject=subject,
                    user_id=user_id,
                )

                if question is None:
                    logger.warning(
                        f"[CONTENT_GEN] Generation failed for {skill_id}/{bucket}/{i}"
                    )
                    self._save_audit(audit)
                    continue

                # Verify
                fmt = audit.get("format", "")
                passed, verify_result = self.verify_question(
                    question,
                    skill_id,
                    skill_name=skill_name,
                    lesson_name=lesson_name,
                    fmt=fmt,
                    subject=subject,
                    grade=grade,
                    difficulty=difficulty,
                )
                audit["verification"] = verify_result

                if not passed:
                    logger.warning(
                        f"[CONTENT_GEN] Verification rejected {skill_id}/{bucket}/{i}"
                    )
                    audit["rejected_reason"] = "verification_failed"
                    self._save_audit(audit)
                    continue

                # Store (includes dedup checks)
                stored = self.store_question(question, audit, skill_id, difficulty, subject=subject)
                if stored:
                    generated_counts[bucket] += 1

        return generated_counts

    def pop_question(self, skill_id: str, difficulty: float,
                     exclude_ids: Optional[set] = None,
                     subject: str = "") -> Optional[dict]:
        """
        Get the best question from the pool for this skill + difficulty.
        Falls back to any existing question if exact bucket is empty.

        Args:
            exclude_ids: question IDs to skip (already seen by the student).
            subject: filter by subject to prevent cross-subject contamination.

        Design goal: NEVER return None if any question exists for the skill.
        Returns None only if the pool and all fallback collections are truly empty,
        in which case the caller should trigger ensure_pool().
        """
        bucket = self._difficulty_to_bucket(difficulty)

        # Build base filter, optionally excluding already-seen questions
        base_filter: dict = {"skill_id": skill_id}
        if subject:
            base_filter["subject"] = subject
        if exclude_ids:
            base_filter["question_id"] = {"$nin": list(exclude_ids)}

        def _serve(doc: dict) -> dict:
            """Mark doc as served and return question_data with question_id."""
            self.pool_col.update_one(
                {"_id": doc["_id"]}, {"$inc": {"attempt_count": 1}}
            )
            qd = dict(doc.get("question_data") or {})  # Copy to avoid mutating cached doc
            # Ensure question_id is present (backfill for older docs)
            q_id = doc.get("question_id") or f"pool_{doc.get('content_hash', '')[:16]}"
            if isinstance(qd, dict):
                qd.setdefault("question_id", q_id)
            # Track format for diversity enforcement
            fmt = doc.get("format", "unknown")
            history = self._format_history.setdefault(skill_id, [])
            history.append(fmt)
            if len(history) > 10:
                history.pop(0)
            return qd

        # Format diversity: check if last 3 serves were the same format
        recent = self._format_history.get(skill_id, [])
        overused_fmt = None
        if len(recent) >= 3 and len(set(recent[-3:])) == 1:
            overused_fmt = recent[-1]

        # Try exact bucket first, sorted by quality (best first), then least served
        exact_filter = {**base_filter, "difficulty_bucket": bucket}

        # If format is overused, try a different format first
        if overused_fmt:
            diverse_filter = {**exact_filter, "format": {"$ne": overused_fmt}}
            doc = self.pool_col.find_one(
                diverse_filter,
                sort=[("quality_score", -1), ("attempt_count", 1)],
            )
            if doc:
                return _serve(doc)

        doc = self.pool_col.find_one(
            exact_filter,
            sort=[("quality_score", -1), ("attempt_count", 1)],
        )

        if doc:
            return _serve(doc)

        # Fallback: any bucket for this skill
        doc = self.pool_col.find_one(
            base_filter,
            sort=[("quality_score", -1), ("attempt_count", 1)],
        )

        if doc:
            return _serve(doc)

        # Fallback: try untagged (subject=None) pool questions for this skill
        if subject:
            untagged_filter: dict = {"skill_id": skill_id, "subject": {"$in": [None, ""]}}
            if exclude_ids:
                untagged_filter["question_id"] = {"$nin": list(exclude_ids)}
            doc = self.pool_col.find_one(
                untagged_filter,
                sort=[("quality_score", -1), ("attempt_count", 1)],
            )
            if doc:
                return _serve(doc)

        # Last resort: check ai_generated_questions collection (legacy pool)
        legacy_filter: dict = {"skill_id": skill_id}
        if subject:
            legacy_filter["subject"] = subject
        if exclude_ids:
            legacy_filter["question_id"] = {"$nin": list(exclude_ids)}
        doc = self.questions_col.find_one(
            legacy_filter,
            sort=[("created_at", -1)],
        )
        if doc:
            # Return perseus_json or item depending on how it was stored
            q = doc.get("perseus_json") or doc.get("question_data") or doc.get("item")
            # Strip any MongoDB ObjectIds that would crash FastAPI serialization
            if isinstance(q, dict):
                q = dict(q)  # Copy to avoid mutating cached doc
                q.pop("_id", None)
                # Backfill question_id for analytics tracking
                if "question_id" not in q and "question_id" in doc:
                    q["question_id"] = doc["question_id"]
            elif q is not None:
                logger.warning(f"[CONTENT_GEN] Legacy question has non-dict data: {type(q)}")
                q = None  # Reject non-dict data rather than passing garbage downstream
            return q

        # Last-last resort: untagged legacy questions
        if subject:
            legacy_untagged: dict = {"skill_id": skill_id, "subject": {"$in": [None, ""]}}
            if exclude_ids:
                legacy_untagged["question_id"] = {"$nin": list(exclude_ids)}
            doc = self.questions_col.find_one(
                legacy_untagged,
                sort=[("created_at", -1)],
            )
            if doc:
                q = doc.get("perseus_json") or doc.get("question_data") or doc.get("item")
                if isinstance(q, dict):
                    q = dict(q)  # Copy to avoid mutating cached doc
                    q.pop("_id", None)
                    if "question_id" not in q and "question_id" in doc:
                        q["question_id"] = doc["question_id"]
                elif q is not None:
                    logger.warning(f"[CONTENT_GEN] Legacy untagged question has non-dict data: {type(q)}")
                    q = None
                return q

        return None  # Truly empty -- caller should trigger ensure_pool

    def pop_assessment_question(
        self, skill_id: str, difficulty: float,
        exclude_ids: Optional[set] = None,
        subject: str = "",
    ) -> Optional[dict]:
        """Pop a verified question suitable for assessment.

        Prefers questions tagged assessment_verified=True (passed verification).
        Falls back to regular pop_question if none available.
        """
        bucket = self._difficulty_to_bucket(difficulty)

        base_filter: dict = {"skill_id": skill_id, "assessment_verified": True}
        if subject:
            base_filter["subject"] = subject
        if exclude_ids:
            base_filter["question_id"] = {"$nin": list(exclude_ids)}

        def _serve(doc: dict) -> dict:
            self.pool_col.update_one(
                {"_id": doc["_id"]}, {"$inc": {"attempt_count": 1}}
            )
            qd = doc.get("question_data") or {}
            q_id = doc.get("question_id") or f"pool_{doc.get('content_hash', '')[:16]}"
            if isinstance(qd, dict):
                qd = dict(qd)  # Copy to avoid mutating cached MongoDB doc
                qd.setdefault("question_id", q_id)
            return qd

        # Try exact bucket (verified only)
        doc = self.pool_col.find_one(
            {**base_filter, "difficulty_bucket": bucket},
            sort=[("quality_score", -1), ("attempt_count", 1)],
        )
        if doc:
            return _serve(doc)

        # Any bucket (verified only)
        doc = self.pool_col.find_one(
            base_filter,
            sort=[("quality_score", -1), ("attempt_count", 1)],
        )
        if doc:
            return _serve(doc)

        # Fall back to regular pop (includes unverified/legacy)
        return self.pop_question(skill_id, difficulty, exclude_ids, subject=subject)

    def on_skill_unlock(
        self,
        student_id: str,
        skill_id: str,
        skill_name: str = "",
        lesson_name: str = "",
        grade: str = "",
        subject: str = "",
        user_id: str = "",
    ) -> Dict[str, int]:
        """Triggered when a student unlocks a new skill.  Ensures pool is ready."""
        logger.info(f"[CONTENT_GEN] Skill unlock: {student_id} -> {skill_id}")
        return self.ensure_pool(
            skill_id,
            skill_name=skill_name,
            lesson_name=lesson_name,
            grade=grade,
            subject=subject,
            user_id=user_id,
        )

    def update_quality_score(
        self, content_hash: str, is_correct: bool, response_time_ms: int
    ):
        """Update pool question quality score based on student outcome.

        Simple EMA: quality_score = 0.8 * old + 0.2 * signal
        Signal: 1.0 if correct with reasonable time, 0.3 if wrong (could be hard, not bad).
        """
        doc = self.pool_col.find_one({"content_hash": content_hash})
        if not doc:
            return

        old_score = doc.get("quality_score", 0.5)
        signal = 1.0 if is_correct else 0.3
        new_score = round(0.8 * old_score + 0.2 * signal, 4)

        self.pool_col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"quality_score": new_score}},
        )

    # ------------------------------------------------------------------
    # Pool stats
    # ------------------------------------------------------------------

    def get_pool_stats(self, skill_id: str) -> dict:
        """Get pool statistics for a skill."""
        stats: Dict[str, Any] = {}
        for bucket in DIFFICULTY_BUCKETS:
            count = self.pool_col.count_documents(
                {"skill_id": skill_id, "difficulty_bucket": bucket}
            )
            stats[bucket] = count
        stats["total"] = sum(stats[b] for b in DIFFICULTY_BUCKETS)
        stats["ready"] = all(
            stats[b] >= POOL_MIN_PER_BUCKET for b in DIFFICULTY_BUCKETS
        )
        return stats

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _save_audit(self, audit: dict):
        """Save full audit trail entry to MongoDB."""
        try:
            safe_audit = {**audit}

            # Do not store huge raw responses
            raw_preview = safe_audit.get("raw_response_preview")
            if raw_preview and len(str(raw_preview)) > 3000:
                safe_audit["raw_response_preview"] = (
                    str(raw_preview)[:3000] + "...[truncated]"
                )

            # Store a preview of parsed_question, not the full thing (it is in the pool)
            if safe_audit.get("parsed_question"):
                safe_audit["parsed_question_preview"] = str(
                    safe_audit["parsed_question"]
                )[:500]
                del safe_audit["parsed_question"]

            self.audit_col.insert_one(safe_audit)
        except Exception as e:
            logger.error(f"[CONTENT_GEN] Audit save failed: {e}")

    def get_audit_log(
        self, skill_id: Optional[str] = None, limit: int = 50
    ) -> list:
        """Retrieve audit log entries.  Returns list of dicts with _id as string."""
        query: Dict[str, Any] = {}
        if skill_id:
            query["skill_id"] = skill_id

        cursor = self.audit_col.find(query).sort("timestamp", -1).limit(limit)
        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])  # ObjectId -> string for JSON serialization
            results.append(doc)
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _difficulty_to_bucket(difficulty: float) -> str:
        """Map 0.0-1.0 difficulty to bucket name."""
        if difficulty < 0.35:
            return "easy"
        elif difficulty < 0.65:
            return "medium"
        elif difficulty < 0.92:
            return "hard"
        else:
            return "synthesis"

    @staticmethod
    def _grade_to_age(grade: str) -> int:
        """Convert grade string to approximate age.

        Handles formats: K, GRADE_N, GRADE N, Grade N, plain number.
        """
        if not grade:
            return 12  # Default
        grade_upper = grade.upper().strip()
        if grade_upper == "K":
            return 5
        for prefix in ["GRADE_", "GRADE "]:
            if grade_upper.startswith(prefix):
                try:
                    return int(grade_upper[len(prefix):]) + 5
                except ValueError:
                    pass
        # Try plain number
        try:
            return int(grade_upper) + 5
        except ValueError:
            pass
        return 12

    def _get_pool_count(self, skill_id: str, bucket: str) -> int:
        """Get current pool count for seed generation."""
        return self.pool_col.count_documents(
            {"skill_id": skill_id, "difficulty_bucket": bucket}
        )
