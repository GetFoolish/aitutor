# DASH System: Mathematical Model Explained

## Overview

The DASH (Dynamic Adaptive Skill Hierarchy) system uses mathematical models to:
1. Track student skill mastery over time
2. Account for memory decay (forgetting)
3. Recommend the next best skill to practice
4. Update skills based on performance

This document explains the math behind each component.

---

## 1. Memory Strength Decay

Skills fade over time if not practiced (the "forgetting curve"). The DASH system models this using exponential decay.

### Formula:
```
current_strength = initial_strength × e^(-forgetting_rate × time_elapsed)
```

### Parameters:
- `initial_strength`: Memory strength at last practice (0.0 to 5.0)
- `forgetting_rate`: How quickly the skill fades (0.05 to 0.20)
  - Lower values = slower forgetting (e.g., 0.05 for basic skills)
  - Higher values = faster forgetting (e.g., 0.20 for complex skills)
- `time_elapsed`: Seconds since last practice

### Example:
```python
# Student practiced "addition_basic" 1 hour ago
initial_strength = 3.5
forgetting_rate = 0.07  # Moderate decay
time_elapsed = 3600  # 1 hour = 3600 seconds

current_strength = 3.5 × e^(-0.07 × 3600)
                 = 3.5 × e^(-252)
                 = 3.5 × 0.0 (essentially 0 after 1 hour)
```

**Reality Check**: This is too aggressive! Time should be in **hours** or **days**, not seconds.

### Actual Implementation (dash_system.py:260-263):
```python
def calculate_memory_strength(self, student_id: str, skill_id: str, current_time: float) -> float:
    state = self.get_student_state(student_id, skill_id)
    skill = self.skills[skill_id]

    if state.last_practice_time is None:
        return state.memory_strength

    time_elapsed = current_time - state.last_practice_time  # In seconds!
    decay_factor = math.exp(-skill.forgetting_rate * time_elapsed)

    return state.memory_strength * decay_factor
```

**Issue**: With `forgetting_rate=0.07` and time in seconds, memory decays almost instantly.

**Fix Needed**: Convert time to hours:
```python
time_elapsed_hours = (current_time - state.last_practice_time) / 3600
decay_factor = math.exp(-skill.forgetting_rate * time_elapsed_hours)
```

---

## 2. Correctness Prediction (Sigmoid Function)

The system predicts the probability that a student will answer correctly using a **logistic sigmoid function**.

### Formula:
```
P(correct) = 1 / (1 + e^(-(memory_strength - difficulty)))
```

### Interpretation:
- **memory_strength**: How well the student knows the skill (-2.0 to 5.0)
- **difficulty**: How hard the skill is (0.0 to 5.0)
- **Logit** = memory_strength - difficulty
  - If logit > 0 → Student likely knows it (P > 0.5)
  - If logit < 0 → Student likely struggles (P < 0.5)

### Example:
```python
# Scenario 1: Strong memory, easy skill
memory_strength = 4.0
difficulty = 1.0
logit = 4.0 - 1.0 = 3.0

P(correct) = 1 / (1 + e^(-3.0))
           = 1 / (1 + 0.05)
           = 0.95 (95% likely to answer correctly)

# Scenario 2: Weak memory, hard skill
memory_strength = 0.5
difficulty = 3.0
logit = 0.5 - 3.0 = -2.5

P(correct) = 1 / (1 + e^(2.5))
           = 1 / (1 + 12.18)
           = 0.08 (8% likely to answer correctly)
```

### Implementation (dash_system.py:293-300):
```python
def predict_correctness(self, student_id: str, skill_id: str, current_time: float) -> float:
    memory_strength = self.calculate_memory_strength(student_id, skill_id, current_time)
    skill = self.skills[skill_id]

    logit = memory_strength - skill.difficulty
    return 1 / (1 + math.exp(-logit))
```

---

## 3. Updating Memory Strength (After Practice)

When a student answers a question, the DASH system updates their memory strength.

### For Correct Answers:

#### Formula:
```
strength_increment = 1.0 / (1 + 0.1 × correct_count)
strength_increment = strength_increment × time_penalty

new_strength = min(5.0, current_strength + strength_increment)
```

#### Parameters:
- `correct_count`: Number of previous correct answers
  - First correct answer: increment = 1.0 / (1 + 0) = **1.0**
  - Second correct answer: increment = 1.0 / (1.1) = **0.91**
  - Third correct answer: increment = 1.0 / (1.2) = **0.83**
  - (Diminishing returns as mastery increases)
