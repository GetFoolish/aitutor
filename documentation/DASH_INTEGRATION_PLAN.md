# Integration Plan: Khan Academy Question Bank + DASH System

## Overview

Integrate the Khan Academy question bank hierarchy (Region > Subject > Course > Unit > Lesson > Exercise > Question) with the DASH adaptive learning system. Students select Region and Subject; DASH handles all adaptive question selection.

---

## 1. Data Model Mapping

### Khan Academy Hierarchy → DASH Concepts

| Khan Academy | DASH Concept | Student-Facing | Notes |
|--------------|--------------|----------------|-------|
| Region | Filter | Dropdown selection | e.g., US, IN, IN-KA |
| Subject | Filter | Dropdown selection | e.g., Math, Science |
| Course | Learning Path | Hidden (DASH decides) | e.g., "3rd Grade Math" |
| **Unit** | **Skill** | Shown as "Skills" | Primary skill tracking unit |
| **Lesson** | **Sub-skill** | Shown as "Sub-skills" | Granular progress within unit |
| Exercise | Question Pool | Hidden | Source of questions |
| Question | Question | Practice item | Actual practice content |

### Database Schema Changes

```python
# New Skill model (replaces generated_skills collection)
class KhanSkill:
    skill_id: str           # unit_id from Khan Academy
    name: str               # unit title
    course_id: str          # parent course
    region: str             # e.g., "US"
    subject: str            # e.g., "Math"
    grade_level: GradeLevel # derived from course position/title
    order_in_course: int    # learning sequence
    prerequisites: List[str] # previous units in course
    sub_skills: List[str]   # lesson_ids within this unit
    difficulty: float       # average difficulty of exercises
    forgetting_rate: float  # default 0.1

# Sub-skill model (new)
class KhanSubSkill:
    sub_skill_id: str       # lesson_id from Khan Academy
    name: str               # lesson title
    skill_id: str           # parent unit_id
    order_in_skill: int     # lesson order within unit
    exercise_ids: List[str] # exercises in this lesson
    difficulty: float       # derived from exercises
```

---

## 2. Initial Assessment Flow

### Triggered When
- New student registers with DOB
- Student selects new Region + Subject combination

### Assessment Algorithm (Progressive Difficulty)

```
1. Calculate expected_grade from DOB:
   - age = current_year - birth_year
   - expected_grade = age - 5 (K=0, Grade 1=1, etc.)

2. Start assessment at expected_grade - 2 (floor at K)

3. For each of 10 questions:
   a. Select question from current_assessment_grade
   b. If correct: move to next higher grade (cap at expected_grade + 2)
   c. If incorrect: stay at current grade or move down
   d. Track skill coverage to avoid repeating skills

4. After 10 questions:
   a. Calculate "actual_grade_level" based on performance
   b. Initialize all units below actual_grade_level as "mastered" (prob >= 0.7)
   c. Set current learning position to first unmastered unit at actual_grade_level
```

### Assessment Question Selection

```python
def select_assessment_question(
    current_grade: int,
    region: str,
    subject: str,
    answered_skill_ids: Set[str]
) -> Question:
    """
    Select diverse questions across skills at the target grade.
    - One question per skill (unit) maximum
    - Prioritize foundational skills (lower order_in_course)
    """
```

---

## 3. DASH System Modifications

### A. Skill Loading (`_load_from_mongodb`)

Replace current skill loading with Khan hierarchy:

```python
def _load_skills_from_khan(self, region: str, subject: str):
    """
    Load skills (units) and sub-skills (lessons) for student's region/subject.
    Build question index from exercises.
    """
    # 1. Get courses for region + subject
    courses = db.courses.find({
        "region": region,
        "subject": subject  # Need to add subject field to courses
    }).sort("order_in_region", 1)

    # 2. For each course, load units as skills
    for course in courses:
        units = db.units.find({"course_id": course["course_id"]})
        for unit in units:
            skill = KhanSkill(
                skill_id=unit["unit_id"],
                name=unit["title"],
                course_id=course["course_id"],
                grade_level=derive_grade_from_course(course),
                order_in_course=unit["order_in_course"],
                prerequisites=get_previous_units(course, unit),
                ...
            )
            self.skills[skill.skill_id] = skill

    # 3. Build question index from exercises
    exercises = db.exercises.find({
        "course_id": {"$in": course_ids}
    })
    # Map exercise_id → lesson_id → unit_id for question selection
```

