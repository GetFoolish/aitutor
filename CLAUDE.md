# AI Tutor Project - Claude Code Rules

## Critical API Signature Rules

### 1. Never Add Parameters Without Verification
**NEVER** add parameters to Python API calls without checking the actual function signature first.

Before calling any function in `dash_system.py`, ALWAYS:
1. Read the function definition to see what parameters it accepts
2. Check existing calls to that function for examples
3. Only use parameters that are explicitly defined

### 2. Check Both Sides of API Calls
When modifying API endpoints or function calls:
- Check the **backend function signature** in `services/DashSystem/dash_system.py`
- Check the **frontend API call** in `frontend/src/` components
- Check the **FastAPI endpoint** in `services/DashSystem/dash_api.py`
- Ensure all three layers use the same parameter names and types

### 3. `get_next_question_flexible()` Signature
This function is called frequently. Its ONLY valid parameters are:
```python
def get_next_question_flexible(
    self,
    student_id: str,
    current_time: float,
    exclude_question_ids: Optional[List[str]] = None,
    force_grade_range: bool = False,
    user_profile: Optional['UserProfile'] = None,
    exclude_skill_ids: Optional[List[str]] = None,
    fast_mode: bool = False
) -> Optional[Question]:
```

**DO NOT** pass: `difficulty`, `grade`, `subject`, `used_skill_ids` - these are NOT valid parameters.

## UI/UX Rules

### 4. AssessmentFlow Must Work End-to-End
Always test that `AssessmentFlow.tsx` can:
- Load question 1
- Submit an answer
- Load question 2
- Complete the full assessment flow

Never close a task until you've verified the assessment can get past question 1.

### 5. Toolbar Overlap Issues
Check for floating UI elements that can overlap with content:
- `FloatingControlPanel` at bottom-right
- Dropdowns and popovers
- Hint panels
- Feedback boxes

Use `z-index` carefully and test on small viewports (≤920px height).

## Testing Rules

### 6. Run Integration Tests
Before claiming "done", run:
```bash
venv/bin/python tests/test_integration.py
```

### 7. Check Browser Console
Always check the browser console for:
- React errors (red text)
- Network errors (failed API calls)
- Perseus widget errors (ErrorBoundary warnings)

## Code Quality Rules

### 8. Batch Similar Bugs
If you find a bug in one component (e.g., toolbar overlap):
1. Search the entire codebase for the same pattern
2. Fix all instances at once
3. Don't fix bugs one at a time

### 9. Perseus Widget Fields
When modifying Perseus questions, ensure ALL required fields are present:
- `numeric-input`: MUST have `coefficient`, `static`, `labelText`, `size`
- `radio`: MUST have sanitized choices with no pre-selected state
- `dropdown`: MUST have 1-based indexing (0 = placeholder)

### 10. Context Before Fixing
When asked to fix a bug:
1. Read the FULL error message including stack trace
2. Read the relevant function signatures
3. Check what arguments are ACTUALLY being passed
4. Fix the mismatch - don't guess

## MongoDB Rules

### 11. Use Environment Variables
- MongoDB is on Atlas (cloud), NOT localhost
- ALWAYS use `MONGODB_URI` from `.env`
- Never hardcode `mongodb://localhost:27017`

### 12. JWT Claims
- JWT `sub` field contains `user_id` (NOT `userId`)
- Auth middleware uses `get_current_user()` which returns `sub`

## Performance Rules

### 13. Parallel Operations
When multiple independent operations are needed:
- Use `ThreadPoolExecutor` with timeouts
- Don't block on slow operations
- Cache results when possible

### 14. Question Generation
- Pool-first: check `content_pool` collection
- JIT fallback: only when pool is empty
- Never block assessment flow on question generation

## Documentation Rules

### 15. Update Memory After Fixes
After fixing a recurring bug class:
1. Document the pattern in `MEMORY.md`
2. Include validation count
3. Make it actionable for future sessions

### 16. No Silent Failures
Never:
- Catch exceptions without logging
- Return `None` without explanation
- Fail silently on critical paths

Always log errors with enough context to debug.

---

## Quick Reference: Common Function Signatures

### DASHSystem Methods
```python
# Get next question
get_next_question_flexible(student_id, current_time, exclude_question_ids, force_grade_range, user_profile, exclude_skill_ids, fast_mode)

# Record attempt
record_attempt(student_id, question_id, skill_ids, correct, difficulty, time_spent)

# Get recommendations
get_skill_recommendations(student_id, current_time, limit)
```

### ContentV1Engine Methods
```python
# Pop from pool
pop_assessment_question(skill_id, difficulty_tier, user_id)
pop_learning_question(skill_id, difficulty_tier, user_id)

# Ensure pool exists
ensure_pool(skill_id, user_id)
```

### AIQuestionProvider Methods
```python
# Get question (JIT fallback)
get_question_for_skill(skill_id, skill_name, target_difficulty, grade_level, age, exclude_question_ids, user_id, fast_mode, subject)
```

---

**Remember: When in doubt, READ THE ACTUAL FUNCTION SIGNATURE before calling it.**