- `time_penalty`: Multiplier based on response time
  - Fast response (< 3 min): `1.0` (no penalty)
  - Slow response (> 3 min): `0.5` (50% penalty)

#### Example:
```python
# Student answered correctly for the 2nd time, took 90 seconds
correct_count = 1  # (was 1, now will be 2)
current_strength = 2.0
response_time = 90  # seconds

strength_increment = 1.0 / (1 + 0.1 × 1) = 0.91
time_penalty = 1.0  # (90 < 180 seconds)
strength_increment = 0.91 × 1.0 = 0.91

new_strength = min(5.0, 2.0 + 0.91) = 2.91
```

### For Incorrect Answers:

#### Formula:
```
new_strength = max(-2.0, current_strength - 0.2)
```

- Memory strength **decreases by 0.2** (fixed penalty)
- Cannot go below **-2.0**

#### Example:
```python
# Student answered incorrectly
current_strength = 1.5

new_strength = max(-2.0, 1.5 - 0.2) = 1.3
```

### Implementation (dash_system.py:302-328):
```python
def update_student_state(self, student_id: str, skill_id: str, is_correct: bool,
                        current_time: float, response_time_seconds: float = 0.0):
    state = self.get_student_state(student_id, skill_id)

    # Update practice counts
    state.practice_count += 1
    if is_correct:
        state.correct_count += 1

    # Calculate current memory strength with decay
    current_strength = self.calculate_memory_strength(student_id, skill_id, current_time)

    # Update memory strength based on performance
    if is_correct:
        # Base strength increment with diminishing returns
        strength_increment = 1.0 / (1 + 0.1 * state.correct_count)

        # Apply time penalty
        time_penalty = self.calculate_time_penalty(response_time_seconds)
        strength_increment *= time_penalty

        state.memory_strength = min(5.0, current_strength + strength_increment)
    else:
        # Slight decrease for incorrect answers
        state.memory_strength = max(-2.0, current_strength - 0.2)

    # Update last practice time
    state.last_practice_time = current_time
```

---

## 4. Prerequisite Penalty (When Student Gets It Wrong)

When a student answers incorrectly, the DASH system assumes the foundational skills may also be weak. It penalizes prerequisite skills.

### Formula:
```
For each prerequisite:
    new_strength = max(-2.0, current_strength - 0.1)
```

- **Smaller penalty** (0.1) compared to the direct skill (0.2)
- Applied **recursively** to all prerequisites in the skill tree

### Example:
```
Skill Tree:
- quadratic_equations (Grade 9)
  ├─ quadratic_intro (Grade 8)
     ├─ linear_equations_1var (Grade 7)
        └─ algebraic_expressions (Grade 7)

Student gets quadratic_equations WRONG:
1. quadratic_equations: -0.2
2. quadratic_intro: -0.1
3. linear_equations_1var: -0.1
4. algebraic_expressions: -0.1
```

### Implementation (dash_system.py:331-362):
```python
def update_with_prerequisites(self, student_id: str, skill_ids: List[str], is_correct: bool,
                             current_time: float, response_time_seconds: float = 0.0) -> List[str]:
    all_affected_skills = []

    for skill_id in skill_ids:
        # Always update the direct skill
        self.update_student_state(student_id, skill_id, is_correct, current_time, response_time_seconds)
        all_affected_skills.append(skill_id)

        # If answer is wrong, also penalize prerequisites
        if not is_correct:
            prerequisites = self.get_all_prerequisites(skill_id)
            for prereq_id in prerequisites:
                state = self.get_student_state(student_id, prereq_id)
                current_strength = self.calculate_memory_strength(student_id, prereq_id, current_time)

                # Apply smaller penalty to prerequisites
                state.memory_strength = max(-2.0, current_strength - 0.1)
                state.last_practice_time = current_time

                all_affected_skills.append(prereq_id)

    return all_affected_skills
```

---

## 5. Skill Recommendation Algorithm

The system recommends skills where:
1. **Predicted correctness < 0.7** (student needs practice)
2. **All prerequisites are met** (student is ready)

### Steps:

#### Step 1: Calculate Predicted Correctness for All Skills
```python
for skill in all_skills:
    P(correct) = 1 / (1 + e^(-(memory_strength - difficulty)))
```

