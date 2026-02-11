"""
Prompt templates for AI-generated curriculum (Khan Academy structure).

Three-step generation:
  1. Courses — grade-banded course list for a subject/region
  2. Units   — 5-10 units per course with ordering and key concepts
  3. Lessons — 3-6 lessons per unit with exercise descriptions
"""

import json


# ---------------------------------------------------------------------------
# Step 1 — Generate courses for a subject/region
# ---------------------------------------------------------------------------

def build_courses_prompt(subject: str, region: str) -> str:
    """
    Prompt that produces 8-14 courses spanning K-12, grouped by grade band,
    structured like Khan Academy.
    """
    region_standards = {
        "US": "Common Core State Standards and NGSS",
        "UK": "UK National Curriculum",
        "IN": "CBSE / NCERT framework",
        "AU": "Australian Curriculum",
        "CA": "Canadian provincial curricula",
    }
    standards = region_standards.get(region, f"national curriculum standards for {region}")

    return (
        "You are an expert curriculum designer. "
        f"Generate a Khan Academy-style course list for **{subject}** "
        f"targeting students in the **{region}** education system.\n\n"

        f"Use {standards} as the reference framework.\n\n"

        "Return a JSON array of course objects, each with:\n"
        '  - "title": human-readable course name (e.g. "3rd grade Math", "High school Biology")\n'
        '  - "slug": URL-safe identifier (e.g. "3rd-grade-math")\n'
        '  - "grade_band": grade range string (e.g. "K", "1", "2", "3-5", "6-8", "9-12")\n'
        '  - "min_grade": integer, lowest grade (K=0)\n'
        '  - "max_grade": integer, highest grade\n'
        '  - "order": integer, position in sequence (1-based)\n'
        '  - "description": one-sentence summary of what the course covers\n\n'

        "RULES:\n"
        "- Generate 8-14 courses spanning K through 12.\n"
        "- Courses must progress logically from foundational to advanced.\n"
        "- Use grade bands similar to Khan Academy (single grades for K-5, bands for middle/high school).\n"
        "- Course titles must include the grade level AND subject name.\n"
        "- Do NOT include any text outside the JSON array. No markdown fences.\n"
    )


# ---------------------------------------------------------------------------
# Step 2 — Generate units for a single course
# ---------------------------------------------------------------------------

def build_units_prompt(
    subject: str,
    region: str,
    course_title: str,
    grade_band: str,
) -> str:
    """
    Prompt that produces 5-10 units per course with prerequisite ordering.
    """
    return (
        "You are an expert curriculum designer. "
        f"Generate units for the course **{course_title}** "
        f"({subject}, {region} curriculum, grade band {grade_band}).\n\n"

        "A unit is a major topic area (like Khan Academy units). "
        "Each unit will later contain 3-6 lessons.\n\n"

        "Return a JSON array of unit objects, each with:\n"
        '  - "title": unit name (e.g. "Place value", "Fractions", "Linear equations")\n'
        '  - "slug": URL-safe identifier\n'
        '  - "order": integer, sequence within this course (1-based)\n'
        '  - "key_concepts": array of 3-5 core concepts covered\n'
        '  - "description": one-sentence summary\n\n'

        "RULES:\n"
        "- Generate 5-10 units per course.\n"
        "- Units must be ordered so that each builds on the previous.\n"
        "- Concepts must be age-appropriate for the grade band.\n"
        "- Use topic names that match standard curriculum expectations.\n"
        "- Do NOT include any text outside the JSON array. No markdown fences.\n"
    )


# ---------------------------------------------------------------------------
# Step 3 — Generate lessons for a single unit
# ---------------------------------------------------------------------------

def build_lessons_prompt(
    subject: str,
    region: str,
    unit_title: str,
    course_title: str,
    grade_band: str,
) -> str:
    """
    Prompt that produces 3-6 lessons per unit, each with an exercise description.
    """
    return (
        "You are an expert curriculum designer. "
        f"Generate lessons for the unit **{unit_title}** "
        f"in course **{course_title}** "
        f"({subject}, {region} curriculum, grade band {grade_band}).\n\n"

        "A lesson is a specific skill or topic within a unit "
        "(like Khan Academy lessons). Each lesson maps to one exercise set.\n\n"

        "Return a JSON array of lesson objects, each with:\n"
        '  - "title": lesson name (e.g. "Adding within 10", "Solving one-step equations")\n'
        '  - "slug": URL-safe identifier\n'
        '  - "order": integer, sequence within this unit (1-based)\n'
        '  - "exercise_title": name for the practice exercise\n'
        '  - "exercise_description": what the exercise tests (1 sentence)\n'
        '  - "difficulty_hint": float 0.0-1.0, suggested difficulty level\n'
        '  - "description": one-sentence summary of what students learn\n\n'

        "RULES:\n"
        "- Generate 3-6 lessons per unit.\n"
        "- Lessons must be ordered from simpler to more complex.\n"
        "- Each lesson should be narrow enough for a single practice session.\n"
        "- Exercise descriptions should be specific enough for question generation.\n"
        "- Do NOT include any text outside the JSON array. No markdown fences.\n"
    )
