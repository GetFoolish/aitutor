#!/usr/bin/env python3
"""
Generate content_pool questions for core subjects (math, science, history, english, music theory).

Selects representative skills spread across grade levels and triggers pool generation
using the ContentGenerationService pipeline (3 hints, 9 formats, verification).
"""
import os, sys, json, time, logging, random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

import pymongo

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

client = pymongo.MongoClient(os.environ["MONGODB_URI"])
qdb = client["questions_db"]
db = client["ai_tutor"]

# Subjects and their curriculum IDs (AI-generated curricula)
CURRICULA = {
    "Science": "curr_Science_US",
    "History": "curr_History_US",
    "English": "curr_English_US",
    "Music Theory": "curr_Music Theory_US",
}

# Khan math courses to draw skills from (not AI-generated)
KHAN_MATH_COURSES = [
    "3rd-grade-illustrative-mathematics",
    "4th-grade-illustrative-mathematics",
    "5th-grade-illustrative-mathematics",
    "3rd-grade-math-eureka-squared-aligned",
    "4th-grade-math-eureka-squared-aligned",
]

# How many skills per subject to seed (spread across grades)
SKILLS_PER_SUBJECT = 15

# Grade levels to ensure coverage
TARGET_GRADES = [
    "kindergarten", "1st-grade", "2nd-grade", "3rd-grade", "4th-grade",
    "5th-grade", "6th-grade", "7th-grade", "8th-grade",
    "9th-grade", "10th-grade", "11th-grade", "12th-grade",
    "high-school", "middle-school",
]


def select_skills(curriculum_id, subject, n=SKILLS_PER_SUBJECT):
    """Select n skills spread across grade levels for a subject."""
    all_exercises = list(qdb["exercises"].find(
        {"curriculum_id": curriculum_id},
        {"exercise_id": 1, "title": 1, "course_id": 1}
    ))

    if not all_exercises:
        logger.warning(f"No exercises found for {subject} ({curriculum_id})")
        return []

    # Group by grade (extracted from exercise_id)
    by_grade = {}
    for ex in all_exercises:
        eid = ex["exercise_id"]
        grade = "other"
        for g in TARGET_GRADES:
            if g in eid:
                grade = g
                break
        by_grade.setdefault(grade, []).append(ex)

    # Select 1-2 from each grade, prioritizing coverage
    selected = []
    grades = sorted(by_grade.keys())

    # First pass: 1 from each grade
    for grade in grades:
        if len(selected) >= n:
            break
        pool = by_grade[grade]
        # Skip already-in-content-pool skills
        pool = [e for e in pool if db["content_pool"].count_documents({"skill_id": e["exercise_id"]}) == 0]
        if pool:
            chosen = random.choice(pool)
            selected.append(chosen)

    # Second pass: fill remaining from underrepresented grades
    if len(selected) < n:
        remaining = []
        for grade in grades:
            pool = by_grade[grade]
            pool = [e for e in pool if e not in selected and db["content_pool"].count_documents({"skill_id": e["exercise_id"]}) == 0]
            remaining.extend(pool)
        random.shuffle(remaining)
        for ex in remaining:
            if len(selected) >= n:
                break
            selected.append(ex)

    return selected


def generate_pool_for_skill(skill_id, skill_name, subject, grade):
    """Call the content_generation_service to fill the pool for a skill."""
    # Import locally to avoid circular imports
    from services.DashSystem.content_generation_service import ContentGenerationService

    service = ContentGenerationService.__instances.get("default") if hasattr(ContentGenerationService, '__instances') else None

    if not service:
        # Create a new instance
        service = ContentGenerationService()

    result = service.ensure_pool(
        skill_id=skill_id,
        skill_name=skill_name,
        grade=grade,
        subject=subject,
    )
    return result