### B. Question Selection (`get_next_question`)

Modify to work with Khan hierarchy:

```python
def get_next_question_khan(
    self,
    student_id: str,
    region: str,
    subject: str,
    exclude_question_ids: List[str]
) -> Optional[Question]:
    """
    1. Get recommended skills (units with prob < 0.7)
    2. Within each skill, find sub-skills (lessons) needing practice
    3. Select exercise from target lesson based on difficulty adaptation
    4. Return question from that exercise
    """
```

### C. Prerequisite Chain

Units within a course form a natural prerequisite chain:

```python
def get_previous_units(course_id: str, current_unit: Unit) -> List[str]:
    """
    All units with order_in_course < current_unit.order_in_course
    become prerequisites for the current unit.
    """
    return [u["unit_id"] for u in db.units.find({
        "course_id": course_id,
        "order_in_course": {"$lt": current_unit["order_in_course"]}
    })]
```

---

## 4. API Changes

### New Endpoints

```python
# Student onboarding
POST /api/student/setup
{
    "date_of_birth": "2015-03-15",
    "region": "US",
    "subject": "Math"
}
Response: { "assessment_required": true, "expected_grade": "GRADE_3" }

# Start assessment
POST /api/assessment/start
{
    "region": "US",
    "subject": "Math"
}
Response: { "assessment_id": "...", "total_questions": 10 }

# Get next assessment question
GET /api/assessment/{assessment_id}/next-question
Response: { PerseusQuestion with grade_level metadata }

# Submit assessment answer
POST /api/assessment/{assessment_id}/answer
{
    "question_id": "...",
    "is_correct": true,
    "response_time_seconds": 45.2
}
Response: { "questions_remaining": 7, "current_grade": "GRADE_4" }

# Complete assessment
POST /api/assessment/{assessment_id}/complete
Response: {
    "actual_grade_level": "GRADE_3",
    "skills_initialized": 142,
    "starting_unit": { "unit_id": "...", "name": "Intro to Multiplication" }
}
```

### Modified Endpoints

```python
# Get questions (now requires region/subject context)
GET /api/questions/{sample_size}?region=US&subject=Math

# Skill scores (now returns unit-level skills)
GET /api/skill-scores?region=US&subject=Math
Response: {
    "skills": [
        {
            "skill_id": "unit_abc123",
            "name": "Addition and Subtraction",
            "grade_level": "GRADE_2",
            "probability": 0.85,
            "mastered": true,
            "sub_skills": [
                {"sub_skill_id": "lesson_1", "name": "Adding 1-digit numbers", "probability": 0.92},
                {"sub_skill_id": "lesson_2", "name": "Subtracting 1-digit numbers", "probability": 0.78}
            ]
        }
    ]
}
```

---

## 5. Grade Level Derivation

Map Khan Academy courses to grade levels:

```python
COURSE_GRADE_MAPPING = {
    # US Math courses
    "early-math": GradeLevel.K,
    "cc-kindergarten-math": GradeLevel.K,
    "cc-1st-grade-math": GradeLevel.GRADE_1,
    "cc-2nd-grade-math": GradeLevel.GRADE_2,
    "cc-third-grade-math": GradeLevel.GRADE_3,
    # ... etc
    "algebra": GradeLevel.GRADE_9,
    "geometry": GradeLevel.GRADE_10,
    "algebra2": GradeLevel.GRADE_11,
    "precalculus": GradeLevel.GRADE_12,
}

def derive_grade_from_course(course: dict) -> GradeLevel:
    """
    Derive grade level from course slug or order_in_region.
    Fallback: use order_in_region / total_courses * 12
    """
```

---

## 6. Student State Management

