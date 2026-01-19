"""
Khan Academy Data Models for DASH Integration
Maps Khan Academy hierarchy to DASH concepts:
- Unit → Skill
- Lesson → Sub-skill
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class GradeLevel(Enum):
    """Grade levels K-12"""
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


@dataclass
class KhanSkill:
    """
    Maps to Khan Academy Unit
    Primary skill tracking unit in DASH system
    """
    skill_id: str  # unit_id from Khan Academy
    name: str  # unit title
    course_id: str  # parent course
    region: str  # e.g., "US", "IN"
    subject: str  # e.g., "Math", "Science"
    grade_level: GradeLevel  # derived from course
    order_in_course: int  # learning sequence
    prerequisites: List[str] = field(default_factory=list)  # previous units in course
    sub_skills: List[str] = field(default_factory=list)  # lesson_ids within this unit
    difficulty: float = 0.5  # average difficulty of exercises
    forgetting_rate: float = 0.1  # memory decay rate


@dataclass
class KhanSubSkill:
    """
    Maps to Khan Academy Lesson
    Granular progress tracking within a skill (unit)
    """
    sub_skill_id: str  # lesson_id from Khan Academy
    name: str  # lesson title
    skill_id: str  # parent unit_id
    course_id: str  # for faster lookups
    order_in_skill: int  # lesson order within unit
    exercise_ids: List[str] = field(default_factory=list)  # exercises in this lesson
    difficulty: float = 0.5  # derived from exercises


def derive_grade_from_course(course_title: str, course_slug: str, order_in_region: int = 0) -> GradeLevel:
    """
    Derive grade level from Khan Academy course title and slug.
    
    Args:
        course_title: Course title (e.g., "2nd grade math")
        course_slug: Course slug (e.g., "cc-2nd-grade-math")
        order_in_region: Course order in region (fallback)
    
    Returns:
        GradeLevel enum value
    """
    title_lower = course_title.lower()
    slug_lower = course_slug.lower()
    
    # Check for kindergarten
    if 'kindergarten' in title_lower or 'pre-k' in title_lower or slug_lower.startswith('early-math'):
        return GradeLevel.K
    
    # Check for explicit grade numbers
    grade_patterns = {
        '1st': GradeLevel.GRADE_1,
        'grade 1': GradeLevel.GRADE_1,
        'class 1': GradeLevel.GRADE_1,
        '2nd': GradeLevel.GRADE_2,
        'grade 2': GradeLevel.GRADE_2,
        'class 2': GradeLevel.GRADE_2,
        '3rd': GradeLevel.GRADE_3,
        'grade 3': GradeLevel.GRADE_3,
        'class 3': GradeLevel.GRADE_3,
        '4th': GradeLevel.GRADE_4,
        'grade 4': GradeLevel.GRADE_4,
        'class 4': GradeLevel.GRADE_4,
        '5th': GradeLevel.GRADE_5,
        'grade 5': GradeLevel.GRADE_5,
        'class 5': GradeLevel.GRADE_5,
        '6th': GradeLevel.GRADE_6,
        'grade 6': GradeLevel.GRADE_6,
        'class 6': GradeLevel.GRADE_6,
        '7th': GradeLevel.GRADE_7,
        'grade 7': GradeLevel.GRADE_7,
        'class 7': GradeLevel.GRADE_7,
        '8th': GradeLevel.GRADE_8,
        'grade 8': GradeLevel.GRADE_8,
        'class 8': GradeLevel.GRADE_8,
    }
    
    for pattern, grade in grade_patterns.items():
        if pattern in title_lower:
            return grade
    
    # High school courses
    if 'algebra 1' in title_lower or (('algebra' in title_lower or 'algebra-basics' in slug_lower) and 'algebra 2' not in title_lower):
        return GradeLevel.GRADE_9
    elif 'geometry' in title_lower:
        return GradeLevel.GRADE_10
    elif 'algebra 2' in title_lower or 'algebra ii' in title_lower:
        return GradeLevel.GRADE_11
    elif 'precalculus' in title_lower or 'pre-calculus' in title_lower or 'trigonometry' in title_lower:
        return GradeLevel.GRADE_12
    
    # Special courses (AP, SAT, etc.) - map to high school
    if any(x in title_lower for x in ['ap ', 'sat', 'act', 'calculus']):
        return GradeLevel.GRADE_12
    
    # Fallback: use order_in_region (map 0-12 to K-12)
    if order_in_region <= 12:
        try:
            return list(GradeLevel)[order_in_region]
        except IndexError:
            pass
    
    # Default to grade 8 (middle school)
    return GradeLevel.GRADE_8


def extract_subject(course_title: str) -> str:
    """
    Extract subject from Khan Academy course title.
    
    Args:
        course_title: Course title
    
    Returns:
        Subject name (Math, Science, History, etc.)
    """
    title_lower = course_title.lower()
    
    if any(word in title_lower for word in ['math', 'algebra', 'geometry', 'calculus', 
                                              'trigonometry', 'statistics', 'arithmetic',
                                              'precalculus', 'pre-calculus']):
        return 'Math'
    elif any(word in title_lower for word in ['science', 'physics', 'chemistry', 
                                                'biology', 'astronomy', 'cosmology']):
        return 'Science'
    elif 'history' in title_lower:
        return 'History'
    elif any(word in title_lower for word in ['english', 'grammar', 'reading', 'writing']):
        return 'English'
    elif any(word in title_lower for word in ['economics', 'finance', 'personal finance']):
        return 'Economics'
    elif any(word in title_lower for word in ['computer', 'programming', 'coding', 'javascript', 'python']):
        return 'Computer Science'
    elif 'art' in title_lower:
        return 'Arts'
    elif 'music' in title_lower:
        return 'Music'
    elif any(word in title_lower for word in ['social', 'civics', 'government']):
        return 'Social Studies'
    else:
        return 'Other'