#### Step 2: Check Prerequisites
```python
for skill in candidate_skills:
    for prereq in skill.prerequisites:
        if P(prereq_correct) < 0.7:
            # Prerequisite not mastered yet!
            exclude_skill()
```

#### Step 3: Return Skills Below Threshold
```python
recommended_skills = [
    skill for skill in all_skills
    if P(skill_correct) < 0.7 and all_prerequisites_met(skill)
]
```

### Example:
```
Student Profile:
- addition_basic: memory_strength = 4.0, P(correct) = 0.98 → SKIP (mastered)
- multiplication_tables: memory_strength = 1.5, P(correct) = 0.50 → RECOMMEND
- fractions_intro: memory_strength = 0.2, P(correct) = 0.30 → CHECK PREREQS
  - Prerequisite: division_basic, P(correct) = 0.45 → NOT READY

Recommended Skills: [multiplication_tables]
```

### Implementation (dash_system.py:452-466):
```python
def get_recommended_skills(self, student_id: str, current_time: float, threshold: float = 0.7) -> List[str]:
    recommendations = []

    for skill_id, skill in self.skills.items():
        probability = self.predict_correctness(student_id, skill_id, current_time)

        # Check if prerequisites are met
        prerequisites_met = self.are_prerequisites_met(student_id, skill_id, current_time, threshold)

        # Recommend if probability is below threshold and prerequisites are met
        if probability < threshold and prerequisites_met:
            recommendations.append(skill_id)

    return recommendations
```

---

## 6. Grade-Level Initialization (Cold Start)

When a new student joins and specifies their grade level, the system automatically marks skills below their grade as "mastered".

### Formula:
```
For each skill:
    if skill.grade_level < student.grade_level:
        memory_strength = 3.0  # Marked as mastered
        last_practice_time = now
```

### Example:
```
New Student: Grade 5 (grade_level = 5)

Skills Initialized:
- K (grade 0): counting_1_10 → memory_strength = 3.0
- Grade 1: addition_basic, subtraction_basic → memory_strength = 3.0
- Grade 2: addition_2digit, multiplication_intro → memory_strength = 3.0
- Grade 3: multiplication_tables, division_basic → memory_strength = 3.0
- Grade 4: fractions_operations, decimals_intro → memory_strength = 3.0
- Grade 5: decimals_operations → memory_strength = 0.0 (STARTS HERE)
- Grade 6+: → memory_strength = 0.0
```

### Implementation (dash_system.py:377-390):
```python
if is_new_user and grade_level:
    print(f"🚀 New user '{user_id}' at grade {grade_level.name}. Initializing past skills as mastered...")
    for skill_id, skill in self.skills.items():
        # If skill's grade is lower than the user's starting grade, mark as mastered
        if skill.grade_level.value < grade_level.value:
            if skill_id in user_profile.skill_states:
                user_profile.skill_states[skill_id].memory_strength = 3.0
                user_profile.skill_states[skill_id].last_practice_time = time.time()
                print(f"  ✓ Mastered '{skill.name}' ({skill.grade_level.name})")

    # Save the updated profile
    self.user_manager.save_user(user_profile)
```

---

## 7. Complete Example Walkthrough

### Initial State:
```
Student: Alice (Grade 5)
Skill: multiplication_tables (Grade 3)
- memory_strength: 3.0 (initialized as mastered)
- practice_count: 0
- correct_count: 0
- last_practice_time: 2 hours ago
```

### Step 1: Memory Decay (2 hours later)
```
time_elapsed = 2 × 3600 = 7200 seconds
forgetting_rate = 0.08

decay_factor = e^(-0.08 × 7200) = e^(-576) ≈ 0 (PROBLEM: too aggressive!)

current_strength = 3.0 × 0 ≈ 0
```

**With fixed formula (time in hours)**:
```
time_elapsed_hours = 2
decay_factor = e^(-0.08 × 2) = e^(-0.16) = 0.85

current_strength = 3.0 × 0.85 = 2.55
```

### Step 2: Predict Correctness
```
difficulty = 0.8
logit = 2.55 - 0.8 = 1.75

P(correct) = 1 / (1 + e^(-1.75))
           = 1 / (1 + 0.174)
           = 0.85 (85% chance)
```

### Step 3: Student Answers Correctly (took 45 seconds)
```
correct_count = 0 (before), becomes 1 (after)

strength_increment = 1.0 / (1 + 0.1 × 0) = 1.0
time_penalty = 1.0 (45 < 180 seconds)
strength_increment = 1.0 × 1.0 = 1.0

new_strength = min(5.0, 2.55 + 1.0) = 3.55
```

