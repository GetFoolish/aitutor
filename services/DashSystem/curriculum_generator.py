"""
CurriculumGenerator — builds Khan Academy-structured curricula via Gemini.

On a fresh database this produces the full course/unit/lesson/exercise tree
for any subject+region. Generated data is stored in the same questions_db
collections used by the DASH system, tagged with ``source: "ai_generated"``.

Public API
----------
get_or_generate(subject, region)
    Returns immediately with ``{"status": "complete"}`` if cached, or
    ``{"status": "generating", ...}`` and kicks off background generation.

check_status(subject, region)
    Returns current status from the ``generated_curricula`` registry.
"""

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from services.DashSystem.curriculum_prompts import (
    build_courses_prompt,
    build_lessons_prompt,
    build_units_prompt,
)

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Convert a title to a URL-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s)
    return s.strip("-")


class CurriculumGenerator:
    """Generate and cache Khan-style curricula via Gemini."""

    # Gemini call concurrency limits
    _UNIT_WORKERS = 4
    _LESSON_WORKERS = 6

    def __init__(self, mongo_db, content_engine) -> None:
        """
        Parameters
        ----------
        mongo_db : MongoDBManager
            Shared MongoDB connection (has .courses, .units, .lessons, etc.)
        content_engine : ContentV1Engine
            Provides Gemini client + ``_extract_json`` helper.
        """
        self.mongo = mongo_db
        self.engine = content_engine
        self._bg_threads: Dict[str, threading.Thread] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_generate(self, subject: str, region: str) -> Dict[str, Any]:
        """Start or return cached curriculum for *subject*/*region*."""
        key = self._key(subject, region)
        doc = self.mongo.generated_curricula.find_one({"curriculum_id": key})

        if doc and doc.get("status") == "complete":
            return {
                "status": "complete",
                "curriculum_id": key,
                "stats": doc.get("stats", {}),
            }

        if doc and doc.get("status") == "generating":
            # Check for stale lock (> 5 min)
            if doc.get("lock_expires_at") and doc["lock_expires_at"] < datetime.utcnow():
                logger.warning(f"[CURRICULUM] Stale lock detected for {key}, resetting")
                self.mongo.generated_curricula.update_one(
                    {"curriculum_id": key},
                    {"$set": {"status": "pending", "locked_by": None, "lock_expires_at": None}},
                )
            else:
                return {
                    "status": "generating",
                    "curriculum_id": key,
                    "estimated_wait_seconds": 35,
                }

        # Try to acquire lock
        if not self._acquire_lock(key):
            return {
                "status": "generating",
                "curriculum_id": key,
                "estimated_wait_seconds": 35,
            }

        # Launch background generation
        t = threading.Thread(
            target=self._generate_pipeline,
            args=(subject, region, key),
            daemon=True,
        )
        t.start()
        self._bg_threads[key] = t

        return {
            "status": "generating",
            "curriculum_id": key,
            "estimated_wait_seconds": 35,
        }

    def check_status(self, subject: str, region: str) -> Dict[str, Any]:
        """Return current generation status."""
        key = self._key(subject, region)
        doc = self.mongo.generated_curricula.find_one({"curriculum_id": key})
        if not doc:
            return {"status": "not_found", "curriculum_id": key}
        return {
            "status": doc.get("status", "unknown"),
            "curriculum_id": key,
            "stats": doc.get("stats", {}),
        }

    def backfill_empty_courses(self, subject: str, region: str) -> int:
        """Regenerate units+lessons for courses that have 0 units.

        Returns the number of courses backfilled.
        """
        key = self._key(subject, region)
        courses = list(
            self.mongo.courses.find(
                {"source": "ai_generated", "subject": subject, "region": region}
            )
        )
        backfilled = 0
        for course in courses:
            cid = course["course_id"]
            unit_count = self.mongo.units.count_documents({"course_id": cid})
            if unit_count > 0:
                continue

            logger.info(f"[BACKFILL] Course '{course['title']}' has 0 units — regenerating")
            try:
                new_units = self._generate_units_for_single_course(subject, region, key, course)
                if new_units:
                    course_lookup = {course["course_id"]: course}
                    new_lessons, new_exercises = self._generate_lessons_for_units(
                        subject, region, key, new_units, course_lookup
                    )
                    logger.info(
                        f"[BACKFILL] '{course['title']}': "
                        f"{len(new_units)} units, {len(new_lessons)} lessons"
                    )
                    backfilled += 1
            except Exception as exc:
                logger.error(f"[BACKFILL] Failed for '{course['title']}': {exc}")

        return backfilled

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(subject: str, region: str) -> str:
        return f"curr_{subject}_{region}"

    def _acquire_lock(self, key: str) -> bool:
        """Atomic upsert-based distributed lock via MongoDB."""
        now = datetime.utcnow()
        result = self.mongo.generated_curricula.update_one(
            {
                "curriculum_id": key,
                "$or": [
                    {"status": {"$nin": ["generating", "complete"]}},
                    {"status": {"$exists": False}},
                ],
            },
            {
                "$set": {
                    "status": "generating",
                    "locked_by": threading.current_thread().name,
                    "lock_expires_at": now + timedelta(minutes=5),
                    "started_at": now,
                },
                "$setOnInsert": {
                    "curriculum_id": key,
                    "created_at": now,
                    "version": 1,
                },
            },
            upsert=True,
        )
        return result.upserted_id is not None or result.modified_count > 0

    # ------------------------------------------------------------------
    # Generation pipeline (runs in background thread)
    # ------------------------------------------------------------------

    def _generate_pipeline(self, subject: str, region: str, key: str) -> None:
        """Three-step Gemini pipeline: courses -> units -> lessons."""
        start = time.time()
        try:
            logger.info(f"[CURRICULUM] Starting generation for {subject}/{region}")

            # Step 1 — Courses
            courses = self._generate_courses(subject, region, key)
            logger.info(f"[CURRICULUM] Step 1 done: {len(courses)} courses")

            # Step 2 — Units (parallel per course)
            all_units = self._generate_units_parallel(subject, region, key, courses)
            logger.info(f"[CURRICULUM] Step 2 done: {len(all_units)} units")

            # Step 3 — Lessons (parallel per unit)
            all_lessons, all_exercises = self._generate_lessons_parallel(
                subject, region, key, all_units, courses
            )
            logger.info(f"[CURRICULUM] Step 3 done: {len(all_lessons)} lessons, {len(all_exercises)} exercises")

            elapsed = time.time() - start

            # Mark complete
            self.mongo.generated_curricula.update_one(
                {"curriculum_id": key},
                {
                    "$set": {
                        "status": "complete",
                        "subject": subject,
                        "region": region,
                        "locked_by": None,
                        "lock_expires_at": None,
                        "completed_at": datetime.utcnow(),
                        "generation_time_seconds": round(elapsed, 1),
                        "stats": {
                            "courses": len(courses),
                            "units": len(all_units),
                            "lessons": len(all_lessons),
                            "exercises": len(all_exercises),
                        },
                    }
                },
            )
            logger.info(
                f"[CURRICULUM] Generation complete for {subject}/{region} "
                f"in {elapsed:.1f}s — {len(courses)} courses, {len(all_units)} units, "
                f"{len(all_lessons)} lessons"
            )

        except Exception as exc:
            logger.error(f"[CURRICULUM] Generation failed for {subject}/{region}: {exc}")
            import traceback
            traceback.print_exc()
            self.mongo.generated_curricula.update_one(
                {"curriculum_id": key},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(exc),
                        "locked_by": None,
                        "lock_expires_at": None,
                    }
                },
            )

    # ------------------------------------------------------------------
    # Step 1 — Courses
    # ------------------------------------------------------------------

    def _generate_courses(self, subject: str, region: str, key: str) -> List[Dict]:
        prompt = build_courses_prompt(subject, region)
        raw = self._call_gemini(prompt)
        courses_data = self._parse_json_array(raw)

        docs = []
        for i, c in enumerate(courses_data):
            course_id = f"ai_gen_{_slugify(subject)}_{region.lower()}_{c.get('slug', f'course-{i+1}')}"
            doc = {
                "course_id": course_id,
                "title": c["title"],
                "slug": c.get("slug", _slugify(c["title"])),
                "region": region,
                "subject": subject,
                "grade_band": c.get("grade_band", ""),
                "min_grade": c.get("min_grade", i),
                "max_grade": c.get("max_grade", i),
                "order_in_region": c.get("order", i + 1),
                "description": c.get("description", ""),
                "source": "ai_generated",
                "curriculum_id": key,
                "created_at": datetime.utcnow(),
            }
            docs.append(doc)

        if docs:
            self.mongo.courses.insert_many(docs)
        return docs

    # ------------------------------------------------------------------
    # Step 2 — Units (parallel)
    # ------------------------------------------------------------------

    def _generate_units_parallel(
        self, subject: str, region: str, key: str, courses: List[Dict]
    ) -> List[Dict]:
        all_units: List[Dict] = []

        def _gen_units_for_course(course: Dict) -> List[Dict]:
            prompt = build_units_prompt(
                subject, region, course["title"], course.get("grade_band", "")
            )
            raw = self._call_gemini(prompt)
            units_data = self._parse_json_array(raw)

            docs = []
            for j, u in enumerate(units_data):
                unit_id = f"{course['course_id']}_unit_{u.get('slug', f'unit-{j+1}')}"
                doc = {
                    "unit_id": unit_id,
                    "title": u["title"],
                    "slug": u.get("slug", _slugify(u["title"])),
                    "course_id": course["course_id"],
                    "order_in_course": u.get("order", j + 1),
                    "key_concepts": u.get("key_concepts", []),
                    "description": u.get("description", ""),
                    "source": "ai_generated",
                    "curriculum_id": key,
                    "created_at": datetime.utcnow(),
                }
                docs.append(doc)
            return docs

        with ThreadPoolExecutor(max_workers=self._UNIT_WORKERS) as pool:
            futures = {pool.submit(_gen_units_for_course, c): c for c in courses}
            for future in as_completed(futures):
                try:
                    unit_docs = future.result()
                    if unit_docs:
                        self.mongo.units.insert_many(unit_docs)
                        all_units.extend(unit_docs)
                except Exception as exc:
                    course = futures[future]
                    logger.error(f"[CURRICULUM] Unit generation failed for {course['title']}: {exc}")

        return all_units

    # ------------------------------------------------------------------
    # Step 3 — Lessons + Exercises (parallel)
    # ------------------------------------------------------------------

    def _generate_lessons_parallel(
        self,
        subject: str,
        region: str,
        key: str,
        units: List[Dict],
        courses: List[Dict],
    ) -> tuple:
        # Build course lookup for grade_band
        course_lookup = {c["course_id"]: c for c in courses}
        all_lessons: List[Dict] = []
        all_exercises: List[Dict] = []

        def _gen_lessons_for_unit(unit: Dict) -> tuple:
            course = course_lookup.get(unit["course_id"], {})
            prompt = build_lessons_prompt(
                subject,
                region,
                unit["title"],
                course.get("title", ""),
                course.get("grade_band", ""),
            )
            raw = self._call_gemini(prompt)
            lessons_data = self._parse_json_array(raw)

            lesson_docs = []
            exercise_docs = []
            for k, ls in enumerate(lessons_data):
                lesson_id = f"{unit['unit_id']}_lesson_{ls.get('slug', f'lesson-{k+1}')}"
                exercise_id = f"{lesson_id}_exercise"

                lesson_doc = {
                    "lesson_id": lesson_id,
                    "title": ls["title"],
                    "slug": ls.get("slug", _slugify(ls["title"])),
                    "unit_id": unit["unit_id"],
                    "order_in_unit": ls.get("order", k + 1),
                    "description": ls.get("description", ""),
                    "difficulty_hint": ls.get("difficulty_hint", 0.5),
                    "source": "ai_generated",
                    "curriculum_id": key,
                    "created_at": datetime.utcnow(),
                }
                exercise_doc = {
                    "exercise_id": exercise_id,
                    "title": ls.get("exercise_title", f"{ls['title']} Practice"),
                    "lesson_id": lesson_id,
                    "description": ls.get("exercise_description", ""),
                    "source": "ai_generated",
                    "curriculum_id": key,
                    "created_at": datetime.utcnow(),
                }
                lesson_docs.append(lesson_doc)
                exercise_docs.append(exercise_doc)

            return lesson_docs, exercise_docs

        with ThreadPoolExecutor(max_workers=self._LESSON_WORKERS) as pool:
            futures = {pool.submit(_gen_lessons_for_unit, u): u for u in units}
            for future in as_completed(futures):
                try:
                    lesson_docs, exercise_docs = future.result()
                    if lesson_docs:
                        self.mongo.lessons.insert_many(lesson_docs)
                        all_lessons.extend(lesson_docs)
                    if exercise_docs:
                        self.mongo.exercises.insert_many(exercise_docs)
                        all_exercises.extend(exercise_docs)
                except Exception as exc:
                    unit = futures[future]
                    logger.error(f"[CURRICULUM] Lesson generation failed for {unit['title']}: {exc}")

        return all_lessons, all_exercises

    # ------------------------------------------------------------------
    # Single-course helpers (used by backfill)
    # ------------------------------------------------------------------

    def _generate_units_for_single_course(
        self, subject: str, region: str, key: str, course: Dict
    ) -> List[Dict]:
        """Generate units for one course and insert into MongoDB."""
        prompt = build_units_prompt(
            subject, region, course["title"], course.get("grade_band", "")
        )
        raw = self._call_gemini(prompt)
        units_data = self._parse_json_array(raw)

        docs = []
        for j, u in enumerate(units_data):
            unit_id = f"{course['course_id']}_unit_{u.get('slug', f'unit-{j+1}')}"
            doc = {
                "unit_id": unit_id,
                "title": u["title"],
                "slug": u.get("slug", _slugify(u["title"])),
                "course_id": course["course_id"],
                "order_in_course": u.get("order", j + 1),
                "key_concepts": u.get("key_concepts", []),
                "description": u.get("description", ""),
                "source": "ai_generated",
                "curriculum_id": key,
                "created_at": datetime.utcnow(),
            }
            docs.append(doc)

        if docs:
            self.mongo.units.insert_many(docs)
        return docs

    def _generate_lessons_for_units(
        self,
        subject: str,
        region: str,
        key: str,
        units: List[Dict],
        course_lookup: Dict[str, Dict],
    ) -> tuple:
        """Generate lessons+exercises for a list of units (parallel) and insert."""
        all_lessons: List[Dict] = []
        all_exercises: List[Dict] = []

        def _gen(unit: Dict) -> tuple:
            course = course_lookup.get(unit["course_id"], {})
            prompt = build_lessons_prompt(
                subject, region, unit["title"],
                course.get("title", ""), course.get("grade_band", ""),
            )
            raw = self._call_gemini(prompt)
            lessons_data = self._parse_json_array(raw)

            lesson_docs, exercise_docs = [], []
            for k, ls in enumerate(lessons_data):
                lesson_id = f"{unit['unit_id']}_lesson_{ls.get('slug', f'lesson-{k+1}')}"
                exercise_id = f"{lesson_id}_exercise"
                lesson_docs.append({
                    "lesson_id": lesson_id,
                    "title": ls["title"],
                    "slug": ls.get("slug", _slugify(ls["title"])),
                    "unit_id": unit["unit_id"],
                    "order_in_unit": ls.get("order", k + 1),
                    "description": ls.get("description", ""),
                    "difficulty_hint": ls.get("difficulty_hint", 0.5),
                    "source": "ai_generated",
                    "curriculum_id": key,
                    "created_at": datetime.utcnow(),
                })
                exercise_docs.append({
                    "exercise_id": exercise_id,
                    "title": ls.get("exercise_title", f"{ls['title']} Practice"),
                    "lesson_id": lesson_id,
                    "description": ls.get("exercise_description", ""),
                    "source": "ai_generated",
                    "curriculum_id": key,
                    "created_at": datetime.utcnow(),
                })
            return lesson_docs, exercise_docs

        with ThreadPoolExecutor(max_workers=self._LESSON_WORKERS) as pool:
            futures = {pool.submit(_gen, u): u for u in units}
            for future in as_completed(futures):
                try:
                    ldocs, edocs = future.result()
                    if ldocs:
                        self.mongo.lessons.insert_many(ldocs)
                        all_lessons.extend(ldocs)
                    if edocs:
                        self.mongo.exercises.insert_many(edocs)
                        all_exercises.extend(edocs)
                except Exception as exc:
                    unit = futures[future]
                    logger.error(f"[BACKFILL] Lesson gen failed for {unit['title']}: {exc}")

        return all_lessons, all_exercises

    # ------------------------------------------------------------------
    # Gemini helpers
    # ------------------------------------------------------------------

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini and return raw text response."""
        if not self.engine.client:
            raise RuntimeError("Gemini client not available")
        response = self.engine.client.models.generate_content(
            model=self.engine.model,
            contents=prompt,
            config={"temperature": 0.3},
        )
        return response.text

    def _parse_json_array(self, text: str) -> List[Dict]:
        """Extract a JSON array from Gemini's response text.

        Handles common Gemini quirks: markdown fences, trailing commas,
        single-quoted strings, and unescaped control characters.
        """
        import json

        cleaned = text.strip()
        # Strip markdown fences
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        # Find the array
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fix trailing commas before ] or }
            fixed = re.sub(r",\s*([}\]])", r"\1", cleaned)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                # Last resort: remove control chars and retry
                fixed = re.sub(r"[\x00-\x1f]+", " ", fixed)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    logger.error(f"[PARSE_JSON_ARRAY] All 3 parse attempts failed ({len(fixed)} chars): {fixed[:120]}")
                    return []