### Per Region+Subject State

Students can have different progress in different region/subject combinations:

```python
class StudentProfile:
    user_id: str
    date_of_birth: date

    # Separate state per region+subject
    subject_states: Dict[str, SubjectState]  # key = "US_Math"

class SubjectState:
    region: str
    subject: str
    assessment_completed: bool
    actual_grade_level: GradeLevel
    current_course_id: str
    current_unit_id: str
    skill_states: Dict[str, SkillState]  # unit_id → state
    sub_skill_states: Dict[str, SkillState]  # lesson_id → state
    question_history: List[QuestionAttempt]
```

---

## 7. Implementation Order

### Phase 1: Data Preparation (Khan Academy side)
1. Add `subject` field to courses collection (derive from Khan API or slug)
2. Add `grade_level` field to courses collection
3. Ensure exercises have proper `course_id` (already fixed with compound index)

### Phase 2: DASH Core Changes
1. Create `KhanSkill` and `KhanSubSkill` models
2. Modify `_load_from_mongodb` to load from Khan hierarchy
3. Update `get_recommended_skills` for unit-based skills
4. Update `get_next_question` for exercise-based questions

### Phase 3: Assessment System
1. Implement progressive difficulty assessment algorithm
2. Create assessment start/answer/complete endpoints
3. Implement skill initialization after assessment

### Phase 4: API Integration
1. Add region/subject parameters to existing endpoints
2. Create new student setup endpoint
3. Update skill-scores to return hierarchical view

### Phase 5: Frontend
1. Region + Subject selection UI
2. Assessment flow UI
3. Skill progress display (units as skills, lessons as sub-skills)

---

## 8. Decisions Summary

| Question | Decision |
|----------|----------|
| Skill granularity | Unit = Skill, Lesson = Sub-skill, Exercise = Question source |
| Assessment type | Progressive difficulty (start low, increase on correct) |
| Navigation control | DASH controls all (student picks Region + Subject only) |
| Subject classification | Parse from course title (existing `extract_subject()` function) |
| Multi-subject support | Yes, separate DASH state per region+subject |
| Cross-course prerequisites | Yes, courses form a prerequisite chain within region+subject |

---

## 9. Subject Classification

Subject is derived dynamically from course title using `extract_subject()` in `api_server.py`:

```python
def extract_subject(course_title):
    """Extract subject from course title"""
    title_lower = course_title.lower()

    if 'math' in title_lower or 'algebra' in title_lower or 'geometry' in title_lower or \
       'calculus' in title_lower or 'trigonometry' in title_lower or 'statistics' in title_lower:
        return 'Math'
    elif 'science' in title_lower or 'physics' in title_lower or 'chemistry' in title_lower or \
         'biology' in title_lower:
        return 'Science'
    elif 'history' in title_lower:
        return 'History'
    elif 'english' in title_lower or 'grammar' in title_lower or 'reading' in title_lower:
        return 'English'
    elif 'economics' in title_lower:
        return 'Economics'
    elif 'computer' in title_lower or 'programming' in title_lower or 'coding' in title_lower:
        return 'Computer Science'
    elif 'art' in title_lower:
        return 'Arts'
    elif 'music' in title_lower:
        return 'Music'
    else:
        return 'Other'
```

**Recommendation for DASH**: Copy this function to DASH system OR persist `subject` field in courses collection during scraping.

---

## 10. Files to Modify (in aitutor repo)

| File | Changes |
|------|---------|
| `services/DashSystem/dash_system.py` | Replace skill loading with Khan hierarchy, update question selection |
| `services/DashSystem/dash_api.py` | Add region/subject parameters, new assessment endpoints |
| `managers/user_manager.py` | Add `SubjectState` class, per-subject progress tracking |
| `managers/mongodb_manager.py` | Add Khan Academy collections (courses, units, lessons, exercises, questions) |
| New: `models/khan_models.py` | Define `KhanSkill`, `KhanSubSkill` dataclasses |
| New: `services/assessment_service.py` | Progressive difficulty assessment logic |