### Step 4: 1 Week Later (Memory Decay)
```
time_elapsed_hours = 7 × 24 = 168 hours
decay_factor = e^(-0.08 × 168) = e^(-13.44) ≈ 0.0000015

current_strength = 3.55 × 0.0000015 ≈ 0 (forgotten!)

P(correct) = 1 / (1 + e^(-(0 - 0.8)))
           = 1 / (1 + e^(0.8))
           = 1 / (1 + 2.23)
           = 0.31 (31% chance)

→ RECOMMENDED for practice (below 0.7 threshold)
```

---

## 8. API Integration

### GET /next-question/{user_id}?grade=5
**New User with Grade**:
```json
{
  "user_id": "alice123",
  "grade": "5"
}
```

Response:
```
1. Initialize Alice with Grade 5
2. Mark all skills K-4 as mastered (memory_strength = 3.0)
3. Get recommended skills (where P(correct) < 0.7)
4. Return a question for the top recommended skill
```

### POST /submit-answer/{user_id}
**Submit Answer**:
```json
{
  "question_id": "perseus_12345",
  "skill_ids": ["multiplication_tables"],
  "is_correct": true,
  "response_time_seconds": 45
}
```

Response:
```json
{
  "success": true,
  "is_correct": true,
  "skill_details": [
    {
      "skill_id": "multiplication_tables",
      "name": "Multiplication Tables",
      "memory_strength": 3.55,
      "is_direct": true
    }
  ],
  "affected_skills_count": 1
}
```

### GET /skill-states/{user_id}
**Get All Skills**:
```json
{
  "skills": [
    {
      "skill_id": "counting_1_10",
      "name": "Counting 1-10",
      "grade_level": "K",
      "memory_strength": 3.0,
      "practice_count": 0,
      "correct_count": 0,
      "prerequisites": [],
      "is_locked": false
    },
    {
      "skill_id": "quadratic_equations",
      "name": "Quadratic Equations",
      "grade_level": "GRADE_9",
      "memory_strength": 0.0,
      "practice_count": 0,
      "correct_count": 0,
      "prerequisites": ["quadratic_intro"],
      "is_locked": true
    }
  ]
}
```

---

## 9. Frontend Integration

### Learning Path Sidebar
The sidebar fetches `/skill-states/{user_id}` and displays:
- **Green**: memory_strength ≥ 0.8 (mastered)
- **Yellow**: 0.3 ≤ memory_strength < 0.8 (in progress)
- **Red**: memory_strength < 0.3 (needs practice)
- **Locked**: Prerequisites not met

### Question Display
1. Fetches `/next-question/{user_id}?grade=5`
2. Renders Perseus math content
3. User answers
4. Submits via `/submit-answer/{user_id}`
5. Shows updated skill strengths

---

## 10. Summary: How Everything Works Together

```
┌─────────────────────────────────────────────┐
│ 1. User logs in (Grade 5)                  │
│    → Initialize skills (K-4 mastered)      │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 2. GET /next-question/{user_id}?grade=5    │
│    → Calculate memory decay for all skills │
│    → Predict P(correct) for each skill     │
│    → Find skills with P(correct) < 0.7     │
│    → Check prerequisites                    │
│    → Return question for top skill         │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 3. User answers question                    │
│    → POST /submit-answer/{user_id}         │
│    → Update memory_strength                │
│      • Correct: +1.0 / (1 + 0.1×count)     │
│      • Wrong: -0.2                         │
│      • Prereqs: -0.1 if wrong              │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 4. Display updated skills                   │
│    → GET /skill-states/{user_id}           │
│    → Show progress in sidebar              │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ 5. Time passes (memory decay)               │
│    → strength × e^(-rate × hours)          │
│    → Skills need practice again             │
└─────────────────────────────────────────────┘
```

---

## Conclusion

The DASH system provides an intelligent, adaptive learning experience by:
1. **Tracking** skill mastery over time
2. **Modeling** memory decay (forgetting curve)
3. **Predicting** student performance (sigmoid function)
4. **Updating** skills based on correct/incorrect answers
5. **Recommending** the next best skill to practice
6. **Penalizing** prerequisites when foundational skills are weak
7. **Initializing** new students based on grade level

All the math is implemented in `DashSystem/dash_system.py` and exposed via REST APIs in `DashSystem/dash_api.py`.