def main():
    logger.info("=" * 70)
    logger.info("CONTENT POOL GENERATION FOR CORE SUBJECTS")
    logger.info("=" * 70)

    total_generated = 0
    total_skills = 0

    # Initialize ContentGenerationService with proper DB connections
    from services.DashSystem.content_generation_service import ContentGenerationService
    from services.DashSystem.content_v1 import ContentV1Engine

    content_engine = ContentV1Engine()
    service = ContentGenerationService(
        db_ai_tutor=db,
        db_questions=qdb,
        content_engine=content_engine,
    )

    # ---- Math (Khan Academy skills) ----
    logger.info(f"\n{'='*50}")
    logger.info(f"Subject: Math (Khan Academy)")
    logger.info(f"{'='*50}")

    math_exercises = []
    for course_slug in KHAN_MATH_COURSES:
        course = qdb["courses"].find_one({"slug": course_slug})
        if course:
            exs = list(qdb["exercises"].find(
                {"course_id": course["course_id"]},
                {"exercise_id": 1, "title": 1, "course_id": 1}
            ).limit(5))
            math_exercises.extend(exs)

    # Filter out skills already in content_pool
    math_exercises = [e for e in math_exercises if db["content_pool"].count_documents({"skill_id": e["exercise_id"]}) == 0]
    random.shuffle(math_exercises)
    math_skills = math_exercises[:SKILLS_PER_SUBJECT]
    logger.info(f"Selected {len(math_skills)} math skills")

    for i, skill in enumerate(math_skills):
        skill_id = skill["exercise_id"]
        skill_name = skill.get("title", skill_id)
        # Infer grade from course slug
        grade = ""
        for cs in KHAN_MATH_COURSES:
            course = qdb["courses"].find_one({"slug": cs})
            if course and skill.get("course_id") == course["course_id"]:
                if "3rd" in cs: grade = "3rd Grade"
                elif "4th" in cs: grade = "4th Grade"
                elif "5th" in cs: grade = "5th Grade"
                break

        logger.info(f"\n  [{i+1}/{len(math_skills)}] {skill_name} (grade={grade})")
        try:
            t0 = time.time()
            result = service.ensure_pool(
                skill_id=skill_id,
                skill_name=skill_name,
                grade=grade,
                subject="Math",
            )
            elapsed = time.time() - t0
            gen_count = sum(result.values())
            total_generated += gen_count
            total_skills += 1
            logger.info(f"    Generated {gen_count} questions in {elapsed:.1f}s: {result}")
        except Exception as e:
            logger.error(f"    FAILED: {e}")

    # ---- AI-generated curricula subjects ----
    for subject, curriculum_id in CURRICULA.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"Subject: {subject}")
        logger.info(f"{'='*50}")

        skills = select_skills(curriculum_id, subject)
        logger.info(f"Selected {len(skills)} skills for {subject}")

        for i, skill in enumerate(skills):
            skill_id = skill["exercise_id"]
            skill_name = skill.get("title", skill_id)

            # Extract grade from skill_id
            grade = ""
            for g in TARGET_GRADES:
                if g in skill_id:
                    grade = g.replace("-", " ").title()
                    break

            logger.info(f"\n  [{i+1}/{len(skills)}] {skill_name} (grade={grade})")
            logger.info(f"    skill_id: {skill_id[:60]}")

            try:
                t0 = time.time()
                result = service.ensure_pool(
                    skill_id=skill_id,
                    skill_name=skill_name,
                    grade=grade,
                    subject=subject,
                )
                elapsed = time.time() - t0
                gen_count = sum(result.values())
                total_generated += gen_count
                total_skills += 1
                logger.info(f"    Generated {gen_count} questions in {elapsed:.1f}s: {result}")
            except Exception as e:
                logger.error(f"    FAILED: {e}")

    logger.info(f"\n{'='*70}")
    logger.info(f"DONE. {total_skills} skills processed, {total_generated} questions generated")
    logger.info(f"{'='*70}")

    # Print final stats
    pool_total = db["content_pool"].count_documents({"skill_id": {"$ne": "test-skill"}})
    logger.info(f"Total content_pool questions: {pool_total}")

    client.close()


if __name__ == "__main__":
    main()
